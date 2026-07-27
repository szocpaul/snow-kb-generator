"""test_signatures.py — the DSPy Signature tests of signatures.py.

The covered areas:
  - All three Signatures load (they exist as classes, have a docstring)
  - The direction of the Input/Output fields is correct (input_fields / output_fields)
  - The field types are consistent with the models of schemas.py
  - list[str] types correctly annotated (Pydantic integration)
  - Predict / ChainOfThought predictors can be constructed on them
  - The field names match the Pydantic models of schemas.py (passability)
"""

from __future__ import annotations

import typing

import dspy
import pytest

from snow_kb.signatures import DraftSections, ExtractChange, FormatKB
from snow_kb.schemas import ArticleSections, KBArticle, StoryData


# ---------------------------------------------------------------------------
# Helper: extracting the field directions (DSPy 3.2 — the attribute, dict format)
# ---------------------------------------------------------------------------

def _inputs(sig) -> list[str]:
    obj = sig.input_fields
    return list(obj.keys()) if isinstance(obj, dict) else list(obj().keys())


def _outputs(sig) -> list[str]:
    obj = sig.output_fields
    return list(obj.keys()) if isinstance(obj, dict) else list(obj().keys())


# ---------------------------------------------------------------------------
# Structure: existence, docstring, fields
# ---------------------------------------------------------------------------

class TestSignatureStructure:
    """The Signatures classes load and have an instruction."""

    @pytest.mark.parametrize("sig", [ExtractChange, DraftSections, FormatKB])
    def test_is_dspy_signature(self, sig):
        assert issubclass(sig, dspy.Signature)

    @pytest.mark.parametrize("sig", [ExtractChange, DraftSections, FormatKB])
    def test_has_docstring(self, sig):
        """The instruction comes from the docstring — it must not be empty."""
        assert sig.__doc__ is not None
        assert len(sig.__doc__.strip()) > 20

    @pytest.mark.parametrize("sig,expected_inputs,expected_outputs", [
        (ExtractChange, ["story_text"], ["change_summary", "key_steps", "audience"]),
        (DraftSections, ["change_summary", "key_steps", "audience", "template_context"],
                         ["title", "problem", "solution_steps", "summary"]),
        (FormatKB, ["title", "problem", "solution_steps", "summary", "template_context"], ["html"]),
    ])
    def test_field_directions(self, sig, expected_inputs, expected_outputs):
        assert _inputs(sig) == expected_inputs
        assert _outputs(sig) == expected_outputs


# ---------------------------------------------------------------------------
# The consistency of the types
# ---------------------------------------------------------------------------

class TestFieldTypes:
    """The field types are correct (str, list[str])."""

    def _field_type(self, sig, name):
        return sig.model_fields[name].annotation

    def test_extract_change_types(self):
        assert self._field_type(ExtractChange, "story_text") is str
        assert self._field_type(ExtractChange, "change_summary") is str
        assert self._field_type(ExtractChange, "key_steps") == list[str]
        # The Literal type: the parser enforces the valid values (DSPy best practice)
        from typing import Literal
        assert self._field_type(ExtractChange, "audience") == Literal["helpdesk", "end-user", "developer"]

    def test_draft_sections_types(self):
        assert self._field_type(DraftSections, "key_steps") == list[str]
        assert self._field_type(DraftSections, "solution_steps") == list[str]
        assert self._field_type(DraftSections, "title") is str

    def test_format_kb_types(self):
        assert self._field_type(FormatKB, "solution_steps") == list[str]
        assert self._field_type(FormatKB, "html") is str


# ---------------------------------------------------------------------------
# The constructability of the predictors
# ---------------------------------------------------------------------------

class TestPredictorConstruction:
    """The Signatures can be used with Predict / ChainOfThought predictors."""

    @pytest.mark.parametrize("sig", [ExtractChange, DraftSections, FormatKB])
    def test_predict_constructible(self, sig):
        p = dspy.Predict(sig)
        assert isinstance(p, dspy.Predict)

    @pytest.mark.parametrize("sig", [ExtractChange, DraftSections])
    def test_chainofthought_constructible(self, sig):
        """ExtractChange and DraftSections require reasoning."""
        p = dspy.ChainOfThought(sig)
        assert isinstance(p, dspy.ChainOfThought)

    def test_format_kb_is_predict_not_cot(self):
        """FormatKB transformation — Predict, not ChainOfThought (by design)."""
        p = dspy.Predict(FormatKB)
        assert isinstance(p, dspy.Predict)


# ---------------------------------------------------------------------------
# The field name consistency with the schemas.py models
# ---------------------------------------------------------------------------

class TestSchemaConsistency:
    """The Signature field names match the Pydantic fields of schemas.py,
    so that the program.forward() can pass the data in a typed way.
    """

    def test_extract_outputs_match_storydata_context(self):
        """The outputs of ExtractChange go into DraftSections as input."""
        extract_outs = set(_outputs(ExtractChange))
        draft_ins = set(_inputs(DraftSections))
        assert extract_outs.issubset(draft_ins), (
            "The outputs of ExtractChange are not a subset of the inputs of DraftSections."
        )

    def test_draft_outputs_match_format_inputs(self):
        """The outputs of DraftSections go into FormatKB as input."""
        draft_outs = set(_outputs(DraftSections))
        format_ins = set(_inputs(FormatKB))
        assert draft_outs.issubset(format_ins), (
            "The outputs of DraftSections are not a subset of the inputs of FormatKB."
        )

    def test_draft_outputs_subset_of_article_sections(self):
        """The outputs of DraftSections are a subset of the ArticleSections fields.

        The `audience` is not a DraftSections output (it is an ExtractChange input
        receives it), but the program.forward() forwards it into ArticleSections.
        Therefore the subset check is the right one: every DraftSections output
        must also exist in ArticleSections.
        """
        draft_outs = set(_outputs(DraftSections))
        article_fields = set(ArticleSections.model_fields.keys())
        assert draft_outs.issubset(article_fields), (
            f"Some of the outputs of DraftSections ({draft_outs}) do not appear "
            f"among the fields of ArticleSections ({article_fields})."
        )

    def test_audience_flows_from_extract_to_article(self):
        """The audience is both an output of ExtractChange and a field of ArticleSections —
        the program.forward() passes between the two steps.
        """
        assert "audience" in _outputs(ExtractChange)
        assert "audience" in ArticleSections.model_fields

    def test_format_outputs_match_kb_article_subset(self):
        """The output of FormatKB (html) matches the KBArticle.html field."""
        format_outs = set(_outputs(FormatKB))
        assert "html" in format_outs
        assert "html" in KBArticle.model_fields

    def test_story_text_is_single_input(self):
        """ExtractChange expects a single story_text input —
        not separate fields. This is the program.forward() contract.
        assert _inputs(ExtractChange) == ["story_text"]

"""
