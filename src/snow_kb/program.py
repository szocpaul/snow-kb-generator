"""program.py — StoryToKBArticle(dspy.Module), a pipeline magja.

A három DSPy Signature-t (signatures.py) egyetlen összetett Module-láncba
fűzi. Ez a "program", amit baseline-olunk és GEPA-val optimalizálunk.

Lépések:
  1. ExtractChange — Story szövegből kinyeri a változás lényegét (ChainOfThought)
  2. DraftSections — kinyert infóból KB cikk részeket szerkeszt (ChainOfThought)
  3. FormatKB     — részeket ServiceNow-kompatibilis HTML-lé alakítja (Predict)

Minden prediktor NEVET kap, hogy a GEPA külön célozhassa a reflection-t.
A forward() egy dspy.Prediction-t ad vissza, ami tartalmazza az ArticleSections-t
(a Draft lépés kimenete) és a végső KBArticle-t.
"""

from __future__ import annotations

import dspy

from snow_kb.schemas import ArticleSections, KBArticle
from snow_kb.signatures import DraftSections, ExtractChange, FormatKB


class StoryToKBArticle(dspy.Module):
    """DSPy program, ami egy ServiceNow Story szövegből KB cikket generál.

    A kategória (category) és a knowledge_base_id a programon kívülről jön
    (a pipeline.py-ból, ami a config-ból olvassa). A forward() ezeket
    opcionálisan elfogadja, hogy a végső KBArticle teljes legyen.
    """

    def __init__(self) -> None:
        super().__init__()
        # Névvel ellátott prediktorok — a GEPA ezeket célozza.
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
        """Lefuttatja a három lépéses pipeline-t.

        Args:
            story_text: a teljes Story szöveg (assemble_story_text kimenete).
            category: KB kategória (config-ból, alapból "General").
            knowledge_base_id: cél KB sys_id (config-ból).

        Returns:
            dspy.Prediction a következő mezőkkel:
              - sections: ArticleSections (a Draft lépés kimenete)
              - article: KBArticle (végső cikk)
              - change_summary, key_steps, audience: az Extract lépésből
                (a metric számára hasznos lehet)
        """
        # 1. Kinyerés: mi történt, lépések, célközönség
        extracted = self.extract(story_text=story_text)

        # 2. Piszkozat: részek szerkesztése a célközönségnek
        drafted = self.draft(
            change_summary=extracted.change_summary,
            key_steps=extracted.key_steps,
            audience=extracted.audience,
        )

        # 3. Formázás: HTML törzs
        formatted = self.format(
            title=drafted.title,
            problem=drafted.problem,
            solution_steps=drafted.solution_steps,
            summary=drafted.summary,
        )

        # Típusos köztes és végső objektumok (schemas.py)
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
            # az Extract lépés kimenetei is elérhetők (a metric számára)
            change_summary=extracted.change_summary,
            key_steps=extracted.key_steps,
            audience=extracted.audience,
        )
