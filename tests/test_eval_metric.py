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
        """Ha a generált HTML eltér a gold-tól (fejléc és tartalom is), a score alacsony.

        Megjegyzés (spec 004): az új súlyok (0.3/0.3/0.2/0.2) mellett a nem-hallucinált
        output 0.2 hallucination pontot kap, így a küszöb 0.45.
        """
        gold = dspy.Example(
            story_text="Test story",
            html="<h2>Problem</h2><p>Expected problem.</p><h2>Solution</h2><ol><li>Step 1.</li></ol>",
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
            html="<h2>Problem</h2><p>Expected problem.</p>",
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
