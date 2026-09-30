"""eval/verification_measure.py — spec 014 T013: kalibrációs mérés (capture + replay + report).

Alapelvek (a 013-as audience_measure mintájára):
  - ÉLŐ felvétel (capture) pinnelt modellel (jev-1.13.0) a címkézett mintán
    (data/examples/verification_labeled.json, ≥20 példa — 013-as tanulság);
    a spot-check cache és a JSONL recording a replay alapja.
  - A report KIZÁRÓLAG determinisztikus replay-ből származik (SC-004):
    ReplayClient (fail-closed) + cache-only SpotChecker.
  - A confirmatory kapu az előre kijelölt 0.7-es threshold; a sweep exploratív.

Használat:
    python -m eval.verification_measure capture   # élő hívások (TYPESAFE_API_KEY + SNOW kell)
    python -m eval.verification_measure report    # replay + metrikák + per-példa JSON
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from snow_kb.vendor.jev_replay import (
    load_replay_index,
    response_to_payload,
    system_one_request_hash,
)

LABELED_PATH = Path("data/examples/verification_labeled.json")
RECORDING_PATH = Path("artifacts/verification_measurement.jsonl")
SPOTCHECK_CACHE_PATH = Path("artifacts/verification_spotcheck_cache.json")
REPORT_PATH = Path("artifacts/verification_calibration_report.json")
PINNED_MODEL = "jev-1.13.0"  # FR-005: pinnelt verzió
CONFIRMATORY_THRESHOLD = 0.7  # spec SC-002: előre kijelölt kapu (a sweep exploratív)

# A ground-truth címke → elvárt gate-viselkedés leképezése.
_FLAG_LABELS = {"missing_real", "fabricated"}  # a gate-nek JELZENIE kell
# exists → nem jelzés; variant → a variant_of-tól függ; external → nem jelzés


def load_cases() -> list[dict]:
    """A címkézett minta + a levezetett elvárt döntés (flag / ok)."""
    doc = json.loads(LABELED_PATH.read_text(encoding="utf-8"))
    by_name = {e["name"]: e for e in doc["examples"]}
    cases = []
    for e in doc["examples"]:
        label = e["label"]
        if label == "variant":
            ref_label = by_name[e["variant_of"]]["label"]
            expected = "flag" if ref_label in _FLAG_LABELS or ref_label == "missing_real" else "ok"
        else:
            expected = "flag" if label in _FLAG_LABELS else "ok"
        # A jelölt kinyerhető alakja a cikkben (a 011-minta szerint)
        if e["kind"] == "quoted":
            mention = f"A '{e['name']}' komponens a megoldás része."
        else:
            mention = f"A {e['name']} komponens a megoldás része."
        cases.append({
            "case_id": e["name"],
            "label": label,
            "expected": expected,
            "article_html": f"<h2>Megoldás</h2><p>{mention}</p>",
            "story_context": e["note"],
        })
    return cases


class _RecordingClient:
    """TypeSafeClient-csomagoló: minden system_one válasz JSONL-be kerül
    (013-formátum; a request hash deduplikál)."""

    def __init__(self, inner, recording_path: Path):
        self._inner = inner
        self._path = recording_path

    def system_one(self, state=None, questions=None, model=None):
        started = __import__("time").monotonic()
        response = self._inner.system_one(state=state, questions=questions, model=model)
        latency_ms = (__import__("time").monotonic() - started) * 1000
        request_hash = system_one_request_hash(state, questions, model=model)
        if not self._path.exists() or request_hash not in load_replay_index(self._path):
            payload = response_to_payload(response)
            row = {
                "request_hash": request_hash,
                "source": "recorded",
                "model": model,
                "response": {**payload, "latency_ms": round(latency_ms, 3)},
            }
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        return response


def _build_spotchecker(live: bool):
    from snow_kb.verification import SpotChecker

    if not live:
        # Replay-mód: cache-only, session nélkül (cache-miss = unknown).
        return SpotChecker(cache_path=SPOTCHECK_CACHE_PATH, session=None)
    import requests

    session = requests.Session()
    session.auth = (os.environ["SNOW_USERNAME"], os.environ["SNOW_PASSWORD"])
    session.headers.update({"Accept": "application/json"})
    base_url = f"https://{os.environ['SNOW_INSTANCE']}/api/now/table"
    return SpotChecker(cache_path=SPOTCHECK_CACHE_PATH, session=session,
                       base_url=base_url)


def _run_cases(client, live: bool) -> list[dict]:
    from snow_kb.verification import verify_component_names

    checker = _build_spotchecker(live=live)
    out = []
    for case in load_cases():
        result = verify_component_names(
            case["article_html"],
            "",
            spot_checker=checker,
            story_context=case["story_context"],
            decision_client=client,
            decision_model=PINNED_MODEL,
            confidence_threshold=CONFIRMATORY_THRESHOLD,
        )
        if result.skipped:
            raise RuntimeError(f"fail-open a mérésben ({case['case_id']}) — ez hiba")
        verdict = result.verdicts[0]
        predicted = "flag" if verdict.status == "not_exists" else "ok"
        # A kalibrált réteg confidence-a (determinisztikusnál 1.0)
        out.append({
            "case_id": case["case_id"],
            "label": case["label"],
            "expected": case["expected"],
            "predicted": predicted,
            "status": verdict.status,
            "layer": verdict.layer,
            "confidence": verdict.confidence,
            "evidence": verdict.evidence,
        })
    return out


def cmd_capture() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY kell a capture-höz")
    from typesafe_sdk import TypeSafeClient

    client = _RecordingClient(TypeSafeClient(), RECORDING_PATH)
    rows = _run_cases(client, live=True)
    ok = sum(1 for r in rows if r["predicted"] == r["expected"])
    print(f"{len(rows)} eset élő felvétele kész; egyezés: {ok}/{len(rows)}")

    # SC-001 előkészítés: a gold cikkek jelöltjei is a cache-be/recordingba
    # kerülnek, hogy a report replay-módban értékelhesse őket.
    _capture_gold_candidates(client)
    print(f"Recording: {RECORDING_PATH}; spot-check cache: {SPOTCHECK_CACHE_PATH}")


def _capture_gold_candidates(client) -> None:
    """A 9 gold cikk komponensnév-jelöltjeinek élő ellenőrzése (SC-001 adatforrás)."""
    from eval.dataset import load_gold_dataset
    from snow_kb.verification import verify_component_names

    checker = _build_spotchecker(live=True)
    trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
    for idx, ex in enumerate(trainset + valset, 1):
        result = verify_component_names(
            ex.html,
            getattr(ex, "update_set_payloads", "") or "",
            spot_checker=checker,
            story_context=ex.story_text,
            decision_client=client,
            decision_model=PINNED_MODEL,
            confidence_threshold=CONFIRMATORY_THRESHOLD,
        )
        flagged = result.not_existing_names
        print(f"gold-{idx}: {len(result.verdicts)} jelölt, {len(flagged)} jelzett"
              + (f" → {flagged}" if flagged else ""))


def _replay_rows() -> list[dict]:
    from snow_kb.audience import replay_client_from_recording

    client = replay_client_from_recording(RECORDING_PATH)
    return _run_cases(client, live=False)


def cmd_report() -> None:
    """Determinisztikus report a replay-ből (SC-002 metrikák, SC-001 adat)."""
    from eval.jev_metrics import Decision, evaluate_decisions, evaluate_threshold_sweep

    rows = _replay_rows()

    decisions = []
    for r in rows:
        conf = r["confidence"]
        decisions.append(Decision(
            case_id=r["case_id"],
            field="component_verification",
            kind="choice",
            predicted=r["predicted"],
            expected=r["expected"],
            confidence=conf,
            probabilities={r["predicted"]: conf,
                           ("ok" if r["predicted"] == "flag" else "flag"): 1.0 - conf},
        ))

    metrics = evaluate_decisions(decisions, threshold=CONFIRMATORY_THRESHOLD)
    sweep = evaluate_threshold_sweep(
        decisions, thresholds=[round(t / 20, 2) for t in range(0, 21)]
    )

    per_case = rows
    incorrect = [r for r in rows if r["predicted"] != r["expected"]]

    report = {
        "spec": "014-component-instance-verification / T013",
        "model": PINNED_MODEL,
        "n_cases": len(rows),
        "confirmatory_threshold": CONFIRMATORY_THRESHOLD,
        "sc001": _sc001_block(),
        "sc002": {
            "selective_risk": metrics.selective_risk,
            "coverage": metrics.coverage,
            "ece": metrics.ece,
            "brier": metrics.brier,
            "gates": {
                "selective_risk_le_0.15": metrics.selective_risk <= 0.15,
                "coverage_ge_0.7": metrics.coverage >= 0.7,
            },
        },
        "threshold_sweep_explorative": [
            {"threshold": p.threshold, "coverage": p.coverage,
             "selective_risk": p.selective_risk, "accuracy": p.accuracy}
            for p in sweep
        ],
        "incorrect_cases": incorrect,
        "per_case": per_case,
        "note": (
            "A threshold-sweep EXPLORATÍV — a confirmatory kapu a specben "
            "kijelölt 0.7 (SC-002). A legjobb sweep-sor NEM confirmatory eredmény."
        ),
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Report: {REPORT_PATH}")
    print(f"SC-002: selective_risk={metrics.selective_risk:.3f} coverage={metrics.coverage:.3f} "
          f"ece={metrics.ece:.3f}")


def _sc001_block() -> dict:
    """SC-001: a gold cikkeken nincs false 'nem létezik' jelölés (replay-mód)."""
    import dspy

    from eval import metric as metric_mod
    from eval.dataset import load_gold_dataset

    from snow_kb.audience import replay_client_from_recording

    checker = _build_spotchecker(live=False)
    metric_mod.configure_instance_axis(
        checker,
        decision_client=replay_client_from_recording(RECORDING_PATH),
        decision_model=PINNED_MODEL,
        confidence_threshold=CONFIRMATORY_THRESHOLD,
    )
    try:
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        false_positives = []
        for idx, ex in enumerate(trainset + valset, 1):
            gold = dspy.Example(
                story_text=ex.story_text, html=ex.html,
                update_set_payloads=getattr(ex, "update_set_payloads", "") or "",
            ).with_inputs("story_text")
            pred = dspy.Prediction(html=ex.html)
            result = metric_mod.rich_metric(gold, pred)
            if result.axes.get("instance", 1.0) != 1.0:
                false_positives.append({"example": f"gold-{idx}",
                                        "feedback": result.feedback[:400]})
        return {
            "total_gold": len(trainset) + len(valset),
            "false_positives": false_positives,
            "zero_false_positive": not false_positives,
        }
    finally:
        metric_mod.configure_instance_axis(None)


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] not in ("capture", "report"):
        raise SystemExit("Használat: python -m eval.verification_measure [capture|report]")
    if argv[0] == "capture":
        cmd_capture()
    else:
        cmd_report()


if __name__ == "__main__":
    main()
