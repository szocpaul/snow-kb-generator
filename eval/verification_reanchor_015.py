"""eval/verification_reanchor_015.py — spec 015 T007: ReAnchor calibration
with the ASYMMETRIC metric, on an eval-only wrapper (the 014 pattern).

The wrapper MIRRORS the direct SDK call of the calibrated layer of verification.py
(the same three options, the same question + criteria, pinned jev-1.13.0),
but NOT the production decision path: the production call stays a direct SDK call
(src/snow_kb/verification.py), this module was created solely for the calibration
measurement (FR-006).

The metric minimizes the ASYMMETRIC cost of spec 015 (10:1, plan KD1):
a false "yes" (a missed hallucination) 10x, a false "no" (an unnecessary signal) 1x.

GEPA is FORBIDDEN in dev mode (there is no Kimi K3 reflection model) — the ReAnchor
calibration without reflection is allowed.

Run: TYPESAFE_API_KEY is required. Output: artifacts/verification_reanchor_report_015.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

import dspy
from dspy.experimental import Choice, ReAnchor, TypeSafe

from eval.verification_asymmetric import FALSE_NEG_COST, FALSE_POS_EXISTS_COST
from snow_kb.verification import _REFERS_CRITERIA, _REFERS_QUESTION

REPORT_PATH = Path("artifacts/verification_reanchor_report_015.json")
PINNED_MODEL = "jev-1.13.0"  # a pinned version, not a floating alias


class RefersDecisionEval015(dspy.Signature):
    """Decide whether a named reference refers to a real ServiceNow component (eval-only mirror, spec 015)."""

    story_context: str = dspy.InputField(
        desc="The story/article context in which the name appears."
    )
    name: str = dspy.InputField(desc="The extracted component-name candidate.")
    refers: Annotated[
        Literal["yes", "external", "no"],
        Choice[
            ("yes", _REFERS_CRITERIA["yes"]),
            ("external", _REFERS_CRITERIA["external"]),
            ("no", _REFERS_CRITERIA["no"]),
        ],
    ] = dspy.OutputField(desc=_REFERS_QUESTION)


def _expected_refers(label: str, variant_ref_label: str | None = None) -> str:
    if label == "variant":
        return "yes" if variant_ref_label == "exists" else "no"
    return {"exists": "yes", "external": "external"}.get(label, "no")


def asymmetric_metric(example, pred) -> float:
    """The negated asymmetric cost (the ReAnchor MAXIMIZES it).

    Mapped onto the gate semantics:
      pred=yes,  truth=no  → the calibrated layer says "exists" for a fabricated name
                             → a missed hallucination: 10 (FALSE_POS_EXISTS_COST)
      pred=no,  truth=yes  → an unnecessary signal: 1 (FALSE_NEG_COST)
      every other mismatch → 1 (e.g. the external↔no mix-up: from the point of view of the gate
                             behaviour it is mild)
      a match                → 0
    """
    truth = example.refers
    guess = str(pred.refers)
    if guess == truth:
        return 0.0
    if guess == "yes" and truth == "no":
        return -float(FALSE_POS_EXISTS_COST)
    return -float(FALSE_NEG_COST)


def symmetric_metric(example, pred) -> float:
    """The 014 symmetric counter value (for the comparison, spec US2 scenario 1)."""
    return 1.0 if str(pred.refers) == example.refers else 0.0


def _trainset() -> list[dspy.Example]:
    raw = json.loads(Path("data/examples/verification_labeled_015.json").read_text(
        encoding="utf-8"))["examples"]
    by_name = {e["name"]: e for e in raw}
    story_ctx = json.loads(Path("data/examples/verification_labeled_015.json").read_text(
        encoding="utf-8")).get("story_context", "")
    out = []
    for e in raw:
        ref_label = by_name[e["variant_of"]]["label"] if e["label"] == "variant" else None
        expected = _expected_refers(e["label"], ref_label)
        context = e["note"] if e.get("source") != "fixture015" else f"{story_ctx} — {e['note']}"
        out.append(
            dspy.Example(story_context=context, name=e["name"], refers=expected)
            .with_inputs("story_context", "name")
        )
    return out


def main() -> None:
    trainset = _trainset()

    lm = TypeSafe(model=PINNED_MODEL, cache=True)
    dspy.configure(lm=lm)

    wrapper = dspy.Predict(RefersDecisionEval015)

    from dspy.teleprompt.reanchor.calibrate import run

    before_asym = run(wrapper, trainset, asymmetric_metric, num_threads=4)
    before_sym = run(wrapper, trainset, symmetric_metric, num_threads=4)
    print(f"uncalibrated: asymmetric score={before_asym:.3f}, "
          f"symmetric accuracy={before_sym:.3f} ({len(trainset)} cases)")

    optimizer = ReAnchor(asymmetric_metric, num_threads=4,
                         log_dir="artifacts/reanchor_logs_015")
    calibrated = optimizer.compile(wrapper, trainset=trainset)
    after_asym = run(calibrated, trainset, asymmetric_metric, num_threads=4)
    after_sym = run(calibrated, trainset, symmetric_metric, num_threads=4)
    print(f"calibrated:     asymmetric score={after_asym:.3f}, "
          f"szimmetrikus accuracy={after_sym:.3f}")

    fitted_fields = {
        name: dict(p.fields)
        for name, p in calibrated.named_parameters()
        if isinstance(p, dspy.Predict) and p.fields
    }
    report = {
        "spec": "015-asymmetric-verification-gate / T007 ReAnchor (aszimmetrikus)",
        "model": PINNED_MODEL,
        "n_train": len(trainset),
        "asymmetric_score_before": before_asym,
        "asymmetric_score_after": after_asym,
        "symmetric_accuracy_before": before_sym,
        "symmetric_accuracy_after": after_sym,
        "fitted_fields": fitted_fields,
        "reanchor_report": optimizer.report,
        "note": (
            "The fitted parameters are EXPLORATORY — the threshold decision is in the "
            "verification_measure_015 report (sweep + regression gate), "
            "and it can only go into the config after the approval of the T009 MANUAL GATE."
        ),
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
