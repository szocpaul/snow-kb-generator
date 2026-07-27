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


class TestGuardrailKnownRefs:
    """US3 (spec 005): the real KB search hits are not hallucinations (0 false positive)."""

    def test_known_refs_from_search_are_kept(self):
        """The real KB number that appears in the related_articles_context stays untouched."""
        html = "<ul><li>See KB7654321 for details.</li><li>Fake KB0012345</li></ul>"
        known = "KB7654321 | Jira API Authentication Setup"
        result = strip_hallucinated_references(html, "Story without any refs.", known_refs=known)
        assert "KB7654321" in result
        assert "KB0012345" not in result


class TestDirectionGuardrail:
    """Spec 007: the deterministic removal of the direction-violating sections."""

    def test_removes_inbound_section_for_outbound_story(self):
        from snow_kb.pipeline import strip_direction_violating_sections
        html = ("<h2>Overview / Summary</h2><p>Outbound flow.</p>"
                "<h2>Inbound Technical Implementation</h2><h3>Content</h3>"
                "<ul><li>JiraIntegrationUtils builds the payload for Jira issue creation.</li></ul>"
                "<h2>Outbound Technical Implementation</h2><h3>Content</h3><ul><li>REST POST.</li></ul>")
        result = strip_direction_violating_sections(html, "Implement outbound REST API for Jira, outbound payload.")
        assert "Inbound Technical Implementation" not in result
        assert "Outbound Technical Implementation" in result
        assert "Overview / Summary" in result

    def test_keeps_section_when_both_directions(self):
        from snow_kb.pipeline import strip_direction_violating_sections
        html = ("<h2>Inbound Technical Implementation</h2><h3>Content</h3>"
                "<ul><li>The inbound webhook receives Jira events and maps fields.</li></ul>")
        assert strip_direction_violating_sections(html, "inbound webhook and outbound REST sync") == html

    def test_idempotent_when_section_absent(self):
        from snow_kb.pipeline import strip_direction_violating_sections
        html = "<h2>Overview / Summary</h2><p>Only overview.</p>"
        assert strip_direction_violating_sections(html, "outbound integration") == html


class TestNormalizeCodeTags:
    """<code> → <strong> normalization (the grey background is forbidden in the KB view)."""

    def test_replaces_code_with_strong(self):
        from snow_kb.pipeline import normalize_code_tags
        html = '<p>Field: <code>u_jira_key</code> and endpoint <code class="x">/rest/api/2/issue</code>.</p>'
        result = normalize_code_tags(html)
        assert "<code" not in result
        assert "<strong>u_jira_key</strong>" in result
        assert "<strong>/rest/api/2/issue</strong>" in result

    def test_idempotent_without_code(self):
        from snow_kb.pipeline import normalize_code_tags
        html = "<p>No tags here, <strong>already strong</strong>.</p>"
        assert normalize_code_tags(html) == html


class TestDirectionGuardrailNA:
    """The guardrail also removes the N/A direction section (evidence-first: omit, not N/A)."""

    def test_removes_na_only_inbound_section_for_outbound_story(self):
        from snow_kb.pipeline import strip_direction_violating_sections
        html = ("<h2>Overview / Summary</h2><p>Outbound flow.</p>"
                "<h2>Inbound Technical Implementation</h2><h3>Content</h3><ul><li>N/A</li></ul>"
                "<h2>Outbound Technical Implementation</h2><h3>Content</h3><ul><li>REST POST to Jira with payload.</li></ul>")
        result = strip_direction_violating_sections(html, "Implement outbound REST API, outbound payload to Jira.")
        assert "Inbound Technical Implementation" not in result
        assert "Outbound Technical Implementation" in result
