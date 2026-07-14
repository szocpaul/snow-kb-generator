"""pipeline.py — the end-to-end orchestrator: fetch → assemble → generate → push.

This layer connects:
  - the ServiceNow client (Story fetch + KB creation)
  - a DSPy programot (StoryToKBArticle)
  - the configuration (Settings)

The program (program.py) knows nothing about ServiceNow. The client
(servicenow_client.py) knows nothing about DSPy. This module is the glue between them.

It expects the ServiceNowClient in the form of a Protocol (an interface), so the
pipeline can also be tested with a mock client while the real client is not implemented.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

import dspy

from snow_kb.config import Settings, load_settings

logger = logging.getLogger(__name__)
from snow_kb.program import StoryToKBArticle
from snow_kb.schemas import KBArticle, StoryData


# ---------------------------------------------------------------------------
# The ServiceNowClient Protocol (interface)
# ---------------------------------------------------------------------------

class ServiceNowClientProtocol(Protocol):
    """The ServiceNow client interface expected by the pipeline.

    The real implementation (servicenow_client.py) will implement this.
    The pipeline calls only these two methods — it knows nothing about the HTTP details.
    """

    def get_story(self, story_identifier: str) -> StoryData: ...

    def create_kb_article(self, article: KBArticle) -> str:
        """Returns the sys_id of the new KB article."""
        ...

    def get_update_set_changes(self, update_set_name: str) -> str:
        """Returns the modifications of the Update Set (optional, may be empty)."""
        ...


# ---------------------------------------------------------------------------
# Merging the Story into a single text
# ---------------------------------------------------------------------------

# The field label map: human readable labels for the internal field names.
# Only the content fields that go into the context (not the identifiers).
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
    """Merges the fields of the Story into a single labelled text.

    It goes through the fields in the order of config.story_fields and gives every
    field a heading (e.g. "## Description: ..."). It skips the empty fields — they
    would only clutter the context with empty sections.

    This text is the input of the ExtractChange Signature (story_text).

    Args:
        story: the data of the Story fetched from ServiceNow.
        settings: if given, the order of the story_fields is taken from here;
            otherwise it starts from the order of the StoryData fields.

    Returns:
        A single text, split into sections, with labels.
    """
    # The order of the fields to process
    field_order: list[str]
    if settings is not None:
        field_order = settings.story_fields
    else:
        field_order = list(_FIELD_LABELS.keys())

    sections: list[str] = []

    # The Story number goes to the top (if there is one)
    if story.number:
        sections.append(f"# Story: {story.number}")

    # Content fields, labelled, the empty ones skipped
    for field_name in field_order:
        value = getattr(story, field_name, None)
        if not value or not str(value).strip():
            continue
        label = _FIELD_LABELS.get(field_name, field_name.replace("_", " ").title())
        sections.append(f"## {label}\n{value}")

    if not sections:
        return "(The Story contains no processable content.)"

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# LM configuration (according to dspy-fundamentals / dspy-advanced-workflow)
# ---------------------------------------------------------------------------

def configure_lm(settings: Settings) -> None:
    """Configures the DSPy LM globally from the settings.

    According to the skill: dspy.configure(lm=..., track_usage=True) — globally,
    override only in justified cases per module. The track_usage for the cost/latency
    is needed for observability.

    If settings.pipeline.use_pi_auth is True, it uses the dspy_lm_auth.LM class
    (Pi Agent GLM subscription for authentication). Otherwise the standard dspy.LM.
    """
    if settings.pipeline.use_pi_auth:
        # Direct use of the Pi Agent GLM subscription (zai-glm).
        # The dspy_lm_auth only knows the OpenAI Codex/ChatGPT routes,
        # therefore we read the GLM key directly from the Pi auth file.
        import json

        pi_auth_path = Path.home() / ".pi" / "agent" / "auth.json"
        if not pi_auth_path.exists():
            raise RuntimeError(
                "pipeline.use_pi_auth=True, but the Pi Agent "
                "auth file (~/.pi/agent/auth.json) was not found."
            )

        auth_data = json.loads(pi_auth_path.read_text(encoding="utf-8"))

        # Preferred order: GLM subscription -> Kimi -> OpenAI Codex
        provider_keys = ["zai-glm", "kimi-coding", "openai-codex"]
        api_key = None
        for provider in provider_keys:
            cred = auth_data.get(provider, {})
            # The key name can be 'apiKey', 'key' or 'access' depending on the provider
            api_key = cred.get("apiKey") or cred.get("key") or cred.get("access")
            if api_key:
                break

        if not api_key:
            raise RuntimeError(
                "No API key found in the Pi auth file among the supported "
                f"providers: {provider_keys}"
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
# Main orchestrator
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
        story_identifier: the number of the Story (STRY...) or its sys_id.
        client: the ServiceNow client (or mock) that implements the Protocol.
        settings: if None, loads them using load_settings().
        program: if None, creates a new StoryToKBArticle(). When testing
            you can also pass a pre-configured/mock program.
        push: if True, writes the article back to the ServiceNow KB with the client.
            in dry_run mode this will automatically be False.

    Returns:
        The generated KBArticle (filled with its sys_id in case of push).

    Raises:
        ConfigError: if the settings are invalid.
        The client errors (e.g. StoryNotFound) propagate.
    """
    # 1. Load the settings (if not given)
    if settings is None:
        settings = load_settings()

    # 2. Fetch the Story
    story = client.get_story(story_identifier)

    # 3. Merging the Story into a single text
    story_text = assemble_story_text(story, settings)

    # 3b. Appending the Update Set modifications (if any)
    try:
        update_set_changes = client.get_update_set_changes(story_identifier)
        if update_set_changes:
            story_text += "\n\n" + update_set_changes
            logger.info("Update Set modifications added to the Story text.")
    except Exception as exc:
        # The pipeline must not crash if the Update Set fetch fails
        logger.warning("Update Set fetch failed: %s", exc)

    # 4. Dry-run: skipping the program call (no LM), mock article from the Story
    if settings.dry_run:
        article = _mock_article_from_story(story, settings)
    else:
        # 5. LM configuration + running the program
        configure_lm(settings)
        if program is None:
            program = StoryToKBArticle()

        pred = program(
            story_text=story_text,
            category=settings.snow.default_category,
            knowledge_base_id=settings.snow.knowledge_base_id,
        )
        article: KBArticle = pred.article

    # 6. Push to the ServiceNow KB (if requested and not dry_run)
    if push and not settings.dry_run:
        sys_id = client.create_kb_article(article, story_sys_id=story.sys_id)
        # We write the sys_id back to the article (extending it with a new field)
        # the KBArticle does not contain a sys_id field; the caller receives it separately
        return _KBArticleWithSysId(article, sys_id)

    return article


# ---------------------------------------------------------------------------
# Helper: the article + sys_id pair (the result of the push)
# ---------------------------------------------------------------------------

class _KBArticleWithSysId(KBArticle):
    """A KBArticle that contains the sys_id of the created article (after the push)."""

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
# Helper: mock article for the dry-run
# ---------------------------------------------------------------------------

def _mock_article_from_story(story: StoryData, settings: Settings) -> KBArticle:
    """Generates a simple mock article from the Story data in dry-run mode.

    It does not call an LM — it builds an HTML skeleton from the Story's
    short_description and the essential fields. This makes it possible to test
    the whole pipeline without an LM key.
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
        sections_html.append("<p>(There is no content in the Story.)</p>")

    html = "\n".join(sections_html)

    return KBArticle(
        title=title,
        html=html,
        category=settings.snow.default_category,
        knowledge_base_id=settings.snow.knowledge_base_id,
    )
