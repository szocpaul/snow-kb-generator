"""Spec 010 / T003: the style block tests of the GenerateKbFromTemplate signature.

It checks that the docstring contains the WRITING STYLE block, and that the
prohibition list in it is IN SYNC with the eval.metric.BANNED_PHRASES
(the SC-001 regex check and the style judge use the same list).
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
        """The prohibition list listed in the docstring covers the BANNED_PHRASES."""
        doc = GenerateKbFromTemplate.__doc__ or ""
        for phrase in BANNED_PHRASES:
            assert phrase in doc, f"It is missing from the signature docstring: {phrase!r}"

    def test_banned_phrases_list_nonempty_and_lowercase_check(self):
        """The list is not empty and it has no duplicates."""
        assert len(BANNED_PHRASES) >= 5
        assert len(BANNED_PHRASES) == len(set(BANNED_PHRASES))

    def test_existing_instructions_untouched(self):
        """FR-001: the existing instruction anchors stayed in the docstring."""
        doc = GenerateKbFromTemplate.__doc__ or ""
        for anchor in [
            "The template is a MENU, not a mandate",
            "No evidence, no section",
            "NEVER use <code> tags",
            "Do NOT invent new headings",
        ]:
            assert anchor in doc, f"The existing instruction disappeared: {anchor!r}"
