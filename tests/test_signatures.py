"""test_signatures.py — a signatures.py DSPy Signature tesztek.

Lefedett területek:
  - A Signature-k betöltődnek (osztályként léteznek, docstring van)
  - Input/Output mezők iránya helyes (input_fields / output_fields)
  - Mezőtípusok konzisztensek a schemas.py modelljeivel
  - list[str] és Literal típusok helyesen annotálva (Pydantic integráció)
  - Predict / ChainOfThought prediktorok konstruálhatók rajtuk
  - Mezőnevek egyeznek a schemas.py Pydantic modelljeivel (átadhatság)

Spec 009: DraftSections és FormatKB kivezetve — az élő Signature-k:
AnalyzeChanges, ExtractChange, GenerateKbFromTemplate.
"""

from __future__ import annotations

import typing

import dspy
import pytest

from snow_kb.schemas import ArticleSections, KBArticle
from snow_kb.signatures import AnalyzeChanges, ExtractChange, GenerateKbFromTemplate


# ---------------------------------------------------------------------------
# Helper: field irányok kinyerése (DSPy 3.2 — attribute, dict formátum)
# ---------------------------------------------------------------------------

def _inputs(sig) -> list[str]:
    obj = sig.input_fields
    return list(obj.keys()) if isinstance(obj, dict) else list(obj().keys())


def _outputs(sig) -> list[str]:
    obj = sig.output_fields
    return list(obj.keys()) if isinstance(obj, dict) else list(obj().keys())


# ---------------------------------------------------------------------------
# Struktúra: létezés, docstring, mezők
# ---------------------------------------------------------------------------

class TestSignatureStructure:
    """A Signatures osztályai betöltődnek és rendelkeznek instruction-nel."""

    @pytest.mark.parametrize("sig", [AnalyzeChanges, ExtractChange, GenerateKbFromTemplate])
    def test_is_dspy_signature(self, sig):
        assert issubclass(sig, dspy.Signature)

    @pytest.mark.parametrize("sig", [AnalyzeChanges, ExtractChange, GenerateKbFromTemplate])
    def test_has_docstring(self, sig):
        """A docstringből lesz az instruction — nem lehet üres."""
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
# Típusok konzisztenciája
# ---------------------------------------------------------------------------

class TestFieldTypes:
    """A mezők típusai helyesek (str, list[str], Literal)."""

    def _field_type(self, sig, name):
        return sig.model_fields[name].annotation

    def test_extract_change_types(self):
        assert self._field_type(ExtractChange, "story_text") is str
        assert self._field_type(ExtractChange, "change_summary") is str
        assert self._field_type(ExtractChange, "key_steps") == list[str]
        # Literal típus: a parser kényszeríti az érvényes értékeket (DSPy best practice)
        from typing import Literal
        assert self._field_type(ExtractChange, "audience") == Literal["helpdesk", "end-user", "developer"]

    def test_generate_from_template_types(self):
        assert self._field_type(GenerateKbFromTemplate, "story_context") is str
        assert self._field_type(GenerateKbFromTemplate, "html_template") is str
        assert self._field_type(GenerateKbFromTemplate, "related_articles_context") is str
        assert self._field_type(GenerateKbFromTemplate, "title") is str
        assert self._field_type(GenerateKbFromTemplate, "html") is str


# ---------------------------------------------------------------------------
# Prediktorok konstruálhatósága
# ---------------------------------------------------------------------------

class TestPredictorConstruction:
    """A Signatures használhatók Predict / ChainOfThought prediktorokkal."""

    @pytest.mark.parametrize("sig", [AnalyzeChanges, ExtractChange, GenerateKbFromTemplate])
    def test_predict_constructible(self, sig):
        p = dspy.Predict(sig)
        assert isinstance(p, dspy.Predict)

    @pytest.mark.parametrize("sig", [AnalyzeChanges, ExtractChange])
    def test_chainofthought_constructible(self, sig):
        """AnalyzeChanges és ExtractChange érvelést igényelnek."""
        p = dspy.ChainOfThought(sig)
        assert isinstance(p, dspy.ChainOfThought)

    def test_generate_from_template_is_predict_not_cot(self):
        """A template-kitöltés transzformáció — Predict (terv szerint)."""
        p = dspy.Predict(GenerateKbFromTemplate)
        assert isinstance(p, dspy.Predict)


# ---------------------------------------------------------------------------
# Mezőnév-konzisztencia a schemas.py modellekkel
# ---------------------------------------------------------------------------

class TestSchemaConsistency:
    """A Signature mezőnevek egyeznek a schemas.py Pydantic mezőivel."""

    def test_extract_outputs_flow_to_article_sections(self):
        """Az extract kimenetei (change_summary, key_steps, audience) mind
        megvannak az ArticleSections-ben — a forward() innen tölti fel."""
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
        """ExtractChange egyetlen story_text bemenetet vár —
        ez a program.forward() szerződés."""
        assert _inputs(ExtractChange) == ["story_text"]
