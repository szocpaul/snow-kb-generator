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
        """Ha a generált HTML eltér a gold-tól (fejléc és tartalom is), a score alacsony (0.3 alatt)."""
        gold = dspy.Example(
            story_text="Test story",
            html="<h2>Problem</h2><p>Expected problem.</p><h2>Solution</h2><ol><li>Step 1.</li></ol>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Different</h2><p>Wrong content entirely.</p>"
        )

        result = rich_metric(gold, pred)

        assert result.score < 0.3, f"Mismatch should score < 0.3, got {result.score}"
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
