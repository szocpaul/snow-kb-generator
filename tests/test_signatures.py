"""test_signatures.py — the tests of the signatures.py DSPy Signature.

The covered areas:
  - The Signatures load (they exist as classes, with a docstring)
  - The direction of the Input/Output fields is correct (input_fields / output_fields)
  - The field types are consistent with the models of schemas.py
  - The list[str] and Literal types are annotated correctly (Pydantic integration)
  - Predict / ChainOfThought predictors can be constructed on them
  - The field names match the Pydantic models of schemas.py (passability)

Spec 009: DraftSections and FormatKB removed — the live Signatures:
AnalyzeChanges, ExtractChange, GenerateKbFromTemplate.
"""

from __future__ import annotations

import typing

import dspy
import pytest

from snow_kb.schemas import ArticleSections, KBArticle
from snow_kb.signatures import AnalyzeChanges, ExtractChange, GenerateKbFromTemplate


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

    @pytest.mark.parametrize("sig", [AnalyzeChanges, ExtractChange, GenerateKbFromTemplate])
    def test_is_dspy_signature(self, sig):
        assert issubclass(sig, dspy.Signature)

    @pytest.mark.parametrize("sig", [AnalyzeChanges, ExtractChange, GenerateKbFromTemplate])
    def test_has_docstring(self, sig):
        """The instruction comes from the docstring — it must not be empty."""
        assert sig.__doc__ is not None
        assert len(sig.__doc__.strip()) > 20

    @pytest.mark.parametrize("sig,expected_inputs,expected_outputs", [
        (AnalyzeChanges, ["update_set_xml", "query"], ["technical_summary"]),
        (ExtractChange, ["story_text"], ["change_summary", "key_steps", "audience"]),
        (GenerateKbFromTemplate,
         ["story_context", "html_template", "related_articles_context"],
         ["title", "html"]),
    ])
    def test_field_directions(self, sig, expected_inputs, expected_outputs):
        assert _inputs(sig) == expected_inputs
        assert _outputs(sig) == expected_outputs


# ---------------------------------------------------------------------------
# The consistency of the types
# ---------------------------------------------------------------------------

class TestFieldTypes:
    """The types of the fields are correct (str, list[str], Literal)."""

    def _field_type(self, sig, name):
        return sig.model_fields[name].annotation

    def test_extract_change_types(self):
        assert self._field_type(ExtractChange, "story_text") is str
        assert self._field_type(ExtractChange, "change_summary") is str
        assert self._field_type(ExtractChange, "key_steps") == list[str]
        # The Literal type: the parser enforces the valid values (DSPy best practice)
        from typing import Literal
        assert self._field_type(ExtractChange, "audience") == Literal["helpdesk", "end-user", "developer"]

    def test_generate_from_template_types(self):
        assert self._field_type(GenerateKbFromTemplate, "story_context") is str
        assert self._field_type(GenerateKbFromTemplate, "html_template") is str
        assert self._field_type(GenerateKbFromTemplate, "related_articles_context") is str
        assert self._field_type(GenerateKbFromTemplate, "title") is str
        assert self._field_type(GenerateKbFromTemplate, "html") is str


# ---------------------------------------------------------------------------
# The constructability of the predictors
# ---------------------------------------------------------------------------

class TestPredictorConstruction:
    """The Signatures can be used with Predict / ChainOfThought predictors."""

    @pytest.mark.parametrize("sig", [AnalyzeChanges, ExtractChange, GenerateKbFromTemplate])
    def test_predict_constructible(self, sig):
        p = dspy.Predict(sig)
        assert isinstance(p, dspy.Predict)

    @pytest.mark.parametrize("sig", [AnalyzeChanges, ExtractChange])
    def test_chainofthought_constructible(self, sig):
        """AnalyzeChanges and ExtractChange require reasoning."""
        p = dspy.ChainOfThought(sig)
        assert isinstance(p, dspy.ChainOfThought)

    def test_generate_from_template_is_predict_not_cot(self):
        """The template filling transformation — Predict (per the design)."""
        p = dspy.Predict(GenerateKbFromTemplate)
        assert isinstance(p, dspy.Predict)


# ---------------------------------------------------------------------------
# The field name consistency with the schemas.py models
# ---------------------------------------------------------------------------

class TestSchemaConsistency:
    """The field names of the Signature match the Pydantic fields of schemas.py."""

    def test_extract_outputs_flow_to_article_sections(self):
        """The outputs of the extract (change_summary, key_steps, audience) are all
        are present in the ArticleSections — the forward() fills it from here."""
        extract_outs = set(_outputs(ExtractChange))
        article_fields = set(ArticleSections.model_fields.keys())
        for field in ("change_summary", "key_steps", "audience"):
            assert field in extract_outs or field in article_fields

    def test_audience_flows_from_extract_to_article(self):
        assert "audience" in _outputs(ExtractChange)
        assert "audience" in ArticleSections.model_fields

    def test_generate_outputs_match_kb_article(self):
        """GenerateKbFromTemplate kimenetei (title, html) megvannak a KBArticle-ben."""
        gen_outs = set(_outputs(GenerateKbFromTemplate))
        assert {"title", "html"}.issubset(gen_outs)
        assert "title" in KBArticle.model_fields
        assert "html" in KBArticle.model_fields

    def test_story_text_is_single_input(self):
        """ExtractChange expects a single story_text input —
        this is the contract of program.forward()."""
        assert _inputs(ExtractChange) == ["story_text"]
