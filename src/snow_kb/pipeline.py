"""pipeline.py — end-to-end orchestrátor: fetch → assemble → generate → push.

Ez a réteg köti össze:
  - a ServiceNow client-et (Story lekérés + KB létrehozás)
  - a DSPy programot (StoryToKBArticle)
  - a konfigurációt (Settings)

A program (program.py) nem tud a ServiceNow-ról. A client (servicenow_client.py)
nem tud a DSPy-ről. Ez a modul a kettő közöttiragasztó.

A ServiceNowClient-et egy Protocol (interfész) formájában várja, így a pipeline
mock clienttel is tesztelhető, amíg a valódi client nincs implementálva.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

import dspy

from snow_kb.config import Settings, load_settings

logger = logging.getLogger(__name__)


class DuplicateKBError(Exception):
    """Akkor dobódik, ha a Story-hoz már létezik KB cikk és a force_update=False."""

    def __init__(self, message: str, existing_sys_id: str = ""):
        super().__init__(message)
        self.existing_sys_id = existing_sys_id
from snow_kb.program import StoryToKBArticle
from snow_kb.schemas import KBArticle, StoryData


# ---------------------------------------------------------------------------
# ServiceNowClient Protocol (interfész)
# ---------------------------------------------------------------------------

class ServiceNowClientProtocol(Protocol):
    """A pipeline által elvárt ServiceNow client interfész.

    A valódi implementáció (servicenow_client.py) ezt fogja teljesíteni.
    A pipeline csak ezt a két metódust hívja — nem tud a HTTP részletekről.
    """

    def get_story(self, story_identifier: str) -> StoryData: ...

    def create_kb_article(self, article: KBArticle) -> str:
        """Visszaadja az új KB cikk sys_id-ját."""
        ...

    def get_update_set_changes(self, update_set_name: str) -> tuple[str, str]:
        """Visszaadja az Update Set módosításait (summary, raw_payloads)."""
        ...


# ---------------------------------------------------------------------------
# Story szöveggé egyesítése
# ---------------------------------------------------------------------------

# A mezőcímke map: a belső mezőnevek emberi olvasásra alkalmas címke.
# Csak a tartalmi mezők, amik a kontextusba kerülnek (az azonosítók nem).
_FIELD_LABELS: dict[str, str] = {
    "short_description": "Short Description",
    "description": "Description",
    "acceptance_criteria": "Acceptance Criteria",
    "u_technical_specification": "Technical Specification",
    "work_notes": "Work Notes",
    "comments": "Comments",
    "state": "State",
    "assigned_to": "Assigned To",
}


def assemble_story_text(story: StoryData, settings: Settings | None = None) -> str:
    """A Story mezőit egyetlen címkézett szöveggé fűzi össze.

    A config.story_fields sorrendjében halad, és minden mezőt egy fejléccel
    lát el (pl. "## Description: ..."). Az üres mezőket kihagyja — nem
    zavarnak be üres szakaszokkal a kontextusba.

    Ez a szöveg lesz az ExtractChange Signature bemenete (story_text).

    Args:
        story: a ServiceNow-ból lekért Story adatai.
        settings: ha meg van adva, a story_fields sorrendjét innen veszi;
            egyébként a StoryData mezőinek sorrendjéből indul ki.

    Returns:
        Egyetlen szöveg, szakaszokra bontva, címkézve.
    """
    # A feldolgozandó mezők sorrendje
    field_order: list[str]
    if settings is not None:
        field_order = settings.story_fields
    else:
        field_order = list(_FIELD_LABELS.keys())

    sections: list[str] = []

    # A Story száma a tetejére (ha van)
    if story.number:
        sections.append(f"# Story: {story.number}")

    # Tartalmi mezők, címkézve, üresek kihagyva
    for field_name in field_order:
        value = getattr(story, field_name, None)
        if not value or not str(value).strip():
            continue
        label = _FIELD_LABELS.get(field_name, field_name.replace("_", " ").title())
        sections.append(f"## {label}\n{value}")

    if not sections:
        return "(A Story nem tartalmaz feldolgozható tartalmat.)"

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# LM konfigurálás (dspy-fundamentals / dspy-advanced-workflow szerint)
# ---------------------------------------------------------------------------

def configure_lm(settings: Settings) -> None:
    """Globálisan konfigurálja a DSPy LM-et a settings-ből.

    A skill szerint: dspy.configure(lm=..., track_usage=True) — globálisan,
    modulonként csak indokolt esetben override. A track_usage a cost/latency
    megfigyelhetőségséhez kell.

    Ha settings.pipeline.use_pi_auth True, a dspy_lm_auth.LM osztályt használja
    (Pi Agent GLM előfizetés hitelesítéshez). Egyébként a szabványos dspy.LM-et.
    """
    if settings.pipeline.use_pi_auth:
        # A Pi Agent GLM előfizetés (zai-glm) közvetlen használata.
        # A dspy_lm_auth csak OpenAI Codex/ChatGPT route-okat ismer,
        # ezert a GLM kulcsot közvetlenül a Pi auth fájlból olvassuk.
        import json

        pi_auth_path = Path.home() / ".pi" / "agent" / "auth.json"
        if not pi_auth_path.exists():
            raise RuntimeError(
                "A pipeline.use_pi_auth=True, de nem található a Pi Agent "
                "auth fájl (~/.pi/agent/auth.json)."
            )

        auth_data = json.loads(pi_auth_path.read_text(encoding="utf-8"))

        # Preferált sorrend: GLM előfizetés -> Kimi -> OpenAI Codex
        provider_keys = ["zai-glm", "kimi-coding", "openai-codex"]
        api_key = None
        for provider in provider_keys:
            cred = auth_data.get(provider, {})
            # Kulcs neve lehet 'apiKey', 'key', vagy 'access' a provider-től függően
            api_key = cred.get("apiKey") or cred.get("key") or cred.get("access")
            if api_key:
                break

        if not api_key:
            raise RuntimeError(
                "Nem található API kulcs a Pi auth fájlban a támogatott "
                f"provider-ek között: {provider_keys}"
            )

        # A GLM/Kimi API-k OpenAI-kompatibilisak.
        # LiteLLM: "openai/<model>" + api_base + api_key
        lm = dspy.LM(
            settings.models.main,
            api_key=api_key,
            api_base=settings.pipeline.api_base,
            temperature=settings.pipeline.default_temperature,
            max_tokens=settings.pipeline.max_tokens,
        )
    else:
        lm = dspy.LM(
            settings.models.main,
            temperature=settings.pipeline.default_temperature,
            max_tokens=settings.pipeline.max_tokens,
        )

    dspy.configure(lm=lm, track_usage=True)


# ---------------------------------------------------------------------------
# Fő orchestrátor
# ---------------------------------------------------------------------------

def generate_kb_article(
    story_identifier: str,
    client: ServiceNowClientProtocol,
    settings: Settings | None = None,
    *,
    program: StoryToKBArticle | None = None,
    push: bool = True,
    force_update: bool = False,
) -> KBArticle:
    """Lefuttatja a teljes pipeline-t: Story → KB Article.

    Args:
        story_identifier: a Story száma (STRY...) vagy sys_id-ja.
        client: a ServiceNow client (vagy mock), ami teljesíti a Protocol-t.
        settings: ha None, akkor load_settings() segítségével tölti be.
        program: ha None, egy új StoryToKBArticle()-t hoz létre. Tesztelésnél
            előre konfigurált/mock programot is át lehet adni.
        push: ha True, a cikket visszaírja a ServiceNow KB-be a client-tel.
            dry_run módban ez automatikusan False lesz.
        force_update: ha True, és már létezik KB cikk a Story-hoz, a pipeline
            felülírja (frissíti) a meglévőt ahelyett, hogy hibát dobna.

    Returns:
        A generált KBArticle (push esetén a sys_id-jával kitöltve).

    Raises:
        ConfigError: ha a settings érvénytelen.
        A client hibái (pl. StoryNotFound) továbbterjednek.
    """
    # 1. Settings betöltése (ha nem megadva)
    if settings is None:
        settings = load_settings()

    # 2. Story lekérése
    story = client.get_story(story_identifier)

    # 3. Story szöveggé egyítése
    story_text = assemble_story_text(story, settings)

    # 3b. Update Set módosítások hozzáfűzése (ha vannak)
    update_set_summary = ""
    update_set_payloads = ""
    try:
        update_set_summary, update_set_payloads = client.get_update_set_changes(story_identifier)
        if update_set_summary:
            story_text += "\n\n" + update_set_summary
            logger.info("Update Set módosítások hozzáadva a Story szövegéhez.")
    except Exception as exc:
        # Ne döjjön le a pipeline, ha az Update Set lekérés sikertelen
        logger.warning("Update Set lekérés sikertelen: %s", exc)

    # 4. Dry-run: a program hívás kihagyása (nincs LM), mock cikk a Story-ból
    if settings.dry_run:
        article = _mock_article_from_story(story, settings)
    else:
        # 5. LM konfigurálása + program futtatása
        configure_lm(settings)
        if program is None:
            program = StoryToKBArticle()

        pred = program(
            story_text=story_text,
            update_set_payloads=update_set_payloads,
            category=settings.snow.default_category,
            knowledge_base_id=settings.snow.knowledge_base_id,
        )
        article: KBArticle = pred.article
        article.source_story = story_identifier  # Duplikáció megakadályozása

    # 6. Push a ServiceNow KB-be (ha kértük és nem dry_run)
    if push and not settings.dry_run:
        # Duplikáció ellenőrzése
        existing_sys_id = client.find_existing_kb_article(story_identifier)
        
        if existing_sys_id and not force_update:
            # US2: Ha már létezik cikk és nem kérték a frissítést, hibát dobunk
            # (A server.py a 409-es hibakódot fogja returnszni ebből)
            raise DuplicateKBError(
                f"Már létezik KB cikk ehhez a Story-hoz (sys_id: {existing_sys_id}).",
                existing_sys_id=existing_sys_id,
            )
        
        sys_id = client.create_kb_article(
            article, 
            story_sys_id=story.sys_id, 
            existing_sys_id=existing_sys_id or "",
        )
        # Visszaírjuk a sys_id-t az article-re (új mezővel bővítjük)
        return _KBArticleWithSysId(article, sys_id)

    return article


# ---------------------------------------------------------------------------
# Helper: article + sys_id pár (a push eredménye)
# ---------------------------------------------------------------------------

class _KBArticleWithSysId(KBArticle):
    """KBArticle, ami tartalmazza a létrehozott cikk sys_id-ját (push után)."""

    sys_id: str = ""

    def __init__(self, base: KBArticle, sys_id: str, **kwargs):
        super().__init__(
            title=base.title,
            html=base.html,
            category=base.category,
            knowledge_base_id=base.knowledge_base_id,
            **kwargs,
        )
        self.sys_id = sys_id


# ---------------------------------------------------------------------------
# Helper: mock cikk dry-run-hoz
# ---------------------------------------------------------------------------

def _mock_article_from_story(story: StoryData, settings: Settings) -> KBArticle:
    """Dry-run módban generál egy egyszerű mock cikket a Story adataiból.

    Nem hív LM-et — a Story short_description-ből és a lényeges mezőkből
    épít fel egy HTML vázat. Ez teszi lehetővé a teljes pipeline tesztelését
    LM kulcs nélkül.
    """
    title = (
        story.short_description[:120]
        if story.short_description
        else f"Story {story.number}"
    )

    sections_html = []
    if story.description:
        sections_html.append(f"<h2>Problem</h2><p>{story.description}</p>")
    if story.u_technical_specification:
        sections_html.append(
            f"<h2>Technical Details</h2><p>{story.u_technical_specification}</p>"
        )
    if story.work_notes:
        sections_html.append(f"<h2>Work Notes</h2><p>{story.work_notes}</p>")
    if not sections_html:
        sections_html.append("<p>(Nincs tartalom a Story-ban.)</p>")

    html = "\n".join(sections_html)

    return KBArticle(
        title=title,
        html=html,
        category=settings.snow.default_category,
        knowledge_base_id=settings.snow.knowledge_base_id,
    )
