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
    GenerateKbFromTemplate,
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
        self.analyze_changes = dspy.ChainOfThought(AnalyzeChanges)
        self.extract = dspy.ChainOfThought(ExtractChange)
        self.draft = dspy.ChainOfThought(DraftSections)
        self.format = dspy.Predict(FormatKB)
        # Új prediktor: HTML sablon egy-az-egyben történő kitöltése
        self.generate_from_template = dspy.Predict(GenerateKbFromTemplate)

    def forward(
        self,
        story_text: str,
        *,
        update_set_payloads: str = "",
        template_context: str = "",
        category: str = "General",
        knowledge_base_id: str = "",
    ) -> dspy.Prediction:
        """Lefuttatja a pipeline-t.

        Args:
            story_text: a teljes Story szöveg (assemble_story_text kimenete).
            update_set_payloads: a módosítások nyers XML payloadjai (ha vannak).
            template_context: a csapat specifikus KB sablon (Few-Shot példa).
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

        # 0. AnalyzeChanges lépés: Ha vannak módosítások (raw payloadok),
        # a GLM kinyeri belőlük a scripteket/JSDoc-okat. Mivel a GLM-5.2-nek
        # hatalmas (1M token) kontextusablaka van, a 15.000 karakteres korlátot
        # nem kell szigorúan vennünk, de meghagyjuk optimalizálás céljából.
        if update_set_payloads:
            # Ha nagyon nagy a payload, csak az első 50.000 karaktert adjuk át
            # hogy ne terheljük túl a kontextust feleslegesen.
            payload_snippet = update_set_payloads[:50000]
            if len(update_set_payloads) > 50000:
                payload_snippet += "\n... (payload csonkítva 50.000 karakternél)"
                
            analysis = self.analyze_changes(
                update_set_xml=payload_snippet,
                query="Extract all technical details: JSDoc comments, descriptions, function names, and Flow steps.",
            )
            full_context += "\n\n## Update Set Technical Summary (via LLM)\n"
            full_context += analysis.technical_summary

        # 1. Kinyerés: mi történt, lépések, célközönség
        extracted = self.extract(story_text=full_context)

        # 2. Ha van HTML sablon, használd az egy-az-egyben kitöltő Signature-t
        if template_context:
            # A sablon-alapú generálás sokkal rugalmasabb: bármennyi szekciót képes
            # kezelni, mert közvetlenül a HTML struktúrát tölti ki.
            story_context_for_template = (
                f"Change Summary: {extracted.change_summary}\n\n"
                f"Key Steps: {', '.join(extracted.key_steps)}\n\n"
                f"Full Story Context: {full_context}"
            )
            template_result = self.generate_from_template(
                story_context=story_context_for_template,
                html_template=template_context,
            )
            final_html = template_result.html
            # Cím kinyerése az extract lépésből (vagy az első <h1> a HTML-ből)
            final_title = extracted.change_summary.split('.')[0][:120] or "KB Article"
            
            article = KBArticle(
                title=final_title,
                html=final_html,
                category=category,
                knowledge_base_id=knowledge_base_id,
            )
            
            return dspy.Prediction(
                sections=ArticleSections(
                    title=final_title,
                    problem="(Generated from template)",
                    solution_steps=["See generated HTML"],
                    summary=extracted.change_summary,
                    audience=extracted.audience,
                ),
                article=article,
                change_summary=extracted.change_summary,
                key_steps=extracted.key_steps,
                audience=extracted.audience,
            )

        # 2b. Ha NINCS sablon: a hagyományos 3-lépéses pipeline
        drafted = self.draft(
            change_summary=extracted.change_summary,
            key_steps=extracted.key_steps,
            audience=extracted.audience,
            template_context=template_context,
        )

        # 3. Formázás: HTML törzs
        formatted = self.format(
            title=drafted.title,
            problem=drafted.problem,
            solution_steps=drafted.solution_steps,
            summary=drafted.summary,
            template_context=template_context,
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
