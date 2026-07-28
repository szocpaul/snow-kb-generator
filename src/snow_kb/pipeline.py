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
from snow_kb.errors import MissingAssignmentGroupError

logger = logging.getLogger(__name__)


class DuplicateKBError(Exception):
    """Raised when a KB article already exists for the Story and force_update=False."""

    def __init__(self, message: str, existing_sys_id: str = ""):
        super().__init__(message)
        self.existing_sys_id = existing_sys_id
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

    def get_update_set_changes(self, update_set_name: str) -> tuple[str, str]:
        """Returns the modifications of the Update Set (summary, raw_payloads)."""
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


def sanitize_html_field(value: str) -> str:
    """An HTML field value → plain text for the story_text.

    The gold dataset (examples 1-5) uses plain text in the fields — for a
    Story-k viszont nyers HTML-t tartalmaznak (style-blokkok, tagek). A
    consistent production input we delete the rendering noise, then turn the HTML
    structure (headings, list items, paragraphs) into line breaks, and finally
    remove all the tags.
    """
    import re

    if not value:
        return value
    cleaned = re.sub(r"<style[^>]*>.*?</style>", "", value, flags=re.DOTALL)
    cleaned = re.sub(r"<script[^>]*>.*?</script>", "", cleaned, flags=re.DOTALL)
    # Block-level elements → line breaks (the structure stays readable)
    cleaned = re.sub(r"<li[^>]*>", "\n- ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</(h[1-6]|p|ul|ol|li|tr|table|div|blockquote)>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
    # Delete every remaining tag, convert the HTML entities back
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    import html as _html

    cleaned = _html.unescape(cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


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

    # Content fields, labelled, the empty ones skipped, the HTML noise cleaned
    for field_name in field_order:
        value = getattr(story, field_name, None)
        if not value or not str(value).strip():
            continue
        value = sanitize_html_field(str(value))
        if not value:
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

    Ha settings.pipeline.task_model == "kimi", a Kimi K3 a task modell
    (auto-refreshing OAuth token, strong baseline: 0.655 without GEPA).
    If settings.pipeline.use_pi_auth is True, it uses the dspy_lm_auth.LM class
    (Pi Agent GLM subscription for authentication). Otherwise the standard dspy.LM.
    """
    if settings.pipeline.task_model == "kimi":
        # Kimi K3 task model (Kimi-direct architecture): a strong model, GEPA is
        # not needed for the good quality. The token auto-refreshes from the pi auth.json.
        from eval.gepa_optimize import _RefreshingKimiLM

        lm = _RefreshingKimiLM(
            "openai/k3",
            api_key="",  # the _RefreshingKimiLM refreshes it from the auth.json on every call
            api_base="https://api.kimi.com/coding/v1",
            temperature=1.0,  # K3 only accepts temperature=1
            max_tokens=settings.pipeline.max_tokens,
        )
    elif settings.pipeline.use_pi_auth:
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
        # A local or custom endpoint (e.g. llama.cpp, Ollama)
        lm_kwargs = {
            "temperature": settings.pipeline.default_temperature,
            "max_tokens": settings.pipeline.max_tokens,
        }
        # If api_base is given, we use it (e.g. a local llama.cpp)
        if settings.pipeline.api_base:
            lm_kwargs["api_base"] = settings.pipeline.api_base
            lm_kwargs["api_key"] = "not-needed"  # For local endpoints
        lm = dspy.LM(settings.models.main, **lm_kwargs)

    dspy.configure(lm=lm, track_usage=True)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def strip_na_only_sections(html: str) -> str:
    """Removes the N/A-only sections (evidence-first: omit, not an N/A placeholder).

    Every <h2> section whose content is ~empty or only 'N/A' is deleted.
    A deterministic post-process against the 35B habit of writing 'N/A' instead of omitting.
    """
    import re

    from eval.metric import _section_is_na_only

    removed = []
    for heading in re.findall(r"<h2[^>]*>(.*?)</h2>", html):
        if _section_is_na_only(html, heading):
            removed.append(heading)
            html = re.sub(
                r"\s*<h2[^>]*>\s*" + re.escape(heading) + r"\s*</h2>.*?(?=<h2|$)",
                "\n",
                html,
                flags=re.DOTALL | re.IGNORECASE,
            )
    if removed:
        logger.info("strip_na_only_sections: %d sections removed: %s", len(removed), removed)
    return html


def normalize_code_tags(html: str) -> str:
    """Replaces the <code> tags with <strong> (grey background in the KB view — permanently forbidden).

    Deterministic post-process: the 35B model may generate <code> even against the
    instruction, this guardrail normalizes every article.
    """
    import re

    if "<code" not in html:
        return html
    n = len(re.findall(r"<code", html))
    logger.info("normalize_code_tags: %d db <code> → <strong> csere", n)
    return re.sub(r"<code[^>]*>(.*?)</code>", r"<strong>\1</strong>", html, flags=re.DOTALL)


def strip_direction_violating_sections(html: str, story_text: str) -> str:
    """Removes the direction-violating sections (spec 007 guardrail).

    For an outbound story it removes the 'Inbound Technical Implementation' section
    (and vice versa) from the HTML entirely. The 35B task model may fill it in even
    against the explicit instruction — this is the deterministic last line of defence.
    With the 'both'/'unknown' direction it leaves the HTML unchanged.
    """
    import re

    from eval.metric import detect_direction

    forbidden = {"inbound": "Outbound Technical Implementation", "outbound": "Inbound Technical Implementation"}
    direction = detect_direction(story_text)
    if direction not in forbidden:
        return html

    heading = forbidden[direction]
    if not re.search(r"<h2[^>]*>\s*" + re.escape(heading) + r"\s*</h2>", html, re.IGNORECASE):
        return html

    logger.warning("Direction guardrail: the '%s' section removed (%s story — content or N/A)", heading, direction)
    return re.sub(
        r"\s*<h2[^>]*>\s*" + re.escape(heading) + r"\s*</h2>.*?(?=<h2|$)",
        "\n",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )


def strip_hallucinated_references(html: str, story_text: str, known_refs: str = "") -> str:
    """Removes the hallucinated KB references from the generated HTML (spec 004/005).

    A KB reference (KB + >=6 digits) is hallucinated if it does not appear in the
    story_text OR in the known_refs (e.g. the real hits of the ServiceNow KB search
    — spec 005). It removes the <li> elements containing such a reference and
    replaces the other occurrences with the KBXXXXXXX placeholder.
    It never touches the real identifiers.
    """
    import re

    pattern = re.compile(r"\bKB\d{6,}\b")
    known_refs_set = set(pattern.findall(story_text)) | set(pattern.findall(known_refs))
    hallucinated = set(pattern.findall(html)) - known_refs_set
    if not hallucinated:
        return html

    logger.warning("Removing hallucinated KB references: %s", sorted(hallucinated))

    cleaned = html
    # 1. Complete removal of the <li> elements containing a hallucinated reference
    for ref in hallucinated:
        cleaned = re.sub(
            r"[ \t]*<li[^>]*>[^<]*" + re.escape(ref) + r"[^<]*</li>\s*",
            "",
            cleaned,
        )
    # 2. Replacing the remaining occurrences with the placeholder
    for ref in hallucinated:
        cleaned = cleaned.replace(ref, "KBXXXXXXX")
    return cleaned


def _load_program(program_path: str | None = None) -> StoryToKBArticle:
    """Loads the (GEPA-optimized) program, if the JSON file exists.

    Fallback: if there is no program_path, or the file is missing/broken, the basic
    returns a StoryToKBArticle().
    """
    program = StoryToKBArticle()
    if program_path:
        from pathlib import Path

        path = Path(program_path)
        if path.exists():
            try:
                program.load(str(path))
                logger.info("Optimized program loaded: %s", path)
            except Exception as exc:
                logger.warning(
                    "Failed to load the optimized program (%s), using the basic program.",
                    exc,
                )
        else:
            logger.info("No optimized program (%s), using the basic program.", path)
    return program


def generate_kb_article(
    story_identifier: str,
    client: ServiceNowClientProtocol,
    settings: Settings | None = None,
    *,
    program: StoryToKBArticle | None = None,
    program_path: str | None = None,
    push: bool = True,
    force_update: bool = False,
) -> KBArticle:
    """Lefuttatja a teljes pipeline-t: Story → KB Article.

    Args:
        story_identifier: the number of the Story (STRY...) or its sys_id.
        client: the ServiceNow client (or mock) that implements the Protocol.
        settings: if None, loads them using load_settings().
        program: if None, creates a new StoryToKBArticle(). When testing
            you can also pass a pre-configured/mock program.
        program_path: if given (and program is None), the optimized program
            loads it from this JSON file (GEPA export, see artifacts/program.json).
            If the file does not exist or is broken, it falls back to the basic StoryToKBArticle().
        push: if True, writes the article back to the ServiceNow KB with the client.
            in dry_run mode this will automatically be False.
        force_update: if True, and a KB article already exists for the Story, the pipeline
            overwrites (updates) the existing one instead of raising an error.

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

    # 2b. Team-Based Template: check the assignment_group
    if not story.assignment_group:
        raise MissingAssignmentGroupError(
            "The assignment_group field is not filled in on the Story."
        )
    
    template_context = ""
    try:
        template_context = client.get_team_template(story.assignment_group) or ""
        if template_context:
            logger.info("Team specific template loaded: %s", story.assignment_group)
    except Exception as exc:
        logger.warning("Template fetch failed: %s", exc)

    # 3. Merging the Story into a single text
    story_text = assemble_story_text(story, settings)

    # 3b. Append the Update Set modifications (if there are any)
    update_set_summary = ""
    update_set_payloads = ""
    try:
        update_set_summary, update_set_payloads = client.get_update_set_changes(story_identifier)
        if update_set_summary:
            story_text += "\n\n" + update_set_summary
            logger.info("Update Set modifications added to the Story text.")
    except Exception as exc:
        # The pipeline must not crash if the Update Set fetch fails
        logger.warning("Update Set fetch failed: %s", exc)

    # 3c. Searching the related KB articles (spec 005) — real references for the
    # "Table of related KB articles" section (instead of a hallucination)
    related_articles_context = ""
    try:
        search = getattr(client, "search_kb_articles", None)
        if search and story.short_description:
            hits = search(story.short_description, limit=5)
            if hits:
                related_articles_context = "\n".join(
                    f"{h['number']} | {h['short_description']}" for h in hits
                )
                logger.info("Related KB articles: %d hits", len(hits))
    except Exception as exc:
        # The pipeline must not crash if the KB search fails
        logger.warning("Related KB search failed: %s", exc)

    # 4. Dry-run: skipping the program call (no LM), mock article from the Story
    if settings.dry_run:
        article = _mock_article_from_story(story, settings)
    else:
        # 5. LM configuration + running the program
        configure_lm(settings)
        if program is None:
            program = _load_program(program_path)

        pred = program(
            story_text=story_text,
            update_set_payloads=update_set_payloads,
            template_context=template_context,
            related_articles_context=related_articles_context,
            category=settings.snow.default_category,
            knowledge_base_id=settings.snow.knowledge_base_id,
        )
        article: KBArticle = pred.article
        article.source_story = story_identifier  # prevents duplication
        # Format normalization: <code> → <strong> (the grey background is forbidden)
        article.html = normalize_code_tags(article.html)
        # Spec 007 guardrail: removing the direction-violating sections
        article.html = strip_direction_violating_sections(article.html, story_text)
        # Evidence-first guardrail: removing the N/A-only sections (omit, not N/A)
        article.html = strip_na_only_sections(article.html)
        # Spec 004/005 guardrail: removing the hallucinated KB references BEFORE the push
        # (the real search hits are protected as known_refs)
        article.html = strip_hallucinated_references(
            article.html, story_text, known_refs=related_articles_context
        )

    # 6. Push to the ServiceNow KB (if requested and not dry_run)
    if push and not settings.dry_run:
        # Duplication check
        existing_sys_id = client.find_existing_kb_article(story_identifier)
        
        if existing_sys_id and not force_update:
            # US2: if an article already exists and no update was requested, we raise an error
            # (server.py turns this into the 409 status code)
            raise DuplicateKBError(
                f"A KB article already exists for this Story (sys_id: {existing_sys_id}).",
                existing_sys_id=existing_sys_id,
            )
        
        sys_id = client.create_kb_article(
            article, 
            story_sys_id=story.sys_id, 
            existing_sys_id=existing_sys_id or "",
        )
        # We write the sys_id back into the article (extending it with a new field)
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
