"""test_program.py — the tests of the program.py StoryToKBArticle(dspy.Module).

The covered areas:
  - The program can be constructed without an LM call (dry-run / smoke test)
  - a dspy.Module subclass
  - Three named predictors (GEPA targeting)
  - Predictor types: extract/draft = ChainOfThought, format = Predict
  - The Signatures are wired up correctly
  - forward() contract: story_text input, Prediction output

We do not test the LM calls here (that is the job of the integration/eval tests).
We use the DSPy_dummy LM to test forward().
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import dspy
import pytest

from snow_kb.program import StoryToKBArticle
from snow_kb.schemas import ArticleSections, KBArticle
from snow_kb.signatures import DraftSections, ExtractChange, FormatKB


# ---------------------------------------------------------------------------
# The smoke tests (without an LM)
# ---------------------------------------------------------------------------

class TestProgramConstruction:
    """The program can be constructed, the type is correct, the predictors are attached."""

    def test_is_dspy_module(self):
        program = StoryToKBArticle()
        assert isinstance(program, dspy.Module)

    def test_has_four_predictors(self):
        program = StoryToKBArticle()
        # analyze_changes + extract + draft + format
        assert len(program.predictors()) == 4

    def test_predictors_are_named(self):
        """Every predictor got a name — GEPA targets these."""
        program = StoryToKBArticle()
        names = [name for name, _ in program.named_predictors()]
        # Due to the internal structure of ChainOfThought the name will be 'extract.predict',
        # de tartalmazza az eredeti nevet.
        assert any("extract" in n for n in names)
        assert any("draft" in n for n in names)
        assert any("format" in n for n in names)

    def test_predictor_types(self):
        """extract and draft ChainOfThought, format Predict."""
        program = StoryToKBArticle()
        # predictors() also returns the internal predictors
        predictor_map = dict(program.named_predictors())

        # We find the types by name
        types_by_name = {}
        for name, pred in program.named_predictors():
            types_by_name[name] = type(pred).__name__

        # At least one Predict coming from a ChainOfThought and one plain Predict
        # (ChainOfThought internally contains a Predict)
        assert len(types_by_name) == 4

    def test_signatures_attached(self):
        """The predictors use the correct Signatures.

        ChainOfThought internally converts the Signature to a StringSignature
        (the name is lost, but the fields remain and 'reasoning' is added).
        Therefore we check the field names, not the class name.
        """
        program = StoryToKBArticle()

        # Collecting the fields in the name -> (inputs, outputs) format
        pred_fields = {}
        for name, pred in program.named_predictors():
            sig = pred.signature
            ins = list(sig.input_fields.keys())
            outs = list(sig.output_fields.keys())
            pred_fields[name] = (ins, outs)

        # Extract: story_text -> reasoning + change_summary + key_steps + audience
        extract_key = [k for k in pred_fields if k.startswith("extract")][0]
        ext_ins, ext_outs = pred_fields[extract_key]
        assert "story_text" in ext_ins
        assert "change_summary" in ext_outs
        assert "key_steps" in ext_outs
        assert "audience" in ext_outs
        assert "reasoning" in ext_outs  # ChainOfThought adds it

        # Draft: change_summary/key_steps/audience -> title/problem/solution_steps/summary
        draft_key = [k for k in pred_fields if k.startswith("draft")][0]
        _, draft_outs = pred_fields[draft_key]
        assert "title" in draft_outs
        assert "solution_steps" in draft_outs

        # Format: title/problem/solution_steps/summary -> html
        format_key = [k for k in pred_fields if k.startswith("format")][0]
        _, fmt_outs = pred_fields[format_key]
        assert "html" in fmt_outs
        assert "reasoning" not in fmt_outs  # Predict, nem ChainOfThought


# ---------------------------------------------------------------------------
# forward() tests with a mock LM
# ---------------------------------------------------------------------------

class TestForwardContract:
    """Testing the forward() contract with mocked predictors.

    We do not call a real LM — we mock the return value of the three predictors
    and check that forward() chains correctly and
    gives typed output.
    """

    def _make_program_with_mock_predictors(self):
        """Creates a program in which the three predictors are mocked."""
        program = StoryToKBArticle()

        # Mock ExtractChange output
        extract_mock = MagicMock(return_value=dspy.Prediction(
            change_summary="Token TTL bumped from 1800s to 3600s.",
            key_steps=["Patch auth middleware.", "Restart worker pool."],
            audience="helpdesk",
        ))

        # Mock DraftSections output
        draft_mock = MagicMock(return_value=dspy.Prediction(
            title="Resolving SSO Login Failures After IDP Upgrade",
            problem="Users could not log in due to short token TTL.",
            solution_steps=[
                "Patch the auth middleware to v2.3.",
                "Restart the worker pool.",
            ],
            summary="Fix SSO login by increasing token TTL.",
        ))

        # Mock FormatKB output
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
        """The outputs of Extract are passed as input to Draft."""
        program, mocks = self._make_program_with_mock_predictors()
        extract_mock, draft_mock, _ = mocks
        program("story text here")

        draft_mock.assert_called_once()
        call_kwargs = draft_mock.call_args.kwargs
        assert call_kwargs["change_summary"] == "Token TTL bumped from 1800s to 3600s."
        assert call_kwargs["audience"] == "helpdesk"

    def test_forward_passes_draft_outputs_to_format(self):
        """The outputs of Draft are passed as input to Format."""
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
        """The outputs of the Extract are available in the Prediction (for the metric)."""
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
