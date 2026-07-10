"""schemas.py — Pydantic adatmodellek a pipeline számára.

Három fő modell:
  - StoryData        : a ServiceNow-ból lekért Story mezői (bemenet kontextus).
  - ArticleSections  : a pipeline köztes állapota (Draft kimenete, Format bemenete).
  - KBArticle        : a végső, ServiceNow-ba írandó Knowledge Base cikk.

Típusos szerződés: a DSPy Signatures és a ServiceNowClient is ezekre hivatkoznak.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Célközönség, amelyre a cikket szabjuk.
# Literal-ként definiálva, hogy a DSPy Signature-ökben is típusos mezőként használható.
Audience = Literal["helpdesk", "end-user", "developer"]


class StoryData(BaseModel):
    """Egy ServiceNow Story adatai (a config.story_fields-ben felsorolt mezők).

    A `extra="ignore"` miatt a ServiceNow-ból érkező egyéb mezők nem törnek meg
    a modellt — csak a deklaráltak kerülnek be. Az összes szöveges mező
    alapértelmezetten üres string, hogy a mock/részleges adatok is betölthetők
    legyenek (dry_run, teszt).
    """

    model_config = ConfigDict(extra="ignore")

    # --- Azonosítók ---
    number: str = Field(default="", description="Story száma, pl. 'STRY0012345'")
    sys_id: str = Field(default="", description="ServiceNow sys_id (32 karakter)")

    # --- Tartalmi mezők (a story_fields sorrendje) ---
    short_description: str = Field(default="", description="Rövid cím/összefoglaló")
    description: str = Field(default="", description="Részletes leírás")
    acceptance_criteria: str = Field(default="", description="Elfogadási kritériumok")
    u_technical_specification: str = Field(
        default="",
        description="Egyéni technikai specifikáció mező (ServiceNow u_ prefix)",
    )
    work_notes: str = Field(default="", description="Munkajegyzetek (journal, egyesítve)")
    comments: str = Field(default="", description="Kommentek (journal, egyesítve)")
    state: str = Field(default="", description="Story állapota, pl. 'Closed Complete'")
    assigned_to: str = Field(default="", description="Fejlesztő (display value)")


class ArticleSections(BaseModel):
    """A pipeline köztes állapota: a Draft lépés kimenete, a Format lépés bemenete.

    Ezek a strukturált részek készülnek el érveléssel, mielőtt HTML-lé formázódnak.
    """

    title: str = Field(..., description="Cikk címe")
    problem: str = Field(..., description="Mi volt a probléma / miért kellett a változás")
    solution_steps: list[str] = Field(
        ..., description="Reprodukálható lépések, sorszámozva"
    )
    summary: str = Field(..., description="1-2 mondatos absztrakt a cikk tetejére")
    audience: Audience = Field(default="helpdesk", description="Célközönség")

    @field_validator("solution_steps")
    @classmethod
    def _non_empty_steps(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("solution_steps nem lehet üres lista")
        return v

    @field_validator("title")
    @classmethod
    def _title_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title nem lehet üres")
        return v


class KBArticle(BaseModel):
    """A végső, ServiceNow KB-be írandó cikk.

    A `title` és `html` a cikk tartalmát adják; a `category` és
    `knowledge_base_id` a besorolást. A knowledge_base_id alapból a
    config.snow.knowledge_base_id-ből jön, de a create-kor felülírható.
    """

    title: str = Field(..., description="KB cikk címe (short_description)")
    html: str = Field(..., description="ServiceNow-kompatibilis HTML törzs")
    category: str = Field(default="General", description="KB kategória neve vagy sys_id")
    knowledge_base_id: str = Field(default="", description="Cél KB sys_id")

    @field_validator("title")
    @classmethod
    def _title_length(cls, v: str) -> str:
        if not (8 <= len(v) <= 120):
            raise ValueError(
                f"title hossza {len(v)} — 8..120 karakter között kell lennie"
            )
        return v

    @field_validator("html")
    @classmethod
    def _html_has_block(cls, v: str) -> str:
        """A HTML tartalmazzon legalább egy blokk-szintű elemet."""
        lowered = v.lower()
        if "<p>" not in lowered and "<ol" not in lowered and "<ul" not in lowered:
            raise ValueError(
                "html legalább egy <p>, <ol> vagy <ul> blokkot tartalmazzon"
            )
        return v
