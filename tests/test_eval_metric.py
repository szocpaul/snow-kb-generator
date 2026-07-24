"""test_eval_metric.py — a rich_metric (GEPA contract) tesztjei."""

from __future__ import annotations

import dspy
import pytest

from eval.metric import rich_metric


class TestRichMetric:
    """The tests of the rich_metric function (the GEPA contract)."""

    def test_returns_prediction_with_score_and_feedback(self):
        """The metric returns in the dspy.Prediction(score=float, feedback=str) format."""
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
        """If the generated HTML matches perfectly, the score is high (0.8+)."""
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
        """If the generated HTML differs from the gold (header and content too), the score is low (below 0.3)."""
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
        """The feedback is a critique in natural language (not just "error")."""
        gold = dspy.Example(
            story_text="Test story",
            html="<h2>Problem</h2><p>Expected problem.</p>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Different</h2><p>Wrong content.</p>"
        )

        result = rich_metric(gold, pred)

        # The feedback has to contain a concrete detail (why it is bad)
        assert len(result.feedback) > 30, f"Feedback too short: {result.feedback}"
        # The feedback contains the word "mismatch" or "wrong", or a concrete detail
        assert any(word in result.feedback.lower() for word in ["mismatch", "wrong", "expected", "missing", "incorrect"])

    def test_not_a_dict(self):
        """The metric does NOT return a dict (GEPA contract)."""
        gold = dspy.Example(story_text="Test", html="<h2>A</h2>").with_inputs("story_text")
        pred = dspy.Prediction(html="<h2>A</h2>")

        result = rich_metric(gold, pred)

        assert not isinstance(result, dict), "Metric must return dspy.Prediction, not dict (GEPA contract)"
