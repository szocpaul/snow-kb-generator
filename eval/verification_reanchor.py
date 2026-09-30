"""eval/verification_reanchor.py — spec 014 T013: ReAnchor-kalibráció eval-only wrapperen.

A wrapper TÜKRÖZI a verification.py kalibrált rétegének közvetlen SDK-hívását
(ugyanaz a három opció, ugyanaz a kérdés + kritériumok, pinnelt jev-1.13.0),
de NEM a production döntési út: a production hívás közvetlen SDK marad
(src/snow_kb/verification.py), ez a modul kizárólag a kalibrációs méréshez
készült (a 013-as T012 minta).

Futtatás: TYPESAFE_API_KEY kell. Kimenet: artifacts/verification_reanchor_report.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

import dspy
from dspy.experimental import Choice, ReAnchor, TypeSafe

from snow_kb.verification import _REFERS_CRITERIA, _REFERS_QUESTION

REPORT_PATH = Path("artifacts/verification_reanchor_report.json")
PINNED_MODEL = "jev-1.13.0"  # FR-005: pinnelt verzió, nem lebegő alias

# A kalibrált réteg döntése → a címkézett minta elvárt válasza:
#   exists / variant-of-exists → "yes"
#   external                   → "external"
#   missing_real / fabricated / variant-of-missing → "no"


class RefersDecisionEval(dspy.Signature):
    """Decide whether a named reference refers to a real ServiceNow component (eval-only mirror)."""

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


def accuracy_metric(example, pred) -> float:
    return 1.0 if str(pred.refers) == example.refers else 0.0


def _trainset() -> list[dspy.Example]:
    from eval.verification_measure import load_cases

    by_label = {"exists": "yes", "external": "external",
                "missing_real": "no", "fabricated": "no"}
    doc_cases = load_cases()
    out = []
    import json as _json

    raw = {e["name"]: e for e in _json.loads(
        Path("data/examples/verification_labeled.json").read_text(encoding="utf-8"))["examples"]}
    for case in doc_cases:
        e = raw[case["case_id"]]
        if e["label"] == "variant":
            ref_label = raw[e["variant_of"]]["label"]
            expected = "yes" if ref_label == "exists" else "no"
        else:
            expected = by_label[e["label"]]
        out.append(
            dspy.Example(story_context=case["story_context"], name=case["case_id"],
                         refers=expected).with_inputs("story_context", "name")
        )
    return out


def main() -> None:
    trainset = _trainset()

    lm = TypeSafe(model=PINNED_MODEL, cache=True)
    dspy.configure(lm=lm)

    wrapper = dspy.Predict(RefersDecisionEval)

    # Baseline (kalibrálatlan) pontosság — az első lefuttatás tölti a cache-t.
    from dspy.teleprompt.reanchor.calibrate import run

    before = run(wrapper, trainset, accuracy_metric, num_threads=4)
    print(f"kalibrálatlan accuracy: {before:.3f} ({len(trainset)} eset)")

    optimizer = ReAnchor(accuracy_metric, num_threads=4, log_dir="artifacts/reanchor_logs_014")
    calibrated = optimizer.compile(wrapper, trainset=trainset)
    after = run(calibrated, trainset, accuracy_metric, num_threads=4)
    print(f"kalibrált accuracy:    {after:.3f}")

    fitted_fields = {
        name: dict(p.fields)
        for name, p in calibrated.named_parameters()
        if isinstance(p, dspy.Predict) and p.fields
    }
    report = {
        "spec": "014-component-instance-verification / T013 ReAnchor",
        "model": PINNED_MODEL,
        "n_train": len(trainset),
        "accuracy_before": before,
        "accuracy_after": after,
        "fitted_fields": fitted_fields,
        "reanchor_report": optimizer.report,
        "note": (
            "A fitted paraméterek EXPLORATÍVAK — a confirmatory kapu a specben "
            "kijelölt 0.7-es confidence-küszöb (SC-002), a config.yaml értékét "
            "a T014 emberi kapu hagyja jóvá."
        ),
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
