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

from typing import Protocol

import dspy

from snow_kb.config import Settings, load_settings
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
    megfigyelhetőséghez kell.
    """
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

    # 4. LM konfigurálása (csak ha nem dry_run — dry_run-ban a program mock)
    if not settings.dry_run:
        configure_lm(settings)

    # 5. Program futtatása
    if program is None:
        program = StoryToKBArticle()

    pred = program(
        story_text=story_text,
        category=settings.snow.default_category,
        knowledge_base_id=settings.snow.knowledge_base_id,
    )
    article: KBArticle = pred.article

    # 6. Push a ServiceNow KB-be (ha kértük és nem dry_run)
    if push and not settings.dry_run:
        sys_id = client.create_kb_article(article)
        # Visszaírjuk a sys_id-t az article-re (új mezővel bővítjük)
        # a KBArticle nem tartalmaz sys_id mezőt; a hívó kapja meg külön
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
