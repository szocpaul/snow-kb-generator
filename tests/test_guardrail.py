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


class TestDirectionGuardrail:
    """Spec 007: irány-sértő szekciók determinisztikus eltávolítása."""

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
    """<code> → <strong> normalizálás (szürke háttér tiltása a KB nézetben)."""

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
    """A guardrail az N/A-s irány-szekciót is eltávolítja (evidence-first: omit, ne N/A)."""

    def test_removes_na_only_inbound_section_for_outbound_story(self):
        from snow_kb.pipeline import strip_direction_violating_sections
        html = ("<h2>Overview / Summary</h2><p>Outbound flow.</p>"
                "<h2>Inbound Technical Implementation</h2><h3>Content</h3><ul><li>N/A</li></ul>"
                "<h2>Outbound Technical Implementation</h2><h3>Content</h3><ul><li>REST POST to Jira with payload.</li></ul>")
        result = strip_direction_violating_sections(html, "Implement outbound REST API, outbound payload to Jira.")
        assert "Inbound Technical Implementation" not in result
        assert "Outbound Technical Implementation" in result


class TestStripNaOnlySections:
    """Evidence-first guardrail: N/A-only szekciók eltávolítása."""

    def test_removes_na_only_section(self):
        from snow_kb.pipeline import strip_na_only_sections
        html = ("<h2>Overview / Summary</h2><p>Real content here about the change.</p>"
                "<h2>Known Issues</h2><h3>Content</h3><ul><li>N/A</li></ul>"
                "<h2>Testing Guide</h2><h3>Content</h3><ul><li>Run the tests and verify results.</li></ul>")
        result = strip_na_only_sections(html)
        assert "Known Issues" not in result
        assert "Overview / Summary" in result
        assert "Testing Guide" in result

    def test_keeps_sections_with_real_content(self):
        from snow_kb.pipeline import strip_na_only_sections
        html = "<h2>Known Issues</h2><h3>Content</h3><ul><li>Timeout errors were observed under heavy load conditions.</li></ul>"
        assert strip_na_only_sections(html) == html

    def test_removes_multiple_na_sections(self):
        from snow_kb.pipeline import strip_na_only_sections
        html = ("<h2>Overview</h2><p>x real</p>"
                "<h2>Known Issues</h2><h3>Content</h3><ul><li>N/A</li></ul>"
                "<h2>Investigation Steps</h2><h3>Content</h3><ul><li>N/A</li></ul>")
        result = strip_na_only_sections(html)
        assert "Known Issues" not in result
        assert "Investigation Steps" not in result


class TestSanitizeHtmlField:
    """HTML mező-tisztítás a story_text-hez (prod szemét ellen)."""

    def test_strips_style_blocks(self):
        from snow_kb.pipeline import sanitize_html_field
        html = '<h2>Overview</h2><style>body { color: red; } h1 { margin: 0; }</style><p>Real content</p>'
        result = sanitize_html_field(html)
        assert "<style" not in result
        assert "Real content" in result

    def test_strips_inline_style_attrs(self):
        from snow_kb.pipeline import sanitize_html_field
        html = '<span style="color: rgb(0,0,0);">Text</span>'
        assert 'style=' not in sanitize_html_field(html)

    def test_converts_code_to_strong(self):
        from snow_kb.pipeline import sanitize_html_field
        assert sanitize_html_field("<p><code>field_name</code></p>") == "<p><strong>field_name</strong></p>"

    def test_plain_text_unchanged(self):
        from snow_kb.pipeline import sanitize_html_field
        assert sanitize_html_field("plain text") == "plain text"
