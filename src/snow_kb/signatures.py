"""signatures.py — DSPy Signatures a Story → KB pipeline lépéseihez.

Három élő Signature (spec 009: DraftSections/FormatKB kivezetve):
  - AnalyzeChanges        : Update Set XML → technikai összefoglaló
  - ExtractChange         : Story szöveg → strukturált változási információ
  - GenerateKbFromTemplate: story context + HTML sablon → kész cikk (egyetlen generálási út)

Az instruction minden Signature docstring-jéből jön — NINCS hardcode-olt prompt.
A prediktorok (Predict / ChainOfThought) a program.py-ban kerülnek rájuk.

A mezőnevek szigorúan egyeznek a schemas.py Pydantic modelljeivel, hogy a
program Forward lépései típusosan átadhassák az adatokat.
"""

from __future__ import annotations

from typing import Literal

import dspy


# ---------------------------------------------------------------------------
# 0. AnalyzeChanges — az Update Set XML payloadok technikai elemzése (ChainOfThought)
# ---------------------------------------------------------------------------

class AnalyzeChanges(dspy.Signature):
    """Analyze ServiceNow Update Set changes (XML payloads) and extract a structured
    summary of what was technically modified.

    You are given raw XML payloads from a ServiceNow Update Set. These may contain
    Script Includes, Business Rules, Flow Designer definitions, or ACLs.
    Extract JSDoc comments, descriptions, function signatures, or Flow steps, 
    and compile a concise technical summary of the actual implementation work done.
    """
    update_set_xml: str = dspy.InputField(
        desc="Raw XML payloads from ServiceNow sys_update_xml records."
    )
    query: str = dspy.InputField(
        desc="The instruction on what to extract from the modifications."
    )
    technical_summary: str = dspy.OutputField(
        desc="A concise, structured summary of the technical changes found in the XML data."
    )


# ---------------------------------------------------------------------------
# 1. ExtractChange — Story szövegből kinyeri, mi történt
# ---------------------------------------------------------------------------

class ExtractChange(dspy.Signature):
    """Analyze a completed ServiceNow Story and extract what changed, for whom,
    and the reproducible steps.

    Read the story text carefully. Identify the technical change that was
    implemented, distill it into a one-or-two sentence summary, extract the
    concrete reproducible steps, and determine the primary audience for a
    knowledge base article about this change.
    """
    story_text: str = dspy.InputField(
        desc="The full text of a completed ServiceNow Story, including its "
             "description, technical specification, acceptance criteria, "
             "work notes, and comments — assembled into labeled sections."
    )
    change_summary: str = dspy.OutputField(
        desc="What changed, in one or two sentences. Focus on the outcome, "
             "not the process."
    )
    key_steps: list[str] = dspy.OutputField(
        desc="Concrete, reproducible steps that a reader would follow to "
             "understand or replicate the change. Each step is a single "
             "string, no numbering prefix."
    )
    audience: Literal["helpdesk", "end-user", "developer"] = dspy.OutputField(
        desc="Primary audience for a KB article."
    )


# ---------------------------------------------------------------------------
# 4. GenerateKbFromTemplate — HTML sablon egy-az-egyben kitöltése
# ---------------------------------------------------------------------------

class GenerateKbFromTemplate(dspy.Signature):
    """Generate a complete ServiceNow KB article by filling in an HTML template.

    You are given:
    1. A `story_context`: The extracted summary and technical details of a completed Story.
    2. An `html_template`: An HTML skeleton containing the team's required headings 
       and structure (e.g., <h2>Overview</h2>, <h2>Inbound Technical Implementation</h2>).

    YOUR TASK (CRITICAL):
    You MUST return a single, complete HTML document built from the `html_template`.
    The template is a MENU, not a mandate:
    - Include ONLY the sections the `story_context` supports with concrete evidence.
    - If a section has no supporting evidence in the story, OMIT it entirely
      (do NOT write "N/A" placeholders). No evidence, no section.
    - Corollary: for an outbound-only story, OMIT the 'Inbound Technical Implementation'
      section (and vice versa). Shared components belong to the direction the story
      actually implements.
    - Do NOT invent new headings. Use the template's heading names verbatim.
    - Copy the HTML tags (<h2>, <ul>, <li>, <p>) style from the template for the
      sections you include.
    - NEVER use <code> tags (gray background in the KB view) — use <strong> for
      identifiers, script names, field names, endpoints and API paths instead.
    - Do NOT add a "Theme" line or a "Target Audience" section. If the story_context
      mentions a target audience, use it ONLY to adapt the writing style/tone of each
      section (e.g., technical depth for developers, business language for process owners).

    WRITING STYLE — write like a senior engineer documenting their own work:
    - NEVER use these boilerplate phrases (they make the article sound AI-generated):
      "This document describes", "This document outlines", "This article describes",
      "seamless", "seamlessly", "leverage", "In today's fast-paced world",
      "It is important to note", "plays a crucial role", "In conclusion".
    - State facts directly: name the concrete field, endpoint, script, or value instead
      of generalizing (e.g., "The Business Rule fires when the Incident state changes
      to Escalated (6)", not "A robust mechanism ensures timely synchronization").
    - NEVER invent component names: if the story does not name a Business Rule,
      Script Include, table, or endpoint explicitly, refer to it by its function
      (e.g., "a Business Rule on the incident table") — do not fabricate a
      plausible-looking name, even partially derived from URLs or group names.
    - Vary sentence length and structure; do not start consecutive sentences the same way.
    - Prefer active voice and plain verbs over buzzwords.
    """
    story_context: str = dspy.InputField(
        desc="The extracted summary, change details, and technical implementation info."
    )
    html_template: str = dspy.InputField(
        desc="The exact HTML structure/headings the output MUST follow."
    )
    related_articles_context: str = dspy.InputField(
        desc="REAL related KB articles from ServiceNow, one per line as 'KB<number> | <short_description>'. "
        "Use ONLY these in the 'Table of related KB articles' section — never invent article numbers or titles. "
        "If empty, OMIT the related articles section entirely (no evidence, no section)."
    )

    title: str = dspy.OutputField(
        desc="Article title: one descriptive sentence, max 120 characters, no trailing cut-off words."
    )
    html: str = dspy.OutputField(
        desc="A complete ServiceNow KB article in HTML, strictly following the provided html_template."
    )
