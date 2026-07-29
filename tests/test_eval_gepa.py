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
        assert "k3" in str(optimizer.reflection_lm.model).lower()  # openai/k3 (Kimi K3 wire id)
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


class TestInstructionProposer:
    """US4 (spec 007): the GEPA uses the SkilledProposer with an evidence-first guidance."""

    def test_proposer_is_skilled_proposer_with_guidance(self):
        """The _create_instruction_proposer() gives a SkilledProposer with the evidence-first rule."""
        from eval.gepa_optimize import _create_instruction_proposer

        proposer = _create_instruction_proposer()
        assert type(proposer).__name__ == "SkilledProposer"

    def test_proposer_guidance_contains_style_rules(self):
        """T009 (spec 010): the guidance contains the style rules AND the evidence-first rules as well."""
        from eval.gepa_optimize import _EVIDENCE_FIRST_GUIDANCE

        # The style focus (US3)
        assert "WRITING STYLE" in _EVIDENCE_FIRST_GUIDANCE
        assert "senior engineer" in _EVIDENCE_FIRST_GUIDANCE
        assert "boilerplate" in _EVIDENCE_FIRST_GUIDANCE.lower()
        # The existing rules STAY (FR-005)
        assert "no 'N/A' placeholders" in _EVIDENCE_FIRST_GUIDANCE
        assert "Never invent KB article" in _EVIDENCE_FIRST_GUIDANCE
        assert "omit the 'Inbound Technical Implementation' section" in _EVIDENCE_FIRST_GUIDANCE

    def test_gepa_optimizer_uses_proposer(self):
        """The GEPA optimizer receives the instruction_proposer."""
        from unittest.mock import MagicMock, patch

        from eval.dataset import load_gold_dataset

        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        with patch("eval.gepa_optimize.configure_lm"):
            from eval.gepa_optimize import run_gepa_optimization
            optimizer = run_gepa_optimization(MagicMock(), trainset, valset)

        assert optimizer.custom_instruction_proposer is not None
        assert type(optimizer.custom_instruction_proposer).__name__ == "SkilledProposer"

    def test_fallback_when_skilled_proposer_missing(self):
        """On an import error the stock proposer (None) + a warning."""
        import sys
        import warnings

        from eval import gepa_optimize

        with patch.dict(sys.modules, {"skilled_proposer": None}):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                proposer = gepa_optimize._create_instruction_proposer()
        assert proposer is None
        assert any("skilled-proposer" in str(x.message) for x in w)
