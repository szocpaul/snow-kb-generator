"""eval/verification_measure_015.py — spec 015 T007/T008: the calibration measurement with an asymmetric cost
on the PDI-native merged sample (capture + replay + report).

Based on the pattern of the 014 verification_measure, with three differences:
  1. the sample is the T005 MERGED set (data/examples/verification_labeled_015.json,
     ≥30 examples: the 24 old ones + the fixture-derived ones);
  2. it stores the RAW (choice, confidence) pair of the calibrated layer for every case —
     so the threshold sweep can be computed from a PURE replay, without a new live call;
  3. the report shows the ASYMMETRIC cost (10:1, plan KD1) and the symmetric
     counter value as well, with the justification of the threshold decision (spec US2).

The production call still is a direct SDK (src/snow_kb/verification.py) —
this module is only for the measurement. The confirmatory gate is the 0.7 threshold; the sweep
is EXPLORATORY (the best sweep row is NOT a confirmatory result).

Usage:
    python -m eval.verification_measure_015 capture   # live calls (TYPESAFE_API_KEY + SNOW)
    python -m eval.verification_measure_015 report    # replay + metrics + report
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.verification_asymmetric import build_calibration_report, cost_summary
from eval.verification_measure import _RecordingClient  # 014 reuse
from snow_kb.vendor.jev_replay import (
    load_replay_index,
    response_to_payload,
    system_one_request_hash,
)

LABELED_PATH = Path("data/examples/verification_labeled_015.json")
RECORDING_PATH = Path("artifacts/verification_measurement_015.jsonl")
SPOTCHECK_CACHE_PATH = Path("artifacts/verification_spotcheck_cache.json")
REPORT_PATH = Path("artifacts/verification_calibration_report_015.json")
BASELINE_PATH = Path("artifacts/verification_asymmetric_baseline.json")  # T004
PINNED_MODEL = "jev-1.13.0"  # FR-005 pattern: a pinned version
CONFIRMATORY_THRESHOLD = 0.7  # the current config value (the sweep is exploratory)

_FLAG_LABELS = {"missing_real", "fabricated"}  # the gate must REPORT it

SWEEP_THRESHOLDS = [round(t / 20, 2) for t in range(0, 21)]


def load_cases() -> list[dict]:
    """The merged labelled sample + the derived expected decision (flag / ok)."""
    doc = json.loads(LABELED_PATH.read_text(encoding="utf-8"))
    by_name = {e["name"]: e for e in doc["examples"]}
    story_ctx = doc.get("story_context", "")
    cases = []
    for e in doc["examples"]:
        label = e["label"]
        if label == "variant":
            ref_label = by_name[e["variant_of"]]["label"]
            expected = "flag" if ref_label in _FLAG_LABELS else "ok"
        else:
            expected = "flag" if label in _FLAG_LABELS else "ok"
        if e["kind"] == "quoted":
            mention = f"The '{e['name']}' component is part of the solution."
        else:
            mention = f"The {e['name']} component is part of the solution."
        context = e["note"] if e.get("source") != "fixture015" else f"{story_ctx} — {e['note']}"
        cases.append({
            "case_id": e["name"],
            "label": label,
            "source": e.get("source", "spec014"),
            "expected": expected,
            "article_html": f"<h2>Solution</h2><p>{mention}</p>",
            "story_context": context,
        })
    return cases


# ---------------------------------------------------------------------------
# The RAW probe of the calibrated layer (the data source of the sweep)
# ---------------------------------------------------------------------------

def _calibrated_probe(name: str, story_context: str, client) -> dict:
    """It asks for the (choice, confidence) pair with the SAME state/questions setup as the
    production _calibrated_decision — the threshold is NOT applied here.

    The request hash is the same as in the production/measurement call → the recording deduplicates,
    a replay pedig fail-closed (byte-identikus riport, SC-005).
    """
    from typesafe_sdk import Choice

    from snow_kb.verification import _REFERS_CRITERIA, _REFERS_QUESTION

    state = (
        f"Article excerpt context (the environment of the source story and/or of the article):\n"
        f"{story_context[:4000]}\n\n"
        f"Examined name: '{name}'"
    )
    questions = {"refers": Choice(instructions=_REFERS_QUESTION,
                                  criteria=dict(_REFERS_CRITERIA))}
    try:
        response = client.system_one(state=state, questions=questions, model=PINNED_MODEL)
        answer = response.answers["refers"]
        return {"choice": getattr(answer, "choice", None),
                "confidence": float(getattr(answer, "confidence", 0.0) or 0.0)}
    except Exception as exc:  # noqa: BLE001
        return {"choice": None, "confidence": 0.0,
                "probe_error": f"{type(exc).__name__}: {exc}"}


def calibrated_predicted(choice: str | None, confidence: float, threshold: float) -> str:
    """The mapping of the calibrated (choice, confidence) → gate decision on a threshold.

    The logic of the production _calibrated_decision (verification.py):
      yes + confident      → exists (ok)
      external + confident → not_applicable (ok)
      otherwise             → not_exists (flag)
    The threshold operator is '<' (spec Edge Cases; the 013 pattern).
    """
    from snow_kb.verification import _REFERS_EPS

    confident = not (confidence < threshold + _REFERS_EPS)
    if choice == "yes" and confident:
        return "ok"
    if choice == "external" and confident:
        return "ok"
    return "flag"


# ---------------------------------------------------------------------------
# Capture / replay
# ---------------------------------------------------------------------------

def _build_spotchecker(live: bool):
    from snow_kb.verification import SpotChecker

    if not live:
        return SpotChecker(cache_path=SPOTCHECK_CACHE_PATH, session=None)
    import os

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
            raise RuntimeError(f"fail-open in the measurement ({case['case_id']}) — this is an error")
        if not result.verdicts:
            raise RuntimeError(
                f"the candidate cannot be extracted from the article ({case['case_id']}) — "
                "the html of the sample does not match the 011 pattern"
            )
        verdict = result.verdicts[0]
        predicted = "flag" if verdict.status == "not_exists" else "ok"
        # The RAW (choice, confidence) pair of the calibrated layer for the sweep
        probe = _calibrated_probe(case["case_id"], case["story_context"], client)
        out.append({
            "case_id": case["case_id"],
            "label": case["label"],
            "source": case["source"],
            "expected": case["expected"],
            "predicted": predicted,
            "status": verdict.status,
            "layer": verdict.layer,
            "confidence": verdict.confidence,
            "evidence": verdict.evidence,
            "calibrated_choice": probe["choice"],
            "calibrated_confidence": probe["confidence"],
        })
    return out


def cmd_capture() -> None:
    import os

    from dotenv import load_dotenv

    load_dotenv()
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY is required for the capture")
    from typesafe_sdk import TypeSafeClient

    client = _RecordingClient(TypeSafeClient(), RECORDING_PATH)
    rows = _run_cases(client, live=True)
    ok = sum(1 for r in rows if r["predicted"] == r["expected"])
    print(f"live capture of {len(rows)} cases done; matches: {ok}/{len(rows)}")
    print(f"Recording: {RECORDING_PATH}; spot-check cache: {SPOTCHECK_CACHE_PATH}")


def _replay_rows() -> list[dict]:
    from snow_kb.audience import replay_client_from_recording

    client = replay_client_from_recording(RECORDING_PATH)
    return _run_cases(client, live=False)


# ---------------------------------------------------------------------------
# Report (tiszta replay — determinisztikus, SC-005)
# ---------------------------------------------------------------------------

def _rows_at_threshold(rows: list[dict], threshold: float) -> list[dict]:
    """The per case predicted on an arbitrary threshold — from a PURE replay.

    The deterministic layers (update_set/spotcheck) are threshold independent;
    the calibrated layer can be computed from the stored (choice, confidence) pair.
    """
    out = []
    for r in rows:
        if r["layer"] == "calibrated":
            predicted = calibrated_predicted(r["calibrated_choice"],
                                             r["calibrated_confidence"], threshold)
        else:
            predicted = r["predicted"]
        out.append({"predicted": predicted, "expected": r["expected"]})
    return out


def _sweep(rows: list[dict]) -> list[dict]:
    """An EXPLORATORY threshold sweep: the asymmetric + the symmetric cost."""
    points = []
    for t in SWEEP_THRESHOLDS:
        summary = cost_summary(_rows_at_threshold(rows, t))
        points.append({"threshold": t,
                       "asymmetric_cost": summary["total_cost"],
                       "symmetric_cost": summary["symmetric_cost"],
                       "false_pos_exists": summary["false_pos_exists"],
                       "false_neg": summary["false_neg"]})
    return points


def _best_threshold(sweep: list[dict]) -> float:
    """The threshold with the lowest asymmetric cost; in a tie the HIGHER
        (the safe direction: fewer missed hallucinations). EXPLORATORY."""
    best_cost = min(p["asymmetric_cost"] for p in sweep)
    candidates = [p["threshold"] for p in sweep if p["asymmetric_cost"] == best_cost]
    return max(candidates)


def _regression_block(rows: list[dict], threshold: float) -> dict:
    """SC-003 (T008): the candidate (or remaining) threshold on the EXISTING 24-example
        sample, compared with the T004 baseline. A degradation → the config is NOT modified."""
    old_rows = [r for r in rows if r["source"] == "spec014"]
    summary = cost_summary(_rows_at_threshold(old_rows, threshold))
    baseline_cost = None
    if BASELINE_PATH.exists():
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        baseline_cost = baseline["asymmetric"]["total_cost"]
    worse = baseline_cost is not None and summary["total_cost"] > baseline_cost
    return {
        "threshold": threshold,
        "n_old_cases": len(old_rows),
        "asymmetric_cost": summary["total_cost"],
        "symmetric_cost": summary["symmetric_cost"],
        "baseline_threshold": 0.7,
        "baseline_asymmetric_cost": baseline_cost,
        "worse_than_baseline": worse,
    }


def cmd_report() -> None:
    rows = _replay_rows()
    sweep = _sweep(rows)
    candidate = _best_threshold(sweep)

    calib = build_calibration_report(
        threshold_before=CONFIRMATORY_THRESHOLD,
        threshold_after=candidate,
        rows_before=_rows_at_threshold(rows, CONFIRMATORY_THRESHOLD),
        rows_after=_rows_at_threshold(rows, candidate),
    )

    # The KD1 sensitivity analysis: the best sweep threshold at other weight ratios
    # (5:1, 20:1) — if it is insensitive, the simplest 10:1 stays; if it is sensitive,
        # the T009 human gate weighs the ratio.
    sensitivity = {}
    for ratio in (5, 10, 20):
        costs = [(p["threshold"], p["false_pos_exists"] * ratio + p["false_neg"])
                 for p in sweep]
        best_cost = min(c for _, c in costs)
        best_ts = [t for t, c in costs if c == best_cost]
        sensitivity[f"{ratio}:1"] = {"best_thresholds": best_ts,
                                     "best_cost": best_cost}
    sensitive = len({v["best_thresholds"][-1] for v in sensitivity.values()}) > 1

    regression = _regression_block(rows, calib["threshold_after"])
    if regression["worse_than_baseline"] and calib["decision"] == "valtozik":
        # SC-003: a degradation on the old sample → the config is NOT modified, the report is RED
        calib["decision"] = "marad"
        calib["threshold_after"] = CONFIRMATORY_THRESHOLD
        calib["rationale"] += (
            "; BUT the SC-003 regression gate shows a DEGRADATION on the existing 24-example "
            "sample → the threshold is NOT put into effect"
        )

    report = {
        "spec": "015-asymmetric-verification-gate / T007-T008",
        "model": PINNED_MODEL,
        "n_cases": len(rows),
        "confirmatory_threshold": CONFIRMATORY_THRESHOLD,
        "calibration": calib,
        "regression_sc003": regression,
        "sensitivity_ratio_analysis": sensitivity,
        "ratio_sensitive": sensitive,
        "threshold_sweep_explorative": sweep,
        "incorrect_cases": [r for r in rows if r["predicted"] != r["expected"]],
        "per_case": rows,
        "note": (
            "The threshold sweep is EXPLORATORY — the best sweep row is NOT a confirmatory "
            "result. The threshold can only go into the config.yaml after the approval of the "
            "T009 MANUAL GATE. The fail-open and the flag-only base behaviour are a "
            "manually set safety floor, the calibration does NOT move them."
        ),
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Report: {REPORT_PATH}")
    print(f"Calibration: {calib['decision']} — {calib['rationale']}")
    print(f"SC-003 regression: {'DEGRADATION (RED)' if regression['worse_than_baseline'] else 'no degradation'} "
          f"(cost {regression['baseline_asymmetric_cost']} → {regression['asymmetric_cost']})")


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] not in ("capture", "report"):
        raise SystemExit("Usage: python -m eval.verification_measure_015 [capture|report]")
    if not LABELED_PATH.exists():
        raise SystemExit(f"The merged sample is missing: {LABELED_PATH} — "
                         "futtasd: python -m eval.verification_labeled_015 build "
                         "(after the T003 MANUAL GATE)")
    if argv[0] == "capture":
        cmd_capture()
    else:
        cmd_report()


if __name__ == "__main__":
    main()
