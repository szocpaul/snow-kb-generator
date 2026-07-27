"""signatures.py — DSPy Signatures a Story → KB pipeline lépéseihez.

Három Signature, mindegyik tiszta Input/Output szerződés:
  - ExtractChange : Story szöveg → strukturált változási információ
  - DraftSections : kinyert info → KB cikk részei (title, problem, solution, summary)
  - FormatKB      : részek → ServiceNow-kompatibilis HTML

Az instruction minden Signature docstring-jéből jön — NINCS hardcode-olt prompt.
A prediktorok (Predict / ChainOfThought) a program.py-ban kerülnek rájuk.

A mezőnevek szigorúan egyeznek a schemas.py Pydantic modelljeivel, hogy a
program Forward lépései típusosan átadhassák az adatokat.
"""

from __future__ import annotations

import dspy


# ---------------------------------------------------------------------------
# 0. AnalyzeChanges (RLM) — Rekurzívan elemzi a nagy módosításokat
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
    audience: str = dspy.OutputField(
        desc="Primary audience for a KB article: one of "
             "'helpdesk', 'end-user', or 'developer'."
    )


# ---------------------------------------------------------------------------
# 2. DraftSections — a kinyert infóból KB cikk részeket szerkeszt
# ---------------------------------------------------------------------------

class DraftSections(dspy.Signature):
    """Draft Knowledge Base article sections from the extracted change info.
    
    CRITICAL OUTPUT FORMAT INSTRUCTION: 
    You MUST strictly follow the structural outline provided in the `template_context`.
    Do NOT use generic headings like 'Problem' or 'Solution'.
    Instead, map the extracted change info into the EXACT sections and headings demanded by the team's template_context.
    """
    change_summary: str = dspy.InputField(desc="What changed (from ExtractChange).")
    key_steps: list[str] = dspy.InputField(desc="Reproducible steps (from ExtractChange).")
    audience: str = dspy.InputField(desc="Target audience: helpdesk | end-user | developer.")
    template_context: str = dspy.InputField(
        desc="HTML/text example of the team's required structure. Mimic this format.",
        default="",
    )

    title: str = dspy.OutputField(
        desc="Article title, 8-120 characters, descriptive and specific."
    )
    problem: str = dspy.OutputField(
        desc="What was the problem or need that prompted this change? "
             "1-3 sentences."
    )
    solution_steps: list[str] = dspy.OutputField(
        desc="Reproducible solution steps, refined and ordered. Each step "
             "is a single string without numbering prefix."
    )
    summary: str = dspy.OutputField(
        desc="One-or-two sentence abstract for the top of the article."
    )


# ---------------------------------------------------------------------------
# 3. FormatKB — a részeket ServiceNow-kompatibilis HTML-lé alakítja
# ---------------------------------------------------------------------------

class FormatKB(dspy.Signature):
    """Format drafted sections into ServiceNow-compatible HTML.
    
    CRITICAL INSTRUCTION: You MUST strictly follow the exact HTML tags, headings, 
    and overall structure provided in the `template_context`. If the template 
    uses specific <h2> headings (e.g., 'Overview / Summary', 'Inbound Technical Implementation'), 
    you MUST use those exact headings in your output HTML.
    """
    title: str = dspy.InputField(desc="Article title.")
    problem: str = dspy.InputField(desc="Problem statement.")
    solution_steps: list[str] = dspy.InputField(desc="Ordered solution steps.")
    summary: str = dspy.InputField(desc="Article summary.")
    template_context: str = dspy.InputField(
        desc="HTML structure/example to mimic exactly.",
        default="",
    )

    html: str = dspy.OutputField(
        desc="ServiceNow KB article body as HTML. Must contain at least one "
             "<p>, <ol>, or <ul> block. No <html>/<head>/<body> wrappers."
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
    - Do NOT add a "Theme" line or a "Target Audience" section. If the story_context
      mentions a target audience, use it ONLY to adapt the writing style/tone of each
      section (e.g., technical depth for developers, business language for process owners).
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
        "If empty, write 'N/A' in that section."
    )

    html: str = dspy.OutputField(
        desc="A complete ServiceNow KB article in HTML, strictly following the provided html_template."
    )
