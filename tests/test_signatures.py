"""test_signatures.py — a signatures.py DSPy Signature tesztek.

Le fedett területek:
  - Mindhárom Signature betöltődik (osztályként létezik, docstring van)
  - Input/Output mezők iránya helyes (input_fields / output_fields)
  - Mezőtípusok konzisztensek a schemas.py modelljeivel
  - list[str] típusok helyesen annotálva (Pydantic integráció)
  - Predict / ChainOfThought prediktorok konstruálhatók rajtuk
  - Mezőnevek egyeznek a schemas.py Pydantic modelljeivel (átadhatság)
"""

from __future__ import annotations

import typing

import dspy
import pytest

from snow_kb.signatures import DraftSections, ExtractChange, FormatKB
from snow_kb.schemas import ArticleSections, KBArticle, StoryData


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

    @pytest.mark.parametrize("sig", [ExtractChange, DraftSections, FormatKB])
    def test_is_dspy_signature(self, sig):
        assert issubclass(sig, dspy.Signature)

    @pytest.mark.parametrize("sig", [ExtractChange, DraftSections, FormatKB])
    def test_has_docstring(self, sig):
        """A docstringből lesz az instruction — nem lehet üres."""
        assert sig.__doc__ is not None
        assert len(sig.__doc__.strip()) > 20

    @pytest.mark.parametrize("sig,expected_inputs,expected_outputs", [
        (ExtractChange, ["story_text"], ["change_summary", "key_steps", "audience"]),
        (DraftSections, ["change_summary", "key_steps", "audience"],
                         ["title", "problem", "solution_steps", "summary"]),
        (FormatKB, ["title", "problem", "solution_steps", "summary"], ["html"]),
    ])
    def test_field_directions(self, sig, expected_inputs, expected_outputs):
        assert _inputs(sig) == expected_inputs
        assert _outputs(sig) == expected_outputs


# ---------------------------------------------------------------------------
# Típusok konzisztenciája
# ---------------------------------------------------------------------------

class TestFieldTypes:
    """A mezők típusai helyesek (str, list[str])."""

    def _field_type(self, sig, name):
        return sig.model_fields[name].annotation

    def test_extract_change_types(self):
        assert self._field_type(ExtractChange, "story_text") is str
        assert self._field_type(ExtractChange, "change_summary") is str
        assert self._field_type(ExtractChange, "key_steps") == list[str]
        assert self._field_type(ExtractChange, "audience") is str

    def test_draft_sections_types(self):
        assert self._field_type(DraftSections, "key_steps") == list[str]
        assert self._field_type(DraftSections, "solution_steps") == list[str]
        assert self._field_type(DraftSections, "title") is str

    def test_format_kb_types(self):
        assert self._field_type(FormatKB, "solution_steps") == list[str]
        assert self._field_type(FormatKB, "html") is str


# ---------------------------------------------------------------------------
# Prediktorok konstruálhatósága
# ---------------------------------------------------------------------------

class TestPredictorConstruction:
    """A Signatures használhatók Predict / ChainOfThought prediktorokkal."""

    @pytest.mark.parametrize("sig", [ExtractChange, DraftSections, FormatKB])
    def test_predict_constructible(self, sig):
        p = dspy.Predict(sig)
        assert isinstance(p, dspy.Predict)

    @pytest.mark.parametrize("sig", [ExtractChange, DraftSections])
    def test_chainofthought_constructible(self, sig):
        """ExtractChange és DraftSections érvelést igényelnek."""
        p = dspy.ChainOfThought(sig)
        assert isinstance(p, dspy.ChainOfThought)

    def test_format_kb_is_predict_not_cot(self):
        """FormatKB transzformáció — Predict, nem ChainOfThought (terv szerint)."""
        p = dspy.Predict(FormatKB)
        assert isinstance(p, dspy.Predict)


# ---------------------------------------------------------------------------
# Mezőnév-konzisztencia a schemas.py modellekkel
# ---------------------------------------------------------------------------

class TestSchemaConsistency:
    """A Signature mezőnevek egyeznek a schemas.py Pydantic mezőivel,
    hogy a program.forward() típusosan át tudja adni az adatokat.
    """

    def test_extract_outputs_match_storydata_context(self):
        """ExtractChange kimenetei (change_summary, key_steps, audience)
        bemenetként bekerülnek DraftSections-be — láncolhatóság."""
        extract_outs = set(_outputs(ExtractChange))
        draft_ins = set(_inputs(DraftSections))
        assert extract_outs == draft_ins, (
            "ExtractChange kimenetei és DraftSections bemenetei nem egyeznek — "
            "a pipeline láncolása el fog törni."
        )

    def test_draft_outputs_match_format_inputs(self):
        """DraftSections kimenetei bemenetként bekerülnek FormatKB-be."""
        draft_outs = set(_outputs(DraftSections))
        format_ins = set(_inputs(FormatKB))
        assert draft_outs == format_ins, (
            "DraftSections kimenetei és FormatKB bemenetei nem egyeznek."
        )

    def test_draft_outputs_subset_of_article_sections(self):
        """DraftSections kimenetei az ArticleSections mezőinek részhalmazát adják.

        Az `audience` nem DraftSections kimenet (az ExtractChange bemenetként
        kapja meg), de a program.forward() továbbítja az ArticleSections-be.
        Ezért a részhalmaz-ellenőrzés a helyes: minden DraftSections kimenet
        léteznie kell ArticleSections-ben is.
        """
        draft_outs = set(_outputs(DraftSections))
        article_fields = set(ArticleSections.model_fields.keys())
        assert draft_outs.issubset(article_fields), (
            f"DraftSections kimenetei ({draft_outs}) némelyike nem szerepel "
            f"ArticleSections mezői között ({article_fields})."
        )

    def test_audience_flows_from_extract_to_article(self):
        """Az audience az ExtractChange kimenete és ArticleSections mező is —
        a program.forward() továbbítja a két lépés között.
        """
        assert "audience" in _outputs(ExtractChange)
        assert "audience" in ArticleSections.model_fields

    def test_format_outputs_match_kb_article_subset(self):
        """FormatKB kimenete (html) egyezik a KBArticle.html mezővel."""
        format_outs = set(_outputs(FormatKB))
        assert "html" in format_outs
        assert "html" in KBArticle.model_fields

    def test_story_text_is_single_input(self):
        """ExtractChange egyetlen story_text bemenetet vár —
        nem külön mezőket. Ez a program.forward() szerződés."""
        assert _inputs(ExtractChange) == ["story_text"]
