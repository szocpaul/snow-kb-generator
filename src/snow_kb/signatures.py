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
    """Draft Knowledge Base article sections from the extracted change info,
    tailored to the audience.

    Write a clear, actionable title; a concise problem statement explaining
    why the change was needed; a numbered-style solution with reproducible
    steps; and a one-or-two sentence summary for the top of the article.
    Match the depth and terminology to the audience.
    """
    change_summary: str = dspy.InputField(desc="What changed (from ExtractChange).")
    key_steps: list[str] = dspy.InputField(desc="Reproducible steps (from ExtractChange).")
    audience: str = dspy.InputField(desc="Target audience: helpdesk | end-user | developer.")

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
    """Format drafted article sections into ServiceNow-compatible HTML.

    Produce clean, semantic HTML suitable for a ServiceNow Knowledge Base
    article body. Use <h2> for section headings, <p> for paragraphs, and
    <ol> with <li> for the solution steps. Do NOT include <html>, <head>,
    or <body> tags — only the body fragment.
    """
    title: str = dspy.InputField(desc="Article title.")
    problem: str = dspy.InputField(desc="Problem statement.")
    solution_steps: list[str] = dspy.InputField(desc="Ordered solution steps.")
    summary: str = dspy.InputField(desc="Article summary.")

    html: str = dspy.OutputField(
        desc="ServiceNow KB article body as HTML. Must contain at least one "
             "<p>, <ol>, or <ul> block. No <html>/<head>/<body> wrappers."
    )
