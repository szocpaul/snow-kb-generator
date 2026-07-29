"""Spec 010 / T003: a GenerateKbFromTemplate signature stílus-blokk tesztjei.

Ellenőrzi, hogy a docstring tartalmazza a WRITING STYLE blokkot, és hogy a
benne szereplő tiltólista SZINKRONBAN van az eval.metric.BANNED_PHRASES-szel
(az SC-001 regex-ellenőrzés és a style judge ugyanazt a listát használja).
"""

from __future__ import annotations

from eval.metric import BANNED_PHRASES
from snow_kb.signatures import GenerateKbFromTemplate


class TestSignatureStyleBlock:
    def test_docstring_contains_style_block(self):
        doc = GenerateKbFromTemplate.__doc__ or ""
        assert "WRITING STYLE" in doc
        assert "senior engineer" in doc

    def test_docstring_contains_all_banned_phrases(self):
        """A docstring-ben felsorolt tiltólista lefedi a BANNED_PHRASES-t."""
        doc = GenerateKbFromTemplate.__doc__ or ""
        for phrase in BANNED_PHRASES:
            assert phrase in doc, f"A signature docstring-ből hiányzik: {phrase!r}"

    def test_banned_phrases_list_nonempty_and_lowercase_check(self):
        """A lista nem üres, és nincs benne duplikátum."""
        assert len(BANNED_PHRASES) >= 5
        assert len(BANNED_PHRASES) == len(set(BANNED_PHRASES))

    def test_existing_instructions_untouched(self):
        """FR-001: a meglévő instrukció-kulcsok megmaradtak a docstring-ben."""
        doc = GenerateKbFromTemplate.__doc__ or ""
        for anchor in [
            "The template is a MENU, not a mandate",
            "No evidence, no section",
            "NEVER use <code> tags",
            "Do NOT invent new headings",
        ]:
            assert anchor in doc, f"A meglévő instrukció eltűnt: {anchor!r}"
