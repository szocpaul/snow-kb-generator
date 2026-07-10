"""schemas.py — Pydantic data models for the pipeline.

Three main models:
  - StoryData        : the Story fields fetched from ServiceNow (input context).
  - ArticleSections  : the intermediate pipeline state (Draft output, Format input).
  - KBArticle        : the final Knowledge Base article to be written to ServiceNow.

Typed contract: the DSPy Signatures and the ServiceNowClient refer to these as well.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# The audience the article is written for.
# Defined as a Literal so that it can also be used as a typed field in the DSPy Signatures.
Audience = Literal["helpdesk", "end-user", "developer"]


class StoryData(BaseModel):
    """The data of a single ServiceNow Story (the fields listed in config.story_fields).

    Thanks to `extra="ignore"`, further fields arriving from ServiceNow do not
    break the model — only the declared ones are taken over. Every text field
    defaults to an empty string so that mock/partial data can also be loaded
    should be (dry_run, test).
    """

    model_config = ConfigDict(extra="ignore")

    # --- Identifiers ---
    number: str = Field(default="", description="Story number, e.g. 'STRY0012345'")
    sys_id: str = Field(default="", description="ServiceNow sys_id (32 characters)")

    # --- Content fields (in story_fields order) ---
    short_description: str = Field(default="", description="Short title / summary")
    description: str = Field(default="", description="Detailed description")
    acceptance_criteria: str = Field(default="", description="Acceptance criteria")
    u_technical_specification: str = Field(
        default="",
        description="Custom technical specification field (ServiceNow u_ prefix)",
    )
    work_notes: str = Field(default="", description="Work notes (journal, merged)")
    comments: str = Field(default="", description="Comments (journal, merged)")
    state: str = Field(default="", description="Story state, e.g. 'Closed Complete'")
    assigned_to: str = Field(default="", description="Developer (display value)")


class ArticleSections(BaseModel):
    """The intermediate pipeline state: the output of the Draft step, the input of the Format step.

    These structured sections are produced with reasoning before they are formatted into HTML.
    """

    title: str = Field(..., description="Article title")
    problem: str = Field(..., description="What the problem was / why the change was needed")
    solution_steps: list[str] = Field(
        ..., description="Reproducible steps, numbered"
    )
    summary: str = Field(..., description="A 1-2 sentence abstract for the top of the article")
    audience: Audience = Field(default="helpdesk", description="Target audience")

    @field_validator("solution_steps")
    @classmethod
    def _non_empty_steps(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("solution_steps must not be an empty list")
        return value

    @field_validator("title")
    @classmethod
    def _title_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title must not be empty")
        return value


class KBArticle(BaseModel):
    """The final article to be written to the ServiceNow KB.

    `title` and `html` carry the content of the article; `category` and
    `knowledge_base_id` carry the classification. The knowledge_base_id comes
    from config.snow.knowledge_base_id by default, but it can be overridden on create.
    """

    title: str = Field(..., description="KB article title (short_description)")
    html: str = Field(..., description="ServiceNow-compatible HTML body")
    category: str = Field(default="General", description="KB category name or sys_id")
    knowledge_base_id: str = Field(default="", description="Target KB sys_id")

    @field_validator("title")
    @classmethod
    def _title_length(cls, value: str) -> str:
        if not (8 <= len(value) <= 120):
            raise ValueError(
                f"title length {len(value)} — it must be between 8 and 120 characters"
            )
        return value

    @field_validator("html")
    @classmethod
    def _html_has_block(cls, value: str) -> str:
        """The HTML must contain at least one block-level element."""
        lowered = value.lower()
        if "<p>" not in lowered and "<ol" not in lowered and "<ul" not in lowered:
            raise ValueError(
                "the html must contain at least one <p>, <ol> or <ul> block"
            )
        return value
