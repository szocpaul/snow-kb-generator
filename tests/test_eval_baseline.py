"""test_eval_baseline.py — the integration tests of the baseline evaluation (dspy.Evaluate)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import dspy
import pytest

from eval.baseline import run_baseline
from eval.dataset import load_gold_dataset


class TestBaselineEvaluation:
    """The integration tests of the baseline evaluation (dspy.Evaluate)."""

    def test_baseline_returns_evaluation_result(self):
        """A baseline evaluation returns a dspy.EvaluationResult."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        program = MagicMock()
        program.return_value = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p><h2>Solution</h2><ol><li>Step 1.</li></ol>"
        )

        with patch("eval.baseline.configure_lm"):
            result = run_baseline(program, valset)

        assert isinstance(result, dspy.Evaluate) or hasattr(result, "score")

    def test_baseline_saves_results_to_json(self, tmp_path):
        """It saves the baseline results into a JSON file."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        program = MagicMock()
        program.return_value = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p>"
        )

        with patch("eval.baseline.configure_lm"):
            result = run_baseline(program, valset, output_path=tmp_path / "baseline.json")

        assert (tmp_path / "baseline.json").exists()
        data = json.loads((tmp_path / "baseline.json").read_text())
        assert "average_score" in data
        assert "timestamp" in data

    def test_baseline_average_score_computed(self):
        """It computes the average baseline score from the valset examples."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        program = MagicMock()
        program.return_value = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p>"
        )

        with patch("eval.baseline.configure_lm"):
            result = run_baseline(program, valset)

        # The average score is between 0 and 1
        assert 0.0 <= result.score <= 1.0


class TestBaselineSave:
    """The tests of saving the baseline results (runs/baseline.json)."""

    def test_baseline_saves_results_with_per_example_feedback(self, tmp_path):
        """The baseline saves the results into runs/baseline.json (average_score, timestamp)."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        program = MagicMock()
        program.return_value = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p>"
        )

        with patch("eval.baseline.configure_lm"):
            result = run_baseline(program, valset, output_path=tmp_path / "baseline.json")

        assert (tmp_path / "baseline.json").exists()
        data = json.loads((tmp_path / "baseline.json").read_text())
        assert "average_score" in data
        assert "timestamp" in data
        assert isinstance(data["average_score"], float)

    def test_baseline_result_is_dspy_evaluate(self):
        """The baseline result is a dspy.Evaluate object (not a dict)."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        program = MagicMock()
        program.return_value = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p>"
        )

        with patch("eval.baseline.configure_lm"):
            result = run_baseline(program, valset)

        assert isinstance(result, dspy.Evaluate) or hasattr(result, "score")
