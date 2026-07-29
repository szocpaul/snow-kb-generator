"""test_eval_metric.py — a rich_metric (GEPA contract) tesztjei."""

from __future__ import annotations

import dspy
import pytest

from eval.metric import rich_metric


class TestRichMetric:
    """A rich_metric függvény (GEPA contract) tesztjei."""

    def test_returns_prediction_with_score_and_feedback(self):
        """A metric dspy.Prediction(score=float, feedback=str) formátumban tér vissza."""
        gold = dspy.Example(
            story_text="Test story about LDAP fix",
            html="<h2>Problem</h2><p>LDAP auth failed.</p><h2>Solution</h2><ol><li>Retry.</li></ol>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Problem</h2><p>LDAP auth failed.</p><h2>Solution</h2><ol><li>Retry.</li></ol>"
        )

        result = rich_metric(gold, pred)

        assert isinstance(result, dspy.Prediction)
        assert isinstance(result.score, float)
        assert 0.0 <= result.score <= 1.0
        assert isinstance(result.feedback, str)
        assert len(result.feedback) > 10

    def test_perfect_match_returns_high_score(self):
        """Ha a generált HTML tökéletesen egyezik, a score magas (0.8+)."""
        gold = dspy.Example(
            story_text="Test story",
            html="<h2>Problem</h2><p>Same problem.</p><h2>Solution</h2><ol><li>Step 1.</li></ol>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p><h2>Solution</h2><ol><li>Step 1.</li></ol>"
        )

        result = rich_metric(gold, pred)

        assert result.score > 0.8, f"Perfect match should score > 0.8, got {result.score}"
        assert "Correct" in result.feedback or "perfect" in result.feedback.lower()

    def test_mismatch_returns_low_score(self):
        """Ha a generált HTML eltér a gold-tól (fejléc és tény is), a score alacsony.

        Megjegyzés (spec 010): a content tengely tény-azonosítókat illeszt (stílus-
        semleges), ezért a példa szándékosan azonosító-dús — a pred-ben ezek hiányoznak.
        """
        gold = dspy.Example(
            story_text="Test story",
            html="<h2>Problem</h2><p>LDAP query timeout in LDAP_Retry_Authenticator on u_user table.</p>"
            "<h2>Solution</h2><ol><li>Step 1.</li></ol>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Different</h2><p>Wrong content entirely.</p>"
        )

        result = rich_metric(gold, pred)

        assert result.score < 0.45, f"Mismatch should score < 0.45, got {result.score}"
        assert "mismatch" in result.feedback.lower() or "wrong" in result.feedback.lower()

    def test_feedback_is_natural_language(self):
        """A feedback természetes nyelvű kritika (nem csak "error")."""
        gold = dspy.Example(
            story_text="Test story",
            html="<h2>Problem</h2><p>LDAP timeout in LDAP_Retry_Authenticator.</p>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Different</h2><p>Wrong content.</p>"
        )

        result = rich_metric(gold, pred)

        # A feedback-nek konkrétumot kell tartalmaznia (miért rossz)
        assert len(result.feedback) > 30, f"Feedback too short: {result.feedback}"
        # A feedback tartalmazza a "mismatch" vagy "wrong" szót, vagy konkrétumot
        assert any(word in result.feedback.lower() for word in ["mismatch", "wrong", "expected", "missing", "incorrect"])

    def test_not_a_dict(self):
        """A metric NEM dict-et ad vissza (GEPA contract)."""
        gold = dspy.Example(story_text="Test", html="<h2>A</h2>").with_inputs("story_text")
        pred = dspy.Prediction(html="<h2>A</h2>")

        result = rich_metric(gold, pred)

        assert not isinstance(result, dict), "Metric must return dspy.Prediction, not dict (GEPA contract)"


class TestHallucinationAxis:
    """US2 (spec 004): a rich_metric bünteti a hallucinált KB hivatkozásokat."""

    def _gold(self):
        return dspy.Example(
            story_text="Story about Jira integration. Related article: KB7654321 was updated.",
            html="<h2>Problem</h2><p>Expected problem.</p>",
        ).with_inputs("story_text")

    def test_fictional_kb_number_is_penalized(self):
        """A story_text-ben NEM szereplő KB szám hallucináció: score csökken + feedback."""
        pred = dspy.Prediction(
            html="<h2>Problem</h2><p>Expected problem.</p><p>See also KB0012345.</p>"
        )
        result = rich_metric(self._gold(), pred)
        assert "KB0012345" in result.feedback
        assert "Hallucinated" in result.feedback

    def test_real_kb_number_is_not_penalized(self):
        """A story_text-ben szereplő KB szám (KB7654321) nem számít hallucinációnak."""
        pred = dspy.Prediction(
            html="<h2>Problem</h2><p>Expected problem.</p><p>See also KB7654321.</p>"
        )
        result = rich_metric(self._gold(), pred)
        assert "Hallucinated" not in result.feedback

    def test_placeholder_is_not_penalized(self):
        """A KBXXXXXXX placeholder és az N/A nem számít hallucinációnak."""
        pred = dspy.Prediction(
            html="<h2>Problem</h2><p>Expected problem.</p><p>Related: KBXXXXXXX or N/A.</p>"
        )
        result = rich_metric(self._gold(), pred)
        assert "Hallucinated" not in result.feedback


class TestHallucinationKnownRefs:
    """US3 (spec 005): a metric a related_articles_context-et is ismeri."""

    def test_related_context_kb_number_is_not_penalized(self):
        gold = dspy.Example(
            story_text="Story about Jira.",
            related_articles_context="KB7654321 | Jira API Authentication Setup",
            html="<h2>Problem</h2><p>Expected problem.</p>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Problem</h2><p>Expected problem.</p><p>See KB7654321.</p>"
        )
        result = rich_metric(gold, pred)
        assert "Hallucinated" not in result.feedback


class TestDirectionViolation:
    """US1 (spec 007): irány-érzékeny template_adherence."""

    OUTBOUND_STORY = "Implement Outbound REST API for Jira bug creation. The outbound payload is sent to Jira."
    GOLD_OUTBOUND = "<h2>Overview / Summary</h2><p>Outbound integration.</p>"

    def test_outbound_story_with_filled_inbound_is_penalized(self):
        """Outbound story + kitöltött Inbound szekció → Direction violation feedback."""
        pred = dspy.Prediction(
            html="<h2>Overview / Summary</h2><p>Outbound integration.</p>"
            "<h2>Inbound Technical Implementation</h2><h3>Content</h3>"
            "<ul><li>Script Includes: JiraIntegrationUtils parses and validates the incoming payload data.</li></ul>"
        )
        gold = dspy.Example(story_text=self.OUTBOUND_STORY, html=self.GOLD_OUTBOUND).with_inputs("story_text")
        result = rich_metric(gold, pred)
        assert "Direction violation" in result.feedback
        assert "Inbound Technical Implementation" in result.feedback

    def test_outbound_story_without_inbound_is_ok(self):
        """Outbound story + Inbound szekció hiányzik/N/A → nincs büntetés."""
        pred = dspy.Prediction(html="<h2>Overview / Summary</h2><p>Outbound integration.</p>")
        gold = dspy.Example(story_text=self.OUTBOUND_STORY, html=self.GOLD_OUTBOUND).with_inputs("story_text")
        result = rich_metric(gold, pred)
        assert "Direction violation" not in result.feedback

    def test_both_directions_skips_check(self):
        """Ha a story mindkét irányt említi, az irány-ellenőrzés kihagyott."""
        gold = dspy.Example(
            story_text="Bidirectional sync: inbound webhook and outbound REST call.",
            html=self.GOLD_OUTBOUND,
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Overview / Summary</h2><p>Sync.</p>"
            "<h2>Inbound Technical Implementation</h2><h3>Content</h3>"
            "<ul><li>The inbound webhook listener receives Jira events and maps fields to incidents.</li></ul>"
        )
        result = rich_metric(gold, pred)
        assert "Direction violation" not in result.feedback

    def test_detect_direction_helper(self):
        from eval.metric import detect_direction
        assert detect_direction("Outbound REST API, outbound payload") == "outbound"
        assert detect_direction("Inbound webhook listener") == "inbound"
        assert detect_direction("inbound and outbound sync") == "both"
        assert detect_direction("REST integration") == "unknown"


class TestUnsupportedSection:
    """US1 (spec 007): a gold szerint támogatatlan szekció büntetve van."""

    def test_section_absent_in_gold_but_filled_in_pred(self):
        gold = dspy.Example(
            story_text="Simple story about config change.",
            html="<h2>Overview / Summary</h2><p>Config updated.</p>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Overview / Summary</h2><p>Config updated.</p>"
            "<h2>Testing Guide</h2><h3>Content</h3>"
            "<ul><li>Run the full regression test suite and verify all integration points behave correctly.</li></ul>"
        )
        result = rich_metric(gold, pred)
        assert "Unsupported section" in result.feedback
        assert "Testing Guide" in result.feedback


class TestNAOnlySections:
    """Spec 007 kiegészítés: az N/A-only szekció büntetése, ha a gold kihagyja."""

    def test_na_only_section_penalized_when_gold_omits(self):
        """Pred-ben 'Known Issues / N/A', goldban nincs ilyen szekció → büntetés + feedback."""
        gold = dspy.Example(
            story_text="Outbound REST integration to Jira, outbound payload.",
            html="<h2>Overview / Summary</h2><p>Outbound integration.</p>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Overview / Summary</h2><p>Outbound integration.</p>"
            "<h2>Known Issues</h2><h3>Content</h3><ul><li>N/A</li></ul>"
        )
        result = rich_metric(gold, pred)
        assert "N/A-only section" in result.feedback
        assert "Known Issues" in result.feedback

    def test_na_only_section_ok_when_gold_has_it(self):
        """Ha a goldban is megvan a szekció, az N/A-only pred nem büntetett itt."""
        gold = dspy.Example(
            story_text="Simple story.",
            html="<h2>Overview / Summary</h2><p>X.</p><h2>Known Issues</h2><h3>Content</h3><ul><li>Some real issue documented here.</li></ul>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Overview / Summary</h2><p>X.</p><h2>Known Issues</h2><h3>Content</h3><ul><li>N/A</li></ul>"
        )
        result = rich_metric(gold, pred)
        assert "N/A-only section" not in result.feedback

    def test_omitted_section_is_clean(self):
        """A gold szerint kihagyott szekció tényleges kihagyása → semmilyen feedback."""
        gold = dspy.Example(
            story_text="Outbound integration.",
            html="<h2>Overview / Summary</h2><p>Outbound integration.</p>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(html="<h2>Overview / Summary</h2><p>Outbound integration.</p>")
        result = rich_metric(gold, pred)
        assert "N/A-only section" not in result.feedback
        assert "Unsupported section" not in result.feedback
