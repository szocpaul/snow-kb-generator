"""eval/verification_asymmetric.py — spec 015: the metric with an asymmetric cost.

The 014 calibration metric was SYMMETRIC (both error types cost the same).
"In reality (spec Background):
  - a false "exists" (the gate let the hallucinated name through) is much more expensive —
    it misleads the engineer reading the article;
  - a false "does not exist" (an unnecessary signal) is at most noise.

Cost ratio (plan Key Decision 1): 10:1. The sensitivity analysis (5:1, 20:1)
is part of the calibration report; if the threshold is insensitive to the ratio, the
simpler 10:1 stays.

The "predicted"/"expected" values are the shapes of the 014 measurement: "ok" (according to the gate
it exists / does not signal) and "flag" (the gate signalled: a non-existent name).
"""

from __future__ import annotations

FALSE_POS_EXISTS_COST = 10  # a false "exists" (a missed hallucination)
FALSE_NEG_COST = 1          # a false "does not exist" (an unnecessary signal)


def case_cost(predicted: str, expected: str,
              fp_cost: float = FALSE_POS_EXISTS_COST,
              fn_cost: float = FALSE_NEG_COST) -> float:
    """The asymmetric cost of a single case.

    predicted="ok", expected="flag"  → a false "exists" (fp_cost)
    predicted="flag", expected="ok"  → a false "does not exist" (fn_cost)
    a match                            → 0
    """
    if predicted == expected:
        return 0.0
    return fp_cost if predicted == "ok" else fn_cost


def cost_summary(rows: list[dict],
                 fp_cost: float = FALSE_POS_EXISTS_COST,
                 fn_cost: float = FALSE_NEG_COST) -> dict:
    """The total cost on a predicted/expected row list."""
    fp = sum(1 for r in rows if r["predicted"] == "ok" and r["expected"] == "flag")
    fn = sum(1 for r in rows if r["predicted"] == "flag" and r["expected"] == "ok")
    return {
        "n": len(rows),
        "false_pos_exists": fp,
        "false_neg": fn,
        "total_cost": float(fp * fp_cost + fn * fn_cost),
        "symmetric_cost": float(fp + fn),
        "fp_cost": fp_cost,
        "fn_cost": fn_cost,
    }


def build_calibration_report(*, threshold_before: float, threshold_after: float,
                             rows_before: list[dict], rows_after: list[dict]) -> dict:
    """The calibration report (spec US2 Acceptance 1-2).

    The decision rule (the reference pattern: "if it does not beat it → it stays"):
      - the new threshold only goes live if the asymmetric total cost
        is STRICTLY lower with it (equality = it stays);
      - in the "stays" case the threshold_after is reset to the old value in the report, and the
        rationale records the justification (not a silent stay).
    """
    before = cost_summary(rows_before)
    after = cost_summary(rows_after)
    improves = after["total_cost"] < before["total_cost"]
    if improves:
        decision = "valtozik"
        effective_threshold = threshold_after
        rationale = (
            f"az aszimmetrikus osszkoltseg {before['total_cost']:.0f} -> "
            f"{after['total_cost']:.0f} (szimmetrikus: {before['symmetric_cost']:.0f} -> "
            f"{after['symmetric_cost']:.0f}) a {threshold_before} -> {threshold_after} "
            "thresholddal; a valtozas indokolt"
        )
    else:
        decision = "marad"
        effective_threshold = threshold_before
        rationale = (
            f"the asymmetric total cost is not better ({before['total_cost']:.0f} -> "
            f"{after['total_cost']:.0f}); a threshold marad {threshold_before} "
            "(the reference sample: a single significant difference is not enough to move it)"
        )
    return {
        "threshold_before": threshold_before,
        "threshold_after": effective_threshold,
        "threshold_candidate": threshold_after,
        "cost_before": before["total_cost"],
        "cost_after": after["total_cost"],
        "symmetric_cost_before": before["symmetric_cost"],
        "symmetric_cost_after": after["symmetric_cost"],
        "detail_before": before,
        "detail_after": after,
        "decision": decision,
        "rationale": rationale,
    }
