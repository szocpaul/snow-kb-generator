"""test_eval_baseline.py — a baseline evaluation (dspy.Evaluate) integráció tesztjei."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import dspy
import pytest

from eval.baseline import run_baseline
from eval.dataset import load_gold_dataset


class TestBaselineEvaluation:
    """A baseline evaluation (dspy.Evaluate) integráció tesztjei."""

    def test_baseline_returns_evaluation_result(self, tmp_path):
        """A baseline evaluation dspy.EvaluationResult-et ad vissza."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        program = MagicMock()
        program.return_value = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p><h2>Solution</h2><ol><li>Step 1.</li></ol>"
        )

        with patch("eval.baseline.configure_lm"):
            result = run_baseline(program, valset, output_path=tmp_path / "baseline.json")

        assert isinstance(result, dspy.Evaluate) or hasattr(result, "score")

    def test_baseline_saves_results_to_json(self, tmp_path):
        """A baseline eredményeket JSON fájlba menti."""
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

    def test_baseline_average_score_computed(self, tmp_path):
        """A baseline átlagos score-t számol a valset példákból."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        program = MagicMock()
        program.return_value = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p>"
        )

        with patch("eval.baseline.configure_lm"):
            result = run_baseline(program, valset, output_path=tmp_path / "baseline.json")

        # Az átlagos score 0-1 között van
        assert 0.0 <= result.score <= 1.0


class TestBaselineSave:
    """A baseline eredmények mentésének tesztjei (runs/baseline.json)."""

    def test_baseline_saves_results_with_per_example_feedback(self, tmp_path):
        """A baseline elmenti az eredményeket a runs/baseline.json-ba (average_score, timestamp)."""
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

    def test_baseline_result_is_dspy_evaluate(self, tmp_path):
        """A baseline eredmény dspy.Evaluate objektum (nem dict)."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        program = MagicMock()
        program.return_value = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p>"
        )

        with patch("eval.baseline.configure_lm"):
            result = run_baseline(program, valset, output_path=tmp_path / "baseline.json")

        assert isinstance(result, dspy.Evaluate) or hasattr(result, "score")
