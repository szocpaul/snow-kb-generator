"""eval/verification_asymmetric.py — spec 015: aszimmetrikus költségű metrika.

A 014-es kalibrációs metrika SZIMMETRIKUS volt (mindkét hibafajta ugyanannyiba
"került"). A valóságban (spec Background):
  - a téves "létező" (a gate átengedte a hallucinált nevet) sokkal drágább —
    tévútra viszi a cikket olvasó mérnököt;
  - a téves "nem létező" (felesleges jelzés) legfeljebb zaj.

Költség-arány (plan Key Decision 1): 10:1. Az érzékenység-analízis (5:1, 20:1)
a kalibrációs riport része; ha a threshold az arányra érzéketlen, az
egyszerűbb 10:1 marad.

A "predicted"/"expected" értékek a 014-es mérés alakjai: "ok" (a gate szerint
létezik / nem jelz) és "flag" (a gate jelz: nem létező név).
"""

from __future__ import annotations

FALSE_POS_EXISTS_COST = 10  # téves "létező" (átsikló hallucináció)
FALSE_NEG_COST = 1          # téves "nem létező" (felesleges jelzés)


def case_cost(predicted: str, expected: str,
              fp_cost: float = FALSE_POS_EXISTS_COST,
              fn_cost: float = FALSE_NEG_COST) -> float:
    """Egy eset aszimmetrikus költsége.

    predicted="ok", expected="flag"  → téves "létező" (fp_cost)
    predicted="flag", expected="ok"  → téves "nem létező" (fn_cost)
    egyezés                          → 0
    """
    if predicted == expected:
        return 0.0
    return fp_cost if predicted == "ok" else fn_cost


def cost_summary(rows: list[dict],
                 fp_cost: float = FALSE_POS_EXISTS_COST,
                 fn_cost: float = FALSE_NEG_COST) -> dict:
    """Összesített költség egy predicted/expected sorlistán."""
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
    """Kalibrációs riport (spec US2 Acceptance 1-2).

    A döntés szabálya (a referencia-minta: "nem veri → marad"):
      - az új threshold CSAK akkor lép életbe, ha az aszimmetrikus összköltség
        SZIGORÚAN kisebb vele (egyenlőség = marad);
      - "marad" esetén a threshold_after a riportban visszaáll a régire, és a
        rationale rögzíti az indoklást (nem csendes maradás).
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
            f"az aszimmetrikus osszkoltseg nem jobb ({before['total_cost']:.0f} -> "
            f"{after['total_cost']:.0f}); a threshold marad {threshold_before} "
            "(a referencia-minta: egy jelolesbeli kulonbseg nem eleg a mozgatashoz)"
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
