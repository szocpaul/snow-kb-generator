"""eval/audience_measure.py — spec 013 T012: kalibrációs mérés (capture + replay + report).

Alapelvek:
  - ÉLŐ felvétel (capture) pinnelt modellel (jev-1.13.0) a gold (9) + mock (3) mintán,
    JSONL recordingba (artifacts/audience_measurement.jsonl).
  - A mérés/report KIZÁRÓLAG determinisztikus replay-ből származik (SC-002, SC-004):
    a report parancs kétszer futtatva byte-identikus kimenetet ad.
  - A confirmatory kapu az előre kijelölt 0.7-es threshold; a sweep exploratív.

Használat:
    python -m eval.audience_measure capture     # élő hívások (TYPESAFE_API_KEY kell)
    python -m eval.audience_measure report      # replay + metrikák + per-példa JSON
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from snow_kb.audience import decide_audience, replay_client_from_recording
from snow_kb.config import load_settings

GOLD_PATH = Path("data/examples/gold_dataset.md")
LABELS_PATH = Path("data/examples/gold_audience_labels.json")
MOCKS_PATH = Path("data/examples/audience_mock_stories.json")
RECORDING_PATH = Path("artifacts/audience_measurement.jsonl")
CASES_PATH = Path("artifacts/audience_measurement_cases.json")
DECISIONS_PATH = Path("artifacts/audience_decisions_new.json")
REPORT_PATH = Path("artifacts/audience_calibration_report.json")
BASELINE_PATH = Path("artifacts/audience_baseline.json")

CONFIRMATORY_THRESHOLD = 0.7  # spec SC-002: előre kijelölt kapu (a sweep exploratív)


def load_cases() -> list[dict]:
    """A mérési minta: 9 gold (story_text + címke) + 3 mock."""
    from eval.dataset import load_gold_dataset

    trainset, valset = load_gold_dataset(GOLD_PATH)
    examples = trainset + valset  # a loader sorrendje = Példa 1..9
    labels = json.loads(LABELS_PATH.read_text(encoding="utf-8"))["labels"]

    cases = []
    for idx, ex in enumerate(examples, 1):
        m = re.search(r'"number":\s*"(STRY\d+)"', ex.story_text)
        if not m:
            raise ValueError(f"A {idx}. gold példából nem olvasható a Story-szám.")
        number = m.group(1)
        cases.append({
            "case_id": number,
            "source": f"gold_példa_{idx}",
            "story_text": ex.story_text,
            "expected": labels[number]["label"],
        })
    for story in json.loads(MOCKS_PATH.read_text(encoding="utf-8"))["stories"]:
        cases.append({
            "case_id": story["id"],
            "source": "mock",
            "story_text": story["story_text"],
            "expected": story["expected"],
        })
    return cases


def _measurement_settings():
    settings = load_settings()
    assert settings.audience_decision.enabled, "config.yaml: audience_decision.enabled kell"
    assert settings.audience_decision.model == "jev-1.13.0", "pinnelt modell kell a méréshez"
    object.__setattr__(settings.audience_decision, "recording_path", str(RECORDING_PATH))
    return settings


def cmd_capture() -> None:
    """Élő felvétel pinnelt modellel; a recording deduplikál (request hash)."""
    settings = _measurement_settings()
    cases = load_cases()
    print(f"{len(cases)} eset élő felvétele (modell: {settings.audience_decision.model})")
    for i, case in enumerate(cases, 1):
        decision = decide_audience(case["story_text"], settings)
        if decision is None:
            raise RuntimeError(f"fail-open a capture közben ({case['case_id']}) — élő mérésnél ez hiba")
        print(f"[{i}/{len(cases)}] {case['case_id']}: {decision.choice} conf={decision.confidence:.2f}")
    CASES_PATH.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Recording: {RECORDING_PATH}; esetek: {CASES_PATH}")


def _replay_decisions() -> list[dict]:
    """Fail-closed replay: a döntések kizárólag a rögzített válaszokból."""
    settings = _measurement_settings()
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    client = replay_client_from_recording(RECORDING_PATH)
    out = []
    for case in cases:
        decision = decide_audience(case["story_text"], settings, client=client)
        if decision is None:
            raise RuntimeError(f"replay fail-open ({case['case_id']}) — hiányzó recording?")
        out.append({
            "case_id": case["case_id"],
            "source": case["source"],
            "expected": case["expected"],
            "choice": decision.choice,
            "confidence": decision.confidence,
            "probabilities": decision.probabilities,
            "model": decision.model,
        })
    return out


def cmd_report() -> None:
    """Determinisztikus report a replay-ből (SC-001 adat + SC-002 metrikák)."""
    from eval.jev_metrics import Decision, evaluate_decisions, evaluate_threshold_sweep

    decisions = _replay_decisions()

    # --- SC-001: baseline (generatív út) vs új döntés a gold példákon ---
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["results"]
    baseline_by_index = {r["example_index"]: r["audience"] for r in baseline}
    gold_rows = []
    for d in decisions:
        if not d["source"].startswith("gold_példa_"):
            continue
        idx = int(d["source"].rsplit("_", 1)[1])
        gold_rows.append({
            "case_id": d["case_id"],
            "expected": d["expected"],
            "baseline_audience": baseline_by_index[idx],
            "baseline_match": baseline_by_index[idx] == d["expected"],
            "new_audience": d["choice"],
            "new_match": d["choice"] == d["expected"],
            "confidence": d["confidence"],
        })
    baseline_matches = sum(r["baseline_match"] for r in gold_rows)
    new_matches = sum(r["new_match"] for r in gold_rows)

    # --- SC-002: jev-dspy-lab metrikák a confirmatory 0.7-es kapunál ---
    lab_decisions = [
        Decision(
            case_id=d["case_id"],
            field="audience",
            kind="choice",
            predicted=d["choice"],
            expected=d["expected"],
            probabilities=d["probabilities"],
        )
        for d in decisions
    ]
    confirmatory = evaluate_decisions(lab_decisions, threshold=CONFIRMATORY_THRESHOLD)
    sweep = evaluate_threshold_sweep(lab_decisions)  # EXPLORATÍV — nem confirmatory

    report = {
        "spec": "013-audience-typed-decision / T012",
        "model": decisions[0]["model"] if decisions else "",
        "n_cases": len(decisions),
        "confirmatory_threshold": CONFIRMATORY_THRESHOLD,
        "sc001": {
            "baseline_matches": baseline_matches,
            "new_matches": new_matches,
            "total_gold": len(gold_rows),
            "new_not_worse": new_matches >= baseline_matches,
            "per_example": gold_rows,
        },
        "sc002": {
            "selective_risk": confirmatory.selective_risk,
            "coverage": confirmatory.coverage,
            "ece": confirmatory.ece,
            "brier": confirmatory.brier,
            "accuracy": confirmatory.accuracy,
            "answered": confirmatory.answered,
            "abstained": confirmatory.abstained,
            "gates": {
                "selective_risk_le_0.15": confirmatory.selective_risk <= 0.15,
                "coverage_ge_0.7": confirmatory.coverage >= 0.7,
                "ece_le_0.10": confirmatory.ece <= 0.10,
            },
        },
        "threshold_sweep_EXPLORATIVE": [
            {
                "threshold": p.threshold,
                "coverage": p.coverage,
                "selective_risk": p.selective_risk,
                "answered": p.answered,
                "abstained": p.abstained,
            }
            for p in sweep
        ],
    }
    DECISIONS_PATH.write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"SC-001: baseline {baseline_matches}/{len(gold_rows)} vs új {new_matches}/{len(gold_rows)}")
    print(f"SC-002 @0.7: selective_risk={confirmatory.selective_risk:.3f} coverage={confirmatory.coverage:.3f} ece={confirmatory.ece:.3f}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("capture", "report"):
        print(__doc__)
        sys.exit(2)
    if sys.argv[1] == "capture":
        cmd_capture()
    else:
        cmd_report()
