"""test_eval_gepa.py — the integration tests of the GEPA optimizer (dspy.GEPA)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import dspy
import pytest

from eval.dataset import load_gold_dataset
from eval.metric import rich_metric


class TestGEPAOptimizer:
    """The integration tests of the GEPA optimizer (dspy.GEPA)."""

    def test_gepa_optimizer_is_created_with_reflection_lm(self):
        """The GEPA optimizer is created with a reflection_lm (Kimi K3)."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        program = MagicMock()
        program.return_value = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p>"
        )

        with patch("eval.gepa_optimize.configure_lm"):
            from eval.gepa_optimize import run_gepa_optimization
            optimizer = run_gepa_optimization(program, trainset, valset)

        assert optimizer is not None
        # DSPy 3.2.x: the GEPA stores the metric in the metric_fn attribute
        assert hasattr(optimizer, "metric_fn")
        assert optimizer.metric_fn == rich_metric

    def test_gepa_optimizer_uses_kimi_k3_reflection(self):
        """The GEPA optimizer uses a Kimi K3 reflection model (temperature=1.0)."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        program = MagicMock()
        program.return_value = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p>"
        )

        with patch("eval.gepa_optimize.configure_lm"):
            from eval.gepa_optimize import run_gepa_optimization
            optimizer = run_gepa_optimization(program, trainset, valset)

        assert optimizer.reflection_lm is not None
        assert "kimi" in str(optimizer.reflection_lm.model).lower()
        # DSPy 3.2.x: the LM stores the temperature in the kwargs dict
        assert optimizer.reflection_lm.kwargs["temperature"] == 1.0

    def test_gepa_optimizer_uses_pareto_selection(self):
        """The GEPA optimizer uses the Pareto selection (candidate_selection_strategy="pareto")."""
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
        """The GEPA optimizer uses a log_dir (checkpointing)."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        program = MagicMock()
        program.return_value = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p>"
        )

        with patch("eval.gepa_optimize.configure_lm"):
            from eval.gepa_optimize import run_gepa_optimization
            optimizer = run_gepa_optimization(program, trainset, valset)

        assert optimizer.log_dir == "./gepa_logs"
