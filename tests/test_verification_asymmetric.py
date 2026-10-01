"""tests/test_verification_asymmetric.py — spec 015 T006: aszimmetrikus
költségű kalibrációs metrika + riport-séma tesztjei (FAIL implementáció előtt).

A metrika (plan KD1): a téves "létező" (átsikló hallucináció: a gate átengedte,
pedig a név nem létezik) FALSE_POS_EXISTS_COST-szoros, a téves "nem létező"
(felesleges jelzés) FALSE_NEG_COST-szoros büntetés; jó döntés = 0. Az arány
10:1 (Key Decision 1), és NEM hard-coded "véletlen" érték: a modul konstansa.
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
        """Key Decision 1: a téves 'létező' 10x dragabb, mint a téves jelzés."""
        assert FALSE_POS_EXISTS_COST == 10
        assert FALSE_NEG_COST == 1

    def test_false_positive_exists_costs_10(self):
        # predicted "ok" (= a gate szerint létezik), expected "flag" (= nem létezik)
        # → átsikló hallucináció
        assert case_cost("ok", "flag") == FALSE_POS_EXISTS_COST

    def test_false_negative_costs_1(self):
        # predicted "flag", expected "ok" → felesleges jelzés (zaj)
        assert case_cost("flag", "ok") == FALSE_NEG_COST

    def test_correct_decisions_cost_zero(self):
        assert case_cost("ok", "ok") == 0.0
        assert case_cost("flag", "flag") == 0.0

    def test_total_cost_aggregation(self):
        rows = [
            _row("ok", "ok"),      # 0
            _row("flag", "flag"),  # 0
            _row("ok", "flag"),    # 10 — átsikló hallucináció
            _row("flag", "ok"),    # 1  — felesleges jelzés
            _row("flag", "ok"),    # 1
        ]
        summary = cost_summary(rows)
        assert summary["n"] == 5
        assert summary["total_cost"] == 12.0
        assert summary["false_pos_exists"] == 1
        assert summary["false_neg"] == 2

    def test_symmetric_cost_is_plain_error_count(self):
        """A szimmetrikus ellenérték: mindkét hibafajta 1-1 (a 014-es metrika)."""
        rows = [_row("ok", "flag"), _row("flag", "ok"), _row("ok", "ok")]
        summary = cost_summary(rows)
        assert summary["symmetric_cost"] == 2.0


class TestCalibrationReportSchema:
    """A riport-séma (spec US2: threshold elott/utana, koltseg elott/utana,
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
            assert key in report, f"hiányzó riport-kulcs: {key}"
        assert report["threshold_before"] == 0.7
        assert report["threshold_after"] == 0.85

    def test_decision_stays_when_not_better(self):
        """Ha az uj threshold NEM jobb aszimmetrikus koltsegu, a dontes 'marad'
        + indoklas (nem csendes maradas — spec US2 2. scenario)."""
        rows_bad = [_row("ok", "flag")] * 3   # regi: 3 átsikló = 30
        rows_worse = rows_bad + [_row("flag", "ok")]  # uj: 30 + 1 = 31, rosszabb
        report = build_calibration_report(
            threshold_before=0.7, threshold_after=0.9,
            rows_before=rows_bad, rows_after=rows_worse,
        )
        assert report["decision"] == "marad"
        assert report["threshold_after"] == 0.7  # nem lep eletbe
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
