"""server.py — the FastAPI HTTP server for the ServiceNow UI Action webhook.

The server builds on the existing pipeline (pipeline.py + servicenow_client.py).
It contains no new business logic — it is only an HTTP layer instead of the CLI.

Endpoints:
  GET  /health              — health check
  POST /generate-kb         — generates a KB article from a Story and pushes it

Authentication: the X-API-Key header (from the .env SNOW_WEBHOOK_API_KEY field).
The ServiceNow UI Action script sends this key.

Running:
  uvicorn snow_kb.server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from snow_kb.config import ConfigError, Settings, load_settings
from snow_kb.errors import MissingAssignmentGroupError
from snow_kb.pipeline import DuplicateKBError, _load_program, generate_kb_article
from snow_kb.servicenow_client import ServiceNowClient, ServiceNowError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------


class GenerateKBRequest(BaseModel):
    """The request sent by the ServiceNow UI Action."""

    story_id: str = Field(..., description="The Story number (STRY...) or its sys_id.")
    push: bool = Field(
        default=True,
        description="If True (default), the article is written to the KB.",
    )
    force_update: bool = Field(
        default=False,
        description="If True, overwrites the existing article (if the story was already processed).",
    )


class GenerateKBResponse(BaseModel):
    """The server response after the generation."""

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

# The path of the GEPA-optimized program (loaded at startup if it exists)
OPTIMIZED_PROGRAM_PATH = "artifacts/program.json"

# The (optimized) program loaded at startup — when None, the pipeline
# uses the basic StoryToKBArticle() (fallback).
_program = None


@app.on_event("startup")
def load_optimized_program() -> None:
    """Loads the GEPA-optimized program, if artifacts/program.json exists."""
    global _program
    try:
        _program = _load_program(OPTIMIZED_PROGRAM_PATH)
    except Exception as exc:
        logger.warning("Failed to load the optimized program: %s", exc)
        _program = None


def _get_settings() -> Settings:
    """Loads the settings (cached for the lifetime of the process)."""
    return load_settings()


def _get_api_key() -> str:
    """Returns the webhook API key from settings."""
    import os

    return os.environ.get("SNOW_WEBHOOK_API_KEY", "")


def _verify_api_key(x_api_key: str | None) -> None:
    """Simple API key check."""
    expected = _get_api_key()
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check (for the Docker/systemd healthcheck)."""
    try:
        settings = _get_settings()
        return HealthResponse(status="ok", dry_run=settings.dry_run)
    except Exception:
        return HealthResponse(status="degraded")


@app.post("/generate-kb", response_model=GenerateKBResponse)
def generate_kb(
    request: GenerateKBRequest,
    x_api_key: str | None = Header(default=None),
) -> GenerateKBResponse:
    """Generates a KB article from a Story and pushes it (optionally).

    The call is synchronous — it waits until the GLM generation finishes (~10-20 s).
    The ServiceNow UI Action needs a matching timeout.
    """
    _verify_api_key(x_api_key)

    try:
        settings = _get_settings()
        client = ServiceNowClient(settings)
        article = generate_kb_article(
            story_identifier=request.story_id,
            client=client,
            settings=settings,
            program=_program,
            push=request.push,
            force_update=request.force_update,
        )
    except DuplicateKBError as exc:
        # US2: on duplication we return 409 Conflict with the existing article data
        logger.warning("Duplication detected: %s", exc)
        settings = _get_settings()
        existing_url = f"https://{settings.snow_instance}/kb_view.do?sys_kb_id={exc.existing_sys_id}"
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(exc),
                "kb_sys_id": exc.existing_sys_id,
                "kb_url": existing_url,
            },
        ) from exc
    except MissingAssignmentGroupError as exc:
        # US2 (Team Feature): if the team is missing we return 422 Unprocessable Entity
        logger.warning("Missing Assignment Group: %s", exc)
        raise HTTPException(
            status_code=422,
            detail={"message": str(exc)},
        ) from exc
    except ServiceNowError as exc:
        logger.error("ServiceNow error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Unexpected error: %s", exc, exc_info=True)
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
        message="KB article created successfully." if sys_id else "Article generated (without push).",
    )
