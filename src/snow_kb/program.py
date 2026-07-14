"""program.py — StoryToKBArticle(dspy.Module), a pipeline magja.

A DSPy Signature-ket egyetlen összetett Module-láncba fűzi. Ez a "program",
amit baseline-olunk és GEPA-val optimalizálunk.

Lépések:
  0. AnalyzeChanges (RLM) — Ha nagy az Update Set, rekurzívan elemzi (opcionális)
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
from snow_kb.signatures import (
    AnalyzeChanges,
    DraftSections,
    ExtractChange,
    FormatKB,
)

# Karakterkorlát: ha az Update Set payloadjai együtt meghaladják ezt az értéket,
# bekapcsol az RLM (Recursive Language Model) lépés, amely rekurzívan feldolgozza
# a nagy adatot. Alatta a sima LLM bírja a kontextust.
RLM_THRESHOLD_CHARS = 15000


class StoryToKBArticle(dspy.Module):
    """DSPy program, ami egy ServiceNow Story szövegből KB cikket generál.

    A kategória (category) és a knowledge_base_id a programon kívülről jön
    (a pipeline.py-ból, ami a config-ból olvassa). A forward() ezeket
    opcionálisan elfogadja, hogy a végső KBArticle teljes legyen.
    """

    def __init__(self) -> None:
        super().__init__()
        # Névvel ellátott prediktorok — a GEPA ezeket célozza.
        # Az RLM lépés (dspy.RLM) csak akkor inicializálódik és fut, ha szükséges.
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
            story_text: a teljes Story szöveg (assemble_story_text kimenete).
            update_set_payloads: a módosítások nyers XML payloadjai (ha vannak).
            category: KB kategória (config-ból, alapból "General").
            knowledge_base_id: cél KB sys_id (config-ból).

        Returns:
            dspy.Prediction a következő mezőkkel:
              - sections: ArticleSections (a Draft lépés kimenete)
              - article: KBArticle (végső cikk)
              - change_summary, key_steps, audience: az Extract lépésből
                (a metric számára hasznos lehet)
        """
        full_context = story_text

        # 0. RLM lépés: Csak akkor fut, ha a nyers payloadok nagyok (> 15.000 karakter)
        if update_set_payloads and len(update_set_payloads) > RLM_THRESHOLD_CHARS:
            rlm_result = self.analyze_changes(
                context=update_set_payloads,
                query="Extract all technical details: JSDoc comments, descriptions, function names, and Flow steps.",
            )
            full_context += "\n\n## Update Set Technical Summary (via RLM)\n"
            full_context += rlm_result.technical_summary
        elif update_set_payloads:
            # Kicsi a payload, elfér a kontextusban, nem kell RLM
            full_context += "\n\n## Update Set Raw Modifications\n"
            full_context += update_set_payloads

        # 1. Kinyerés: mi történt, lépések, célközönség
        extracted = self.extract(story_text=full_context)

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
