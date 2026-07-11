"""server.py — FastAPI HTTP szerver a ServiceNow UI Action webhook-hoz.

A szerver a meglévő pipeline-ra (pipeline.py + servicenow_client.py) épül.
Nem tartalmaz új üzleti logikát — csak egy HTTP réteg a CLI helyett.

Végpontok:
  GET  /health              —健康égységi ellenőrzés
  POST /generate-kb         — Story-ból KB cikket generál és push-ol

Hitelesítés: X-API-Key header (a .env SNOW_WEBHOOK_API_KEY mezőjéből).
A ServiceNow UI Action script ezt a kulcsot küldi el.

Futtatás:
  uvicorn snow_kb.server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from snow_kb.config import ConfigError, Settings, load_settings
from snow_kb.pipeline import generate_kb_article
from snow_kb.servicenow_client import ServiceNowClient, ServiceNowError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic kérés/válasz modellek
# ---------------------------------------------------------------------------


class GenerateKBRequest(BaseModel):
    """A ServiceNow UI Action által küldött kérés."""

    story_id: str = Field(..., description="A Story száma (STRY...) vagy sys_id-ja.")
    push: bool = Field(
        default=True,
        description="Ha True (alapértelmezett), a cikk bekerül a KB-be.",
    )


class GenerateKBResponse(BaseModel):
    """A szerver válasza a generálás után."""

    success: bool
    story_id: str
    kb_sys_id: str | None = None
    kb_url: str | None = None
    title: str | None = None
    message: str = ""


class HealthResponse(BaseModel):
    status: str = "ok"
    dry_run: bool = False


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="snow-kb-generator",
    description="DSPy pipeline: ServiceNow Story → Knowledge Base Article",
    version="0.1.0",
)


def _get_settings() -> Settings:
    """Betölti a settings-t (cache-elve a process lifetime-re)."""
    return load_settings()


def _get_api_key() -> str:
    """Visszaadja a webhook API kulcsot a settings-ből."""
    import os

    return os.environ.get("SNOW_WEBHOOK_API_KEY", "")


def _verify_api_key(x_api_key: str | None) -> None:
    """Egyszerű API kulcs ellenőrzés."""
    expected = _get_api_key()
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Érvénytelen API kulcs.")


# ---------------------------------------------------------------------------
# Végpontok
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Egészségügyi ellenőrzés (Docker/systemd healthcheck-hez)."""
    try:
        settings = _get_settings()
        return HealthResponse(status="ok", dry_run=settings.dry_run)
    except Exception:
        return HealthResponse(status="degraded")


@app.post("/generate-kb", response_model=GenerateKBResponse)
async def generate_kb(
    request: GenerateKBRequest,
    x_api_key: str | None = Header(default=None),
) -> GenerateKBResponse:
    """Story-ból KB cikket generál és (opcionálisan) push-ol.

    A hívás szinkron — a GLM generálás befejezéséig vár (~10-20 mp).
    A ServiceNow UI Action-nak megfelelő timeout-ot kell beállítani.
    """
    _verify_api_key(x_api_key)

    try:
        settings = _get_settings()
        client = ServiceNowClient(settings)
        article = generate_kb_article(
            story_identifier=request.story_id,
            client=client,
            settings=settings,
            push=request.push,
        )
    except ServiceNowError as exc:
        logger.error("ServiceNow hiba: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ConfigError as exc:
        logger.error("Konfigurációs hiba: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Váratlan hiba: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    sys_id = getattr(article, "sys_id", None)
    kb_url = None
    if sys_id:
        kb_url = f"https://{settings.snow_instance}/kb_view.do?sys_kb_id={sys_id}"

    return GenerateKBResponse(
        success=True,
        story_id=request.story_id,
        kb_sys_id=sys_id,
        kb_url=kb_url,
        title=article.title,
        message="KB cikk sikeresen létrehozva." if sys_id else "Cikk generálva (push nélkül).",
    )
