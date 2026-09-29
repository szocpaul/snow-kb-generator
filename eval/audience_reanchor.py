"""eval/audience_reanchor.py — spec 013 T012: ReAnchor-kalibráció eval-only wrapperen.

A wrapper TÜKRÖZI a T007 közvetlen SDK-hívást (ugyanaz a három opció, ugyanaz a
kérdés + kritériumok, pinnelt jev-1.13.0), de NEM a production döntési út:
a production hívás közvetlen SDK marad (src/snow_kb/audience.py), ez a modul
kizárólag a kalibrációs méréshez készült.

A ReAnchor LLM-hívás nélkül hangol: az első lefuttatás cache-eli a TypeSafe
valószínűségeket, a threshold/weight-jelöltek onnantól a cache-ből dolgoznak.

Futtatás: TYPESAFE_API_KEY kell. Kimenet: artifacts/audience_reanchor_report.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

import dspy
from dspy.experimental import Choice, ReAnchor, TypeSafe

from snow_kb.audience import AUDIENCE_CRITERIA, AUDIENCE_OPTIONS, AUDIENCE_QUESTION

REPORT_PATH = Path("artifacts/audience_reanchor_report.json")
PINNED_MODEL = "jev-1.13.0"  # FR-002: pinnelt verzió, nem jev-latest


class AudienceDecisionEval(dspy.Signature):
    """Decide the primary audience of a ServiceNow KB article (eval-only mirror)."""

    story_text: str = dspy.InputField(
        desc="The full text of a completed ServiceNow Story, assembled into labeled sections."
    )
    audience: Annotated[
        Literal["helpdesk", "end-user", "developer"],
        Choice[
            ("helpdesk", AUDIENCE_CRITERIA["helpdesk"]),
            ("end-user", AUDIENCE_CRITERIA["end-user"]),
            ("developer", AUDIENCE_CRITERIA["developer"]),
        ],
    ] = dspy.OutputField(desc=AUDIENCE_QUESTION)


def accuracy_metric(example, pred) -> float:
    return 1.0 if str(pred.audience) == example.audience else 0.0


def main() -> None:
    from eval.audience_measure import load_cases

    cases = load_cases()
    trainset = [
        dspy.Example(story_text=c["story_text"], audience=c["expected"]).with_inputs("story_text")
        for c in cases
    ]

    lm = TypeSafe(model=PINNED_MODEL, cache=True)
    dspy.configure(lm=lm)

    wrapper = dspy.Predict(AudienceDecisionEval)

    # Baseline (kalibrálatlan) pontosság — az első lefuttatás tölti a cache-t.
    from dspy.teleprompt.reanchor.calibrate import run

    before = run(wrapper, trainset, accuracy_metric, num_threads=4)
    print(f"kalibrálatlan accuracy: {before:.3f} ({len(trainset)} eset)")

    optimizer = ReAnchor(accuracy_metric, num_threads=4, log_dir="artifacts/reanchor_logs")
    calibrated = optimizer.compile(wrapper, trainset=trainset)
    after = run(calibrated, trainset, accuracy_metric, num_threads=4)
    print(f"kalibrált accuracy:    {after:.3f}")

    fitted_fields = {
        name: dict(p.fields)
        for name, p in calibrated.named_parameters()
        if isinstance(p, dspy.Predict) and p.fields
    }
    report = {
        "spec": "013-audience-typed-decision / T012 ReAnchor",
        "model": PINNED_MODEL,
        "n_train": len(trainset),
        "accuracy_before": before,
        "accuracy_after": after,
        "fitted_fields": fitted_fields,
        "reanchor_report": optimizer.report,
        "note": (
            "A fitted paraméterek EXPLORATÍVAK — a confirmatory kapu a specben "
            "kijelölt 0.7-es confidence-küszöb (SC-002), a config.yaml értékét "
            "a T013 emberi kapu hagyja jóvá."
        ),
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
