"""tests/test_verification_asymmetric.py — spec 015 T006: aszimmetrikus
the calibration metric with an asymmetric cost + the report schema tests (FAIL before the implementation).

The metric (plan KD1): the false "exists" (a missed hallucination: the gate let it through,
but the name does not exist) is penalized by FALSE_POS_EXISTS_COST, the false "does not exist"
(an unnecessary signal) is penalized by FALSE_NEG_COST; a good decision = 0. The ratio
10:1 (Key Decision 1), and NOT a hard-coded "random" value: it is a constant of the module.
"""

from __future__ import annotations

from eval.verification_asymmetric import (
    FALSE_NEG_COST,
    FALSE_POS_EXISTS_COST,
    build_calibration_report,
    case_cost,
    cost_summary,
)


def _row(predicted: str, expected: str) -> dict:
    return {"predicted": predicted, "expected": expected}


class TestAsymmetricCost:
    def test_cost_ratio_is_10_to_1(self):
        """Key Decision 1: the false 'exists' is 10x more expensive than the false signal."""
        assert FALSE_POS_EXISTS_COST == 10
        assert FALSE_NEG_COST == 1

    def test_false_positive_exists_costs_10(self):
        # predicted "ok" (= it exists according to the gate), expected "flag" (= it does not exist)
        # → a missed hallucination
        assert case_cost("ok", "flag") == FALSE_POS_EXISTS_COST

    def test_false_negative_costs_1(self):
        # predicted "flag", expected "ok" → an unnecessary signal (noise)
        assert case_cost("flag", "ok") == FALSE_NEG_COST

    def test_correct_decisions_cost_zero(self):
        assert case_cost("ok", "ok") == 0.0
        assert case_cost("flag", "flag") == 0.0

    def test_total_cost_aggregation(self):
        rows = [
            _row("ok", "ok"),      # 0
            _row("flag", "flag"),  # 0
            _row("ok", "flag"),    # 10 — a missed hallucination
            _row("flag", "ok"),    # 1  — an unnecessary signal
            _row("flag", "ok"),    # 1
        ]
        summary = cost_summary(rows)
        assert summary["n"] == 5
        assert summary["total_cost"] == 12.0
        assert summary["false_pos_exists"] == 1
        assert summary["false_neg"] == 2

    def test_symmetric_cost_is_plain_error_count(self):
        """The symmetric counter value: both error types cost 1-1 (the 014 metric)."""
        rows = [_row("ok", "flag"), _row("flag", "ok"), _row("ok", "ok")]
        summary = cost_summary(rows)
        assert summary["symmetric_cost"] == 2.0


class TestCalibrationReportSchema:
    """The report schema (spec US2: before/after the threshold, before/after the cost,
    szimmetrikus osszevetes, dontes + indoklas)."""

    def test_report_schema_keys(self):
        rows = [_row("ok", "ok"), _row("ok", "flag")]
        report = build_calibration_report(
            threshold_before=0.7,
            threshold_after=0.85,
            rows_before=rows,
            rows_after=[_row("flag", "flag")],
        )
        for key in ("threshold_before", "threshold_after",
                    "cost_before", "cost_after",
                    "symmetric_cost_before", "symmetric_cost_after",
                    "decision", "rationale"):
            assert key in report, f"The report key is missing: {key}"
        assert report["threshold_before"] == 0.7
        assert report["threshold_after"] == 0.85

    def test_decision_stays_when_not_better(self):
        """If the new threshold is NOT better in asymmetric cost, the decision is 'stays'
        + a justification (not a silent stay — spec US2 2. scenario)."""
        rows_bad = [_row("ok", "flag")] * 3   # the old ones: 3 missed = 30
        rows_worse = rows_bad + [_row("flag", "ok")]  # uj: 30 + 1 = 31, rosszabb
        report = build_calibration_report(
            threshold_before=0.7, threshold_after=0.9,
            rows_before=rows_bad, rows_after=rows_worse,
        )
        assert report["decision"] == "marad"
        assert report["threshold_after"] == 0.7  # it is not put into effect
        assert report["rationale"]

    def test_decision_changes_when_strictly_better(self):
        rows_bad = [_row("ok", "flag")] * 3   # 30
        rows_good = [_row("flag", "flag")] * 2 + [_row("flag", "ok")]  # 1
        report = build_calibration_report(
            threshold_before=0.7, threshold_after=0.85,
            rows_before=rows_bad, rows_after=rows_good,
        )
        assert report["decision"] == "valtozik"
        assert report["threshold_after"] == 0.85
        assert report["cost_before"] == 30.0
        assert report["cost_after"] == 1.0
