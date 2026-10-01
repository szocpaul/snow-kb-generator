"""eval/verification_measure_015.py — spec 015 T007/T008: aszimmetrikus költségű
kalibrációs mérés a PDI-natív egyesített mintán (capture + replay + report).

A 014-es verification_measure mintájára, három különbséggel:
  1. a minta a T005-ös EGYESÍTETT halmaz (data/examples/verification_labeled_015.json,
     ≥30 példa: 24 régi + fixture-származtatott);
  2. minden esethez tárolja a kalibrált réteg NYERS (choice, confidence) párját —
     így a threshold-sweep TISZTA replay-ből, új élő hívás nélkül számolható;
  3. a riport ASZIMMETRIKUS költséget (10:1, plan KD1) és szimmetrikus
     ellenértéket is mutat, a threshold-döntés indoklásával (spec US2).

A production hívás továbbra is közvetlen SDK (src/snow_kb/verification.py) —
ez a modul kizárólag mérés. A confirmatory kapu a 0.7-es threshold; a sweep
EXPLORATÍV (a legjobb sweep-sor NEM confirmatory eredmény).

Használat:
    python -m eval.verification_measure_015 capture   # élő hívások (TYPESAFE_API_KEY + SNOW)
    python -m eval.verification_measure_015 report    # replay + metrikák + riport
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.verification_asymmetric import build_calibration_report, cost_summary
from eval.verification_measure import _RecordingClient  # 014-es újrahasznosítás
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
PINNED_MODEL = "jev-1.13.0"  # FR-005-minta: pinnelt verzió
CONFIRMATORY_THRESHOLD = 0.7  # a jelenlegi config-érték (a sweep exploratív)

_FLAG_LABELS = {"missing_real", "fabricated"}  # a gate-nek JELZENIE kell

SWEEP_THRESHOLDS = [round(t / 20, 2) for t in range(0, 21)]


def load_cases() -> list[dict]:
    """Az egyesített címkézett minta + a levezetett elvárt döntés (flag / ok)."""
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
            mention = f"A '{e['name']}' komponens a megoldás része."
        else:
            mention = f"A {e['name']} komponens a megoldás része."
        context = e["note"] if e.get("source") != "fixture015" else f"{story_ctx} — {e['note']}"
        cases.append({
            "case_id": e["name"],
            "label": label,
            "source": e.get("source", "spec014"),
            "expected": expected,
            "article_html": f"<h2>Megoldás</h2><p>{mention}</p>",
            "story_context": context,
        })
    return cases


# ---------------------------------------------------------------------------
# Kalibrált réteg NYERS probéja (a sweep adatforrása)
# ---------------------------------------------------------------------------

def _calibrated_probe(name: str, story_context: str, client) -> dict:
    """A production _calibrated_decision-szel AZONOS state/questions felépítéssel
    kérdezi le a (choice, confidence) párt — a threshold NEM itt alkalmazódik.

    A request hash azonos a production/mérési híváséval → a recording deduplikál,
    a replay pedig fail-closed (byte-identikus riport, SC-005).
    """
    from typesafe_sdk import Choice

    from snow_kb.verification import _REFERS_CRITERIA, _REFERS_QUESTION

    state = (
        f"Cikkrészlet-kontextus (a forrás-story és/vagy a cikk környezete):\n"
        f"{story_context[:4000]}\n\n"
        f"Vizsgált megnevezés: '{name}'"
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
    """A kalibrált (choice, confidence) → gate-döntés leképezése egy thresholdon.

    A production _calibrated_decision logikája (verification.py):
      yes + confident      → exists (ok)
      external + confident → not_applicable (ok)
      egyéb                → not_exists (flag)
    A küszöb-operátor '<' (spec Edge Cases; 013-as minta).
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
            raise RuntimeError(f"fail-open a mérésben ({case['case_id']}) — ez hiba")
        if not result.verdicts:
            raise RuntimeError(
                f"a jelölt nem nyerhető ki a cikkből ({case['case_id']}) — "
                "a minta html-je nem felel meg a 011-mintának"
            )
        verdict = result.verdicts[0]
        predicted = "flag" if verdict.status == "not_exists" else "ok"
        # A kalibrált réteg NYERS (choice, confidence) párja a sweep-hez
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
        raise SystemExit("TYPESAFE_API_KEY kell a capture-höz")
    from typesafe_sdk import TypeSafeClient

    client = _RecordingClient(TypeSafeClient(), RECORDING_PATH)
    rows = _run_cases(client, live=True)
    ok = sum(1 for r in rows if r["predicted"] == r["expected"])
    print(f"{len(rows)} eset élő felvétele kész; egyezés: {ok}/{len(rows)}")
    print(f"Recording: {RECORDING_PATH}; spot-check cache: {SPOTCHECK_CACHE_PATH}")


def _replay_rows() -> list[dict]:
    from snow_kb.audience import replay_client_from_recording

    client = replay_client_from_recording(RECORDING_PATH)
    return _run_cases(client, live=False)


# ---------------------------------------------------------------------------
# Report (tiszta replay — determinisztikus, SC-005)
# ---------------------------------------------------------------------------

def _rows_at_threshold(rows: list[dict], threshold: float) -> list[dict]:
    """Per-eset predicted egy tetszőleges thresholdon — TISZTA replay-ből.

    A determinisztikus rétegek (update_set/spotcheck) threshold-függetlenek;
    a kalibrált réteg a tárolt (choice, confidence) párból számolható.
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
    """EXPLORATÍV threshold-sweep: aszimmetrikus + szimmetrikus költség."""
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
    """A legkisebb aszimmetrikus költségű threshold; holtversenyben a MAGASABB
    (a biztonságos irány: kevesebb átsikló hallucináció). EXPLORATÍV."""
    best_cost = min(p["asymmetric_cost"] for p in sweep)
    candidates = [p["threshold"] for p in sweep if p["asymmetric_cost"] == best_cost]
    return max(candidates)


def _regression_block(rows: list[dict], threshold: float) -> dict:
    """SC-003 (T008): a jelölt (vagy maradó) threshold a MEGLÉVŐ 24 példás
    mintán, összevetve a T004 baseline-nal. Romlás → a config NEM módosul."""
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

    # KD1 érzékenység-analízis: a legjobb sweep-threshold más súlyarányoknál
    # (5:1, 20:1) — ha érzéketlen, a legegyszerűbb 10:1 marad; ha érzékeny,
    # a T009 emberi kapu latolgatja az arányt.
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
        # SC-003: romlás a régi mintán → a config NEM módosul, a riport PIROS
        calib["decision"] = "marad"
        calib["threshold_after"] = CONFIRMATORY_THRESHOLD
        calib["rationale"] += (
            "; DE az SC-003 regresszio-gate ROMLAST mutat a meglevo 24 peldas "
            "mintan → a threshold NEM lep eletbe"
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
            "A threshold-sweep EXPLORATÍV — a legjobb sweep-sor NEM confirmatory "
            "eredmény. A threshold CSAK a T009 MANUÁLIS KAPU jóváhagyása után "
            "kerülhet a config.yaml-ba. A fail-open és a flag-only alapviselkedés "
            "kézzel beállított safety floor, a kalibráció NEM mozgatja."
        ),
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Report: {REPORT_PATH}")
    print(f"Kalibráció: {calib['decision']} — {calib['rationale']}")
    print(f"SC-003 regresszió: {'ROMLÁS (PIROS)' if regression['worse_than_baseline'] else 'nincs romlás'} "
          f"(költség {regression['baseline_asymmetric_cost']} → {regression['asymmetric_cost']})")


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] not in ("capture", "report"):
        raise SystemExit("Használat: python -m eval.verification_measure_015 [capture|report]")
    if not LABELED_PATH.exists():
        raise SystemExit(f"Hianyzik az egyesített minta: {LABELED_PATH} — "
                         "futtasd: python -m eval.verification_labeled_015 build "
                         "(T003 MANUÁLIS KAPU után)")
    if argv[0] == "capture":
        cmd_capture()
    else:
        cmd_report()


if __name__ == "__main__":
    main()
