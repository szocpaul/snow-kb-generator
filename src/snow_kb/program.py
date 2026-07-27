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
    GenerateKbFromTemplate,
)

# The uniform query of the AnalyzeChanges step (a constant — GEPA does not
# target it, because it is a callsite value, not a signature instruction).
ANALYZE_CHANGES_QUERY = (
    "Extract all technical details: JSDoc comments, descriptions, "
    "function names, and Flow steps."
)


class StoryToKBArticle(dspy.Module):
    """A DSPy program that generates a KB article from a ServiceNow Story text.

    The category and the knowledge_base_id come from outside the program (from
    pipeline.py, which reads them from the config). The forward() accepts them
    optionally, so that the final KBArticle is complete.
    """

    def __init__(self) -> None:
        super().__init__()
        # Named predictors — GEPA targets these.
        self.analyze_changes = dspy.ChainOfThought(AnalyzeChanges)
        self.extract = dspy.ChainOfThought(ExtractChange)
        self.draft = dspy.ChainOfThought(DraftSections)
        self.format = dspy.Predict(FormatKB)
        # New predictor: one-to-one filling of the HTML template
        self.generate_from_template = dspy.Predict(GenerateKbFromTemplate)

    def forward(
        self,
        story_text: str,
        *,
        update_set_payloads: str = "",
        template_context: str = "",
        related_articles_context: str = "",
        category: str = "General",
        knowledge_base_id: str = "",
    ) -> dspy.Prediction:
        """Lefuttatja a pipeline-t.

        Args:
            story_text: the full Story text (the output of assemble_story_text).
            update_set_payloads: the raw XML payloads of the modifications (if any).
            template_context: the team specific KB template (few-shot example).
            category: KB category (from the config, "General" by default).
            knowledge_base_id: target KB sys_id (from the config).

        Returns:
            a dspy.Prediction with the following fields:
              - sections: ArticleSections (the output of the Draft step)
              - article: KBArticle (the final article)
              - change_summary, key_steps, audience: from the Extract step
                (possibly useful for the metric)
        """
        full_context = story_text

        # 0. AnalyzeChanges step: if there are modifications (raw payloads),
        # the GLM extracts the scripts/JSDocs from them. Since GLM-5.2 has a
        # huge (1M token) context window, the 15,000 character limit does not
        # have to be strict, but we keep it for optimization purposes.
        if update_set_payloads:
            # If the payload is very large, we pass only the first 50,000
            # characters so that we do not overload the context unnecessarily.
            payload_snippet = update_set_payloads[:50000]
            if len(update_set_payloads) > 50000:
                payload_snippet += "\n... (payload truncated at 50,000 characters)"
                
            analysis = self.analyze_changes(
                update_set_xml=payload_snippet,
                query=ANALYZE_CHANGES_QUERY,
            )
            full_context += "\n\n## Update Set Technical Summary (via LLM)\n"
            full_context += analysis.technical_summary

        # 1. Extraction: what happened, the steps, the audience
        extracted = self.extract(story_text=full_context)

        # 2. If there is an HTML template, use the one-to-one filling Signature
        if template_context:
            # Template-based generation is much more flexible: it is able to handle any number of sections
            # to handle, because it fills in the HTML structure directly.
            story_context_for_template = (
                f"Change Summary: {extracted.change_summary}\n\n"
                f"Key Steps: {', '.join(extracted.key_steps)}\n\n"
                f"Target Audience (style only, do NOT create a section for it): {extracted.audience}\n\n"
                f"Full Story Context: {full_context}"
            )
            template_result = self.generate_from_template(
                story_context=story_context_for_template,
                html_template=template_context,
                related_articles_context=related_articles_context,
            )
            final_html = template_result.html
            # The title comes from the model (GenerateKbFromTemplate.title); the fallback is
            # extract change_summary, if the field comes back empty.
            final_title = (template_result.title or "").strip()[:120] or extracted.change_summary.split('.')[0][:120] or "KB Article"
            
            article = KBArticle(
                title=final_title,
                html=final_html,
                category=category,
                knowledge_base_id=knowledge_base_id,
            )
            
            return dspy.Prediction(
                sections=ArticleSections(
                    title=final_title,
                    problem=extracted.change_summary,
                    solution_steps=extracted.key_steps,
                    summary=extracted.change_summary,
                    audience=extracted.audience,
                ),
                article=article,
                change_summary=extracted.change_summary,
                key_steps=extracted.key_steps,
                audience=extracted.audience,
            )

        # 2b. If there is NO template: the traditional 3-step pipeline
        drafted = self.draft(
            change_summary=extracted.change_summary,
            key_steps=extracted.key_steps,
            audience=extracted.audience,
            template_context=template_context,
        )

        # 3. Formatting: HTML body
        formatted = self.format(
            title=drafted.title,
            problem=drafted.problem,
            solution_steps=drafted.solution_steps,
            summary=drafted.summary,
            template_context=template_context,
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
