"""eval/verification_reanchor_015.py — spec 015 T007: ReAnchor-kalibráció
ASZIMMETRIKUS metrikával, eval-only wrapperen (014-es minta).

A wrapper TÜKRÖZI a verification.py kalibrált rétegének közvetlen SDK-hívását
(ugyanaz a három opció, ugyanaz a kérdés + kritériumok, pinnelt jev-1.13.0),
de NEM a production döntési út: a production hívás közvetlen SDK marad
(src/snow_kb/verification.py), ez a modul kizárólag a kalibrációs méréshez
készült (FR-006).

A metrika a spec 015 ASZIMMETRIKUS költségét minimalizálja (10:1, plan KD1):
a téves "yes" (átsikló hallucináció) 10x, a téves "no" (felesleges jelzés) 1x.

GEPA TILOS dev-módban (nincs Kimi K3 reflection-modell) — a ReAnchor
reflection-mentes kalibráció, ez megengedett.

Futtatás: TYPESAFE_API_KEY kell. Kimenet: artifacts/verification_reanchor_report_015.json
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
PINNED_MODEL = "jev-1.13.0"  # pinnelt verzió, nem lebegő alias


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
    """Negált aszimmetrikus költség (a ReAnchor MAXIMALIZÁL).

    A gate-szemantikára vetítve:
      pred=yes,  truth=no  → a kalibrált réteg "létezőt" mond a fabrikált névre
                             → átsikló hallucináció: 10 (FALSE_POS_EXISTS_COST)
      pred=no,  truth=yes  → felesleges jelzés: 1 (FALSE_NEG_COST)
      minden más eltérés   → 1 (pl. external↔no zavar: a gate viselkedése
                             szempontjából enyhe)
      egyezés              → 0
    """
    truth = example.refers
    guess = str(pred.refers)
    if guess == truth:
        return 0.0
    if guess == "yes" and truth == "no":
        return -float(FALSE_POS_EXISTS_COST)
    return -float(FALSE_NEG_COST)


def symmetric_metric(example, pred) -> float:
    """A 014-es szimmetrikus ellenérték (összevetéshez, spec US2 scenario 1)."""
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
    print(f"kalibrálatlan: aszimmetrikus score={before_asym:.3f}, "
          f"szimmetrikus accuracy={before_sym:.3f} ({len(trainset)} eset)")

    optimizer = ReAnchor(asymmetric_metric, num_threads=4,
                         log_dir="artifacts/reanchor_logs_015")
    calibrated = optimizer.compile(wrapper, trainset=trainset)
    after_asym = run(calibrated, trainset, asymmetric_metric, num_threads=4)
    after_sym = run(calibrated, trainset, symmetric_metric, num_threads=4)
    print(f"kalibrált:     aszimmetrikus score={after_asym:.3f}, "
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
            "A fitted paraméterek EXPLORATÍVAK — a threshold-döntés a "
            "verification_measure_015 riportjában (sweep + regresszió-gate), "
            "és CSAK a T009 MANUÁLIS KAPU jóváhagyása után kerülhet a configba."
        ),
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
