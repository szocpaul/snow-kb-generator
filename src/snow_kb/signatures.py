"""signatures.py — DSPy Signatures for the steps of the Story → KB pipeline.

Three Signatures, each with a clean Input/Output contract:
  - ExtractChange : Story text → structured change information
  - DraftSections : extracted info → KB article sections (title, problem, solution, summary)
  - FormatKB      : sections → ServiceNow-compatible HTML

The instruction comes from the docstring of every Signature — there is NO hardcoded prompt.
The predictors (Predict / ChainOfThought) are attached to them in program.py.

The field names strictly match the Pydantic models of schemas.py, so that the
The steps of the program Forward should typically pass the data along.
"""

from __future__ import annotations

import dspy


# ---------------------------------------------------------------------------
# 0. AnalyzeChanges (RLM) — Recursively analyzes the large changes
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
# 1. ExtractChange — extracts what happened from the Story text
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
# 2. DraftSections — edits KB article sections from the extracted info
# ---------------------------------------------------------------------------

class DraftSections(dspy.Signature):
    """Draft Knowledge Base article sections from the extracted change info.
    
    CRITICAL INSTRUCTION: You MUST strictly follow the exact sections, headings, 
    and structure provided in the `template_context`. Do not invent your own 
    headings or sections. Map the extracted change info into the specific 
    sections required by the team's template.
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
# 3. FormatKB — converts the sections into ServiceNow-compatible HTML
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
