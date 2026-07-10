"""program.py — StoryToKBArticle(dspy.Module), a pipeline magja.

The three DSPy Signatures (signatures.py) into a single composite Module chain
chains. This is the "program" that we baseline and optimize with GEPA.

Steps:
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
from snow_kb.signatures import DraftSections, ExtractChange, FormatKB


class StoryToKBArticle(dspy.Module):
    """A DSPy program that generates a KB article from a ServiceNow Story text.

    The category and the knowledge_base_id come from outside the program (from
    pipeline.py, which reads them from the config). The forward() accepts them
    optionally, so that the final KBArticle is complete.
    """

    def __init__(self) -> None:
        super().__init__()
        # Named predictors — GEPA targets these.
        self.extract = dspy.ChainOfThought(ExtractChange)
        self.draft = dspy.ChainOfThought(DraftSections)
        self.format = dspy.Predict(FormatKB)

    def forward(
        self,
        story_text: str,
        *,
        category: str = "General",
        knowledge_base_id: str = "",
    ) -> dspy.Prediction:
        """Runs the three-step pipeline.

        Args:
            story_text: the full Story text (output of assemble_story_text).
            category: KB category (from the config, by default "General").
            knowledge_base_id: target KB sys_id (from the config).

        Returns:
            dspy.Prediction with the following fields:
              - sections: ArticleSections (the output of the Draft step)
              - article: KBArticle (final article)
              - change_summary, key_steps, audience: from the Extract step
                (can be useful for the metric)
        """
        # 1. Extraction: what happened, steps, audience
        extracted = self.extract(story_text=story_text)

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
