"""test_program.py — a program.py StoryToKBArticle(dspy.Module) tesztek.

Lefedett területek:
  - A program konstruálható LM hívás nélkül (dry-run / smoke test)
  - dspy.Module alosztály
  - Három névvel ellátott prediktor (GEPA célzás): analyze_changes, extract,
    generate_from_template (spec 009: a legacy draft/format ág kivezetve)
  - A Signature-k helyesen vannak rákötve
  - forward() szerződése: story_text + template_context bemenet, Prediction kimenet
  - template_context kötelező (ValueError nélküle)

Az LM hívásokat nem teszteljük itt (az integrációs/eval tesztek feladata).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import dspy
import pytest

from snow_kb.program import StoryToKBArticle
from snow_kb.schemas import ArticleSections, KBArticle


# ---------------------------------------------------------------------------
# Smoke tesztek (LM nélkül)
# ---------------------------------------------------------------------------

class TestProgramConstruction:
    """A program konstruálható, helyes típus, prediktorok fel vannak véve."""

    def test_is_dspy_module(self):
        program = StoryToKBArticle()
        assert isinstance(program, dspy.Module)

    def test_has_three_predictors(self):
        """Spec 009: analyze_changes + extract + generate_from_template."""
        program = StoryToKBArticle()
        assert len(program.predictors()) == 3

    def test_predictors_are_named(self):
        """Minden prediktor kapott nevet — a GEPA ezeket célozza."""
        program = StoryToKBArticle()
        names = [name for name, _ in program.named_predictors()]
        assert any("extract" in n for n in names)
        assert any("analyze_changes" in n for n in names)
        assert any("generate_from_template" in n for n in names)

    def test_predictor_types(self):
        """extract/analyze_changes ChainOfThought, generate_from_template Predict."""
        program = StoryToKBArticle()
        types_by_name = {}
        for name, pred in program.named_predictors():
            types_by_name[name] = type(pred).__name__
        assert len(types_by_name) == 3

    def test_signatures_attached(self):
        """A prediktorok a megfelelő Signature-mezőket használják.

        A ChainOfThought belsőleg 'reasoning' mezőt ad hozzá.
        """
        program = StoryToKBArticle()

        pred_fields = {}
        for name, pred in program.named_predictors():
            sig = pred.signature
            pred_fields[name] = (list(sig.input_fields.keys()), list(sig.output_fields.keys()))

        # Extract: story_text -> reasoning + change_summary + key_steps + audience
        extract_key = [k for k in pred_fields if k.startswith("extract")][0]
        ext_ins, ext_outs = pred_fields[extract_key]
        assert "story_text" in ext_ins
        assert "change_summary" in ext_outs
        assert "key_steps" in ext_outs
        assert "audience" in ext_outs
        assert "reasoning" in ext_outs  # ChainOfThought hozzáadja

        # GenerateKbFromTemplate: story_context/html_template/related_articles_context -> title + html
        gen_key = [k for k in pred_fields if k.startswith("generate_from_template")][0]
        gen_ins, gen_outs = pred_fields[gen_key]
        assert "story_context" in gen_ins
        assert "html_template" in gen_ins
        assert "related_articles_context" in gen_ins
        assert "title" in gen_outs
        assert "html" in gen_outs
        assert "reasoning" not in gen_outs  # Predict, nem ChainOfThought


# ---------------------------------------------------------------------------
# forward() tesztek mock prediktorokkal
# ---------------------------------------------------------------------------

TEMPLATE = "<h2>Overview / Summary</h2><h3>Content</h3><ul><li>x</li></ul>"


class TestForwardContract:
    """A forward() szerződésének tesztelése mockolt prediktorokkal."""

    def _make_program_with_mock_predictors(self):
        """Létrehoz egy programot, amiben a prediktorok mockolt."""
        program = StoryToKBArticle()

        extract_mock = MagicMock(return_value=dspy.Prediction(
            change_summary="Token TTL bumped from 1800s to 3600s.",
            key_steps=["Patch auth middleware.", "Restart worker pool."],
            audience="helpdesk",
        ))

        template_mock = MagicMock(return_value=dspy.Prediction(
            title="Resolving SSO Login Failures After IDP Upgrade",
            html="<h2>Overview / Summary</h2><p>Fix SSO by increasing token TTL.</p>",
        ))

        program.extract = extract_mock
        program.generate_from_template = template_mock

        return program, (extract_mock, template_mock)

    def test_forward_returns_prediction(self):
        program, _ = self._make_program_with_mock_predictors()
        result = program("Story: fix login bug", template_context=TEMPLATE)
        assert isinstance(result, dspy.Prediction)

    def test_forward_returns_article(self):
        program, _ = self._make_program_with_mock_predictors()
        result = program("Story: fix login bug", template_context=TEMPLATE)
        assert isinstance(result.article, KBArticle)
        assert "Resolving SSO" in result.article.title
        assert "<h2>" in result.article.html

    def test_forward_title_fallback_when_empty(self):
        """Ha a modell üres címet ad, az extract change_summary-je a fallback."""
        program, (_, template_mock) = self._make_program_with_mock_predictors()
        template_mock.return_value = dspy.Prediction(
            title="",
            html="<h2>Overview</h2><p>x</p>",
        )
        result = program("story", template_context=TEMPLATE)
        assert result.article.title.startswith("Token TTL bumped")

    def test_forward_returns_sections(self):
        program, _ = self._make_program_with_mock_predictors()
        result = program("Story: fix login bug", template_context=TEMPLATE)
        assert isinstance(result.sections, ArticleSections)
        assert result.sections.audience == "helpdesk"
        assert len(result.sections.solution_steps) == 2

    def test_forward_requires_template_context(self):
        """Spec 009: template_context nélkül ValueError."""
        program, _ = self._make_program_with_mock_predictors()
        with pytest.raises(ValueError, match="template_context kötelező"):
            program("story text")

    def test_forward_passes_context_to_template_predictor(self):
        """A generate_from_template a story contextet, sablont és related contextet kapja."""
        program, (_, template_mock) = self._make_program_with_mock_predictors()
        program("story text here", template_context=TEMPLATE, related_articles_context="KB7654321 | Real article")

        template_mock.assert_called_once()
        call_kwargs = template_mock.call_args.kwargs
        assert "Token TTL bumped" in call_kwargs["story_context"]
        assert "helpdesk" in call_kwargs["story_context"]  # audience stílusként
        assert call_kwargs["html_template"] == TEMPLATE
        assert call_kwargs["related_articles_context"] == "KB7654321 | Real article"

    def test_forward_category_defaults_to_general(self):
        program, _ = self._make_program_with_mock_predictors()
        result = program("story text", template_context=TEMPLATE)
        assert result.article.category == "General"
        assert result.article.knowledge_base_id == ""

    def test_forward_accepts_category_and_kb_id(self):
        program, _ = self._make_program_with_mock_predictors()
        result = program(
            "story text",
            template_context=TEMPLATE,
            category="Self-Service",
            knowledge_base_id="kb123",
        )
        assert result.article.category == "Self-Service"
        assert result.article.knowledge_base_id == "kb123"

    def test_forward_exposes_extract_outputs(self):
        """Az Extract kimenetei elérhetők a Prediction-ben (a metric számára)."""
        program, _ = self._make_program_with_mock_predictors()
        result = program("story text", template_context=TEMPLATE)
        assert result.change_summary == "Token TTL bumped from 1800s to 3600s."
        assert result.audience == "helpdesk"
        assert len(result.key_steps) == 2

    def test_extract_called_with_story_text(self):
        """Az Extract a story_text bemenetet kapja."""
        program, (extract_mock, _) = self._make_program_with_mock_predictors()
        program("my story text", template_context=TEMPLATE)
        extract_mock.assert_called_once_with(story_text="my story text")
