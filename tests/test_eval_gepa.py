"""test_eval_gepa.py — a GEPA optimizer (dspy.GEPA) integráció tesztjei."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import dspy
import pytest

from eval.dataset import load_gold_dataset
from eval.metric import rich_metric


class TestGEPAOptimizer:
    """A GEPA optimizer (dspy.GEPA) integráció tesztjei."""

    def test_gepa_optimizer_is_created_with_reflection_lm(self):
        """A GEPA optimizer reflection_lm-mel jön létre (Kimi K3)."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        program = MagicMock()
        program.return_value = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p>"
        )

        with patch("eval.gepa_optimize.configure_lm"):
            from eval.gepa_optimize import run_gepa_optimization
            optimizer = run_gepa_optimization(program, trainset, valset)

        assert optimizer is not None
        # DSPy 3.2.x: a GEPA a metrikát metric_fn attribútumban tárolja
        assert hasattr(optimizer, "metric_fn")
        assert optimizer.metric_fn == rich_metric

    def test_gepa_optimizer_uses_kimi_k3_reflection(self):
        """A GEPA optimizer Kimi K3 reflection modellt használ (temperature=1.0)."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        program = MagicMock()
        program.return_value = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p>"
        )

        with patch("eval.gepa_optimize.configure_lm"):
            from eval.gepa_optimize import run_gepa_optimization
            optimizer = run_gepa_optimization(program, trainset, valset)

        assert optimizer.reflection_lm is not None
        assert "k3" in str(optimizer.reflection_lm.model).lower()  # openai/k3 (Kimi K3 wire id)
        # DSPy 3.2.x: az LM a temperature-t a kwargs dict-ben tárolja
        assert optimizer.reflection_lm.kwargs["temperature"] == 1.0

    def test_gepa_optimizer_uses_pareto_selection(self):
        """A GEPA optimizer Pareto szelekciót használ (candidate_selection_strategy="pareto")."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        program = MagicMock()
        program.return_value = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p>"
        )

        with patch("eval.gepa_optimize.configure_lm"):
            from eval.gepa_optimize import run_gepa_optimization
            optimizer = run_gepa_optimization(program, trainset, valset)

        assert optimizer.candidate_selection_strategy == "pareto"

    def test_gepa_optimizer_uses_log_dir(self):
        """A GEPA optimizer log_dir-t használ (checkpointing)."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        program = MagicMock()
        program.return_value = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p>"
        )

        with patch("eval.gepa_optimize.configure_lm"):
            from eval.gepa_optimize import run_gepa_optimization
            optimizer = run_gepa_optimization(program, trainset, valset)

        assert optimizer.log_dir == "./gepa_logs"
