"""test_program.py — a program.py StoryToKBArticle(dspy.Module) tesztek.

Le fedett területek:
  - A program konstruálható LM hívás nélkül (dry-run / smoke test)
  - dspy.Module alosztály
  - Három névvel ellátott prediktor (GEPA célzás)
  - Prediktor típusok: extract/draft = ChainOfThought, format = Predict
  - A Signature-k helyesen vannak rákötve
  - forward() szerződése: story_text bemenet, Prediction kimenet

Az LM hívásokat nem teszteljük itt (az integrációs/eval tesztek feladata).
A forward() teszteléséhez a DSPy_dummy LM-et használjuk.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import dspy
import pytest

from snow_kb.program import StoryToKBArticle
from snow_kb.schemas import ArticleSections, KBArticle
from snow_kb.signatures import DraftSections, ExtractChange, FormatKB


# ---------------------------------------------------------------------------
# Smoke tesztek (LM nélkül)
# ---------------------------------------------------------------------------

class TestProgramConstruction:
    """A program konstruálható, helyes típus, prediktorok fel vannak véve."""

    def test_is_dspy_module(self):
        program = StoryToKBArticle()
        assert isinstance(program, dspy.Module)

    def test_has_three_predictors(self):
        program = StoryToKBArticle()
        assert len(program.predictors()) == 3

    def test_predictors_are_named(self):
        """Minden prediktor kapott nevet — a GEPA ezeket célozza."""
        program = StoryToKBArticle()
        names = [name for name, _ in program.named_predictors()]
        # ChainOfThought belső szerkezete miatt a név 'extract.predict' lesz,
        # de tartalmazza az eredeti nevet.
        assert any("extract" in n for n in names)
        assert any("draft" in n for n in names)
        assert any("format" in n for n in names)

    def test_predictor_types(self):
        """extract és draft ChainOfThought, format Predict."""
        program = StoryToKBArticle()
        # A predictors() visszaadja a belső prediktorokat is
        predictor_map = dict(program.named_predictors())

        # Megkeressük a típusokat név alapján
        types_by_name = {}
        for name, pred in program.named_predictors():
            types_by_name[name] = type(pred).__name__

        # Legalább egy ChainOfThought-ból jövő Predict és egy sima Predict
        # (ChainOfThought belsőleg Predict-et tartalmaz)
        assert len(types_by_name) == 3

    def test_signatures_attached(self):
        """A prediktorok a megfelelő Signature-kat használják.

        A ChainOfThought a Signature-t belsőleg StringSignature-re fordítja
        (a név elveszik, de a mezők megmaradnak, és hozzáadódik 'reasoning').
        Ezért a mezőneveket ellenőrizzük, nem az osztálynevet.
        """
        program = StoryToKBArticle()

        # Mezők gyűjtése név -> (inputs, outputs) formátumban
        pred_fields = {}
        for name, pred in program.named_predictors():
            sig = pred.signature
            ins = list(sig.input_fields.keys())
            outs = list(sig.output_fields.keys())
            pred_fields[name] = (ins, outs)

        # Extract: story_text -> reasoning + change_summary + key_steps + audience
        extract_key = [k for k in pred_fields if "extract" in k][0]
        ext_ins, ext_outs = pred_fields[extract_key]
        assert "story_text" in ext_ins
        assert "change_summary" in ext_outs
        assert "key_steps" in ext_outs
        assert "audience" in ext_outs
        assert "reasoning" in ext_outs  # ChainOfThought hozzáadja

        # Draft: change_summary/key_steps/audience -> title/problem/solution_steps/summary
        draft_key = [k for k in pred_fields if "draft" in k][0]
        _, draft_outs = pred_fields[draft_key]
        assert "title" in draft_outs
        assert "solution_steps" in draft_outs

        # Format: title/problem/solution_steps/summary -> html
        format_key = [k for k in pred_fields if "format" in k][0]
        _, fmt_outs = pred_fields[format_key]
        assert "html" in fmt_outs
        assert "reasoning" not in fmt_outs  # Predict, nem ChainOfThought


# ---------------------------------------------------------------------------
# forward() tesztek mock LM-mel
# ---------------------------------------------------------------------------

class TestForwardContract:
    """A forward() szerződésének tesztelése mockolt prediktorokkal.

    Nem hívunk valódi LM-et — a három prediktor visszatérési értékét
    mockoljuk, és ellenőrizzük, hogy a forward() helyesen láncolja és
    típusos kimenetet ad.
    """

    def _make_program_with_mock_predictors(self):
        """Létrehoz egy programot, amiben a három prediktor mockolt."""
        program = StoryToKBArticle()

        # Mock ExtractChange kimenet
        extract_mock = MagicMock(return_value=dspy.Prediction(
            change_summary="Token TTL bumped from 1800s to 3600s.",
            key_steps=["Patch auth middleware.", "Restart worker pool."],
            audience="helpdesk",
        ))

        # Mock DraftSections kimenet
        draft_mock = MagicMock(return_value=dspy.Prediction(
            title="Resolving SSO Login Failures After IDP Upgrade",
            problem="Users could not log in due to short token TTL.",
            solution_steps=[
                "Patch the auth middleware to v2.3.",
                "Restart the worker pool.",
            ],
            summary="Fix SSO login by increasing token TTL.",
        ))

        # Mock FormatKB kimenet
        format_mock = MagicMock(return_value=dspy.Prediction(
            html="<h2>Solution</h2><ol><li>Patch middleware.</li></ol>",
        ))

        program.extract = extract_mock
        program.draft = draft_mock
        program.format = format_mock

        return program, (extract_mock, draft_mock, format_mock)

    def test_forward_returns_prediction(self):
        program, _ = self._make_program_with_mock_predictors()
        result = program("Story: fix login bug")
        assert isinstance(result, dspy.Prediction)

    def test_forward_returns_article(self):
        program, _ = self._make_program_with_mock_predictors()
        result = program("Story: fix login bug")
        assert isinstance(result.article, KBArticle)
        assert "Resolving SSO" in result.article.title
        assert "<ol>" in result.article.html

    def test_forward_returns_sections(self):
        program, _ = self._make_program_with_mock_predictors()
        result = program("Story: fix login bug")
        assert isinstance(result.sections, ArticleSections)
        assert result.sections.audience == "helpdesk"
        assert len(result.sections.solution_steps) == 2

    def test_forward_passes_extract_outputs_to_draft(self):
        """Az Extract kimenetei bemenetként adják át a Draft-nak."""
        program, mocks = self._make_program_with_mock_predictors()
        extract_mock, draft_mock, _ = mocks
        program("story text here")

        draft_mock.assert_called_once()
        call_kwargs = draft_mock.call_args.kwargs
        assert call_kwargs["change_summary"] == "Token TTL bumped from 1800s to 3600s."
        assert call_kwargs["audience"] == "helpdesk"

    def test_forward_passes_draft_outputs_to_format(self):
        """A Draft kimenetei bemenetként adják át a Format-nak."""
        program, mocks = self._make_program_with_mock_predictors()
        _, _, format_mock = mocks
        program("story text here")

        format_mock.assert_called_once()
        call_kwargs = format_mock.call_args.kwargs
        assert "Resolving SSO" in call_kwargs["title"]
        assert len(call_kwargs["solution_steps"]) == 2

    def test_forward_category_defaults_to_general(self):
        program, _ = self._make_program_with_mock_predictors()
        result = program("story text")
        assert result.article.category == "General"
        assert result.article.knowledge_base_id == ""

    def test_forward_accepts_category_and_kb_id(self):
        program, _ = self._make_program_with_mock_predictors()
        result = program(
            "story text",
            category="Self-Service",
            knowledge_base_id="kb123",
        )
        assert result.article.category == "Self-Service"
        assert result.article.knowledge_base_id == "kb123"

    def test_forward_exposes_extract_outputs(self):
        """Az Extract kimenetei elérhetők a Prediction-ben (a metric számára)."""
        program, _ = self._make_program_with_mock_predictors()
        result = program("story text")
        assert result.change_summary == "Token TTL bumped from 1800s to 3600s."
        assert result.audience == "helpdesk"
        assert len(result.key_steps) == 2

    def test_extract_called_with_story_text(self):
        """Az Extract a story_text bemenetet kapja."""
        program, mocks = self._make_program_with_mock_predictors()
        extract_mock, _, _ = mocks
        program("my story text")
        extract_mock.assert_called_once_with(story_text="my story text")
