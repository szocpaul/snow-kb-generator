"""test_guardrail.py — a hallucináció-guardrail tesztjei (spec 004, US3)."""

from __future__ import annotations

from snow_kb.pipeline import strip_hallucinated_references


class TestStripHallucinatedReferences:
    """A strip_hallucinated_references() függvény tesztjei."""

    STORY = "Story about Jira. Related article KB7654321 was updated during the fix."

    def test_strips_fictional_kb_reference_in_list_item(self):
        """A fiktív KB számot tartalmazó <li> teljesen eltávolítódik."""
        html = "<ul><li>Related: KB0012345</li><li>Real content</li></ul>"
        result = strip_hallucinated_references(html, self.STORY)
        assert "KB0012345" not in result
        assert "Real content" in result

    def test_keeps_real_kb_reference(self):
        """A story_text-ben szereplő (valódi) KB szám érintetlen marad."""
        html = "<ul><li>See KB7654321 for details.</li></ul>"
        result = strip_hallucinated_references(html, self.STORY)
        assert result == html

    def test_idempotent_on_clean_html(self):
        """Hallucináció-mentes HTML-en a függvény változatlanul hagy mindent."""
        html = "<h2>Problem</h2><p>No references here. Placeholder: KBXXXXXXX.</p>"
        assert strip_hallucinated_references(html, self.STORY) == html

    def test_replaces_bare_fictional_reference_with_placeholder(self):
        """Nem <li>-ben szereplő fiktív hivatkozás placeholder-re cserélődik."""
        html = "<p>For details see KB9999999 in the portal.</p>"
        result = strip_hallucinated_references(html, self.STORY)
        assert "KB9999999" not in result
        assert "KBXXXXXXX" in result


class TestGuardrailKnownRefs:
    """US3 (spec 005): a valódi KB keresési találatok nem hallucinációk (0 false positive)."""

    def test_known_refs_from_search_are_kept(self):
        """A related_articles_context-ben szereplő valódi KB szám érintetlen marad."""
        html = "<ul><li>See KB7654321 for details.</li><li>Fake KB0012345</li></ul>"
        known = "KB7654321 | Jira API Authentication Setup"
        result = strip_hallucinated_references(html, "Story without any refs.", known_refs=known)
        assert "KB7654321" in result
        assert "KB0012345" not in result
