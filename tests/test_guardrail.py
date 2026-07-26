"""test_guardrail.py — the tests of the hallucination guardrail (spec 004, US3)."""

from __future__ import annotations

from snow_kb.pipeline import strip_hallucinated_references


class TestStripHallucinatedReferences:
    """The tests of the strip_hallucinated_references() function."""

    STORY = "Story about Jira. Related article KB7654321 was updated during the fix."

    def test_strips_fictional_kb_reference_in_list_item(self):
        """The <li> that contains a fictional KB number is removed completely."""
        html = "<ul><li>Related: KB0012345</li><li>Real content</li></ul>"
        result = strip_hallucinated_references(html, self.STORY)
        assert "KB0012345" not in result
        assert "Real content" in result

    def test_keeps_real_kb_reference(self):
        """The (real) KB number that appears in the story_text stays untouched."""
        html = "<ul><li>See KB7654321 for details.</li></ul>"
        result = strip_hallucinated_references(html, self.STORY)
        assert result == html

    def test_idempotent_on_clean_html(self):
        """On a hallucination free HTML the function leaves everything unchanged."""
        html = "<h2>Problem</h2><p>No references here. Placeholder: KBXXXXXXX.</p>"
        assert strip_hallucinated_references(html, self.STORY) == html

    def test_replaces_bare_fictional_reference_with_placeholder(self):
        """A fictional reference that is not in an <li> is replaced with the placeholder."""
        html = "<p>For details see KB9999999 in the portal.</p>"
        result = strip_hallucinated_references(html, self.STORY)
        assert "KB9999999" not in result
        assert "KBXXXXXXX" in result
