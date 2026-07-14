"""program.py — StoryToKBArticle(dspy.Module), a pipeline magja.

Chains the DSPy Signatures into a single composite Module chain. This is the "program",
which we baseline and optimize with GEPA.

Steps:
  0. AnalyzeChanges (RLM) — If the Update Set is large, it analyzes it recursively (optional)
  1. ExtractChange — extracts the essence of the change from the Story text (ChainOfThought)
  2. DraftSections — edits KB article sections from the extracted info (ChainOfThought)
  3. FormatKB     — converts the sections into ServiceNow-compatible HTML (Predict)

Every predictor gets a NAME so that GEPA can target the reflection separately.
The forward() returns a dspy.Prediction that contains the ArticleSections
(the output of the Draft step) and the final KBArticle.
"""

from __future__ import annotations

import dspy

from snow_kb.schemas import ArticleSections, KBArticle
from snow_kb.signatures import (
    AnalyzeChanges,
    DraftSections,
    ExtractChange,
    FormatKB,
)

# Character limit: if the Update Set payloads together exceed this value,
# switches on the RLM (Recursive Language Model) step, which recursively processes
# the big data. Below that the plain LLM handles the context.
RLM_THRESHOLD_CHARS = 15000


class StoryToKBArticle(dspy.Module):
    """A DSPy program that generates a KB article from a ServiceNow Story text.

    The category and the knowledge_base_id come from outside the program (from
    pipeline.py, which reads them from the config). The forward() accepts them
    optionally, so that the final KBArticle is complete.
    """

    def __init__(self) -> None:
        super().__init__()
        # Named predictors — GEPA targets these.
        # The RLM step (dspy.RLM) is only initialized and run when needed.
        self.analyze_changes = dspy.RLM(
            AnalyzeChanges,
            max_iterations=15,
            max_llm_calls=30,
            max_output_chars=10_000,
        )
        self.extract = dspy.ChainOfThought(ExtractChange)
        self.draft = dspy.ChainOfThought(DraftSections)
        self.format = dspy.Predict(FormatKB)

    def forward(
        self,
        story_text: str,
        *,
        update_set_payloads: str = "",
        category: str = "General",
        knowledge_base_id: str = "",
    ) -> dspy.Prediction:
        """Lefuttatja a pipeline-t.

        Args:
            story_text: the full Story text (output of assemble_story_text).
            update_set_payloads: the raw XML payloads of the modifications (if any).
            category: KB category (from the config, by default "General").
            knowledge_base_id: target KB sys_id (from the config).

        Returns:
            dspy.Prediction with the following fields:
              - sections: ArticleSections (the output of the Draft step)
              - article: KBArticle (final article)
              - change_summary, key_steps, audience: from the Extract step
                (can be useful for the metric)
        """
        full_context = story_text

        # 0. RLM step: It only runs if the raw payloads are large (> 15.000 characters)
        if update_set_payloads and len(update_set_payloads) > RLM_THRESHOLD_CHARS:
            rlm_result = self.analyze_changes(
                context=update_set_payloads,
                query="Extract all technical details: JSDoc comments, descriptions, function names, and Flow steps.",
            )
            full_context += "\n\n## Update Set Technical Summary (via RLM)\n"
            full_context += rlm_result.technical_summary
        elif update_set_payloads:
            # The payload is small, it fits in the context, no RLM needed
            full_context += "\n\n## Update Set Raw Modifications\n"
            full_context += update_set_payloads

        # 1. Extraction: what happened, the steps, the audience
        extracted = self.extract(story_text=full_context)

        # 2. Touch-up: editing sections for the audience
        drafted = self.draft(
            change_summary=extracted.change_summary,
            key_steps=extracted.key_steps,
            audience=extracted.audience,
        )

        # 3. Formatting: HTML body
        formatted = self.format(
            title=drafted.title,
            problem=drafted.problem,
            solution_steps=drafted.solution_steps,
            summary=drafted.summary,
        )

        # Typed intermediate and final objects (schemas.py)
        sections = ArticleSections(
            title=drafted.title,
            problem=drafted.problem,
            solution_steps=drafted.solution_steps,
            summary=drafted.summary,
            audience=extracted.audience,
        )

        article = KBArticle(
            title=drafted.title,
            html=formatted.html,
            category=category,
            knowledge_base_id=knowledge_base_id,
        )

        return dspy.Prediction(
            sections=sections,
            article=article,
            # the outputs of the Extract step are also accessible (for the metric)
            change_summary=extracted.change_summary,
            key_steps=extracted.key_steps,
            audience=extracted.audience,
        )
