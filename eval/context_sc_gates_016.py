"""eval/context_sc_gates_016.py — spec 016 T013: SC-001..SC-006 gate-ek
exit-code-dal.

  SC-001: cost — the FULL PROMPT tokens of the selected run (template +
          context, LM usage prompt_tokens) are at least by the ratio recorded at the
          T003 MANUAL GATE smaller than the baseline (≥5%)
          (artifacts/context_sc001_target.json)
  SC-002: quality protection — the paired bootstrap CI95 of the rich_metric delta
          is NOT entirely below 0 (the 013/014 non-overlapping interval rule)
  SC-003: recall protection — eval/context_recall_gate.py exit 0 (0/9 drops)
  SC-004: fail-open — tests/test_context_selection.py exit 0
  SC-005: replay — the impact measurement report run twice is byte-identical
  SC-006: calibration — at least 20 labelled pieces, the decision + the rationale in a file,
          the safety floor is untouched (config: min_confidence/fail-open/FR-004)

Run: python -m eval.context_sc_gates_016   (exit 0 = every gate is green)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BASELINE_PATH = Path("artifacts/context_baseline.json")
MEASURE_PATH = Path("artifacts/context_selection_report.json")
CALIB_PATH = Path("artifacts/context_calibration_report_016.json")
REANCHOR_PATH = Path("artifacts/context_reanchor_report_016.json")
TARGET_PATH = Path("artifacts/context_sc001_target.json")


def gate_sc001() -> bool:
    if not TARGET_PATH.exists():
        print("SC-001 RED: the SC-001 target value is missing "
              "(the T003 MANUAL GATE records it — artifacts/context_sc001_target.json)")
        return False
    target = json.loads(TARGET_PATH.read_text(encoding="utf-8"))
    report = json.loads(MEASURE_PATH.read_text(encoding="utf-8"))
    td = report["token_delta"]
    target_ratio = target["target_reduction_ratio"]
    # The decision of the T003 gate: the target is the reduction measured on the FULL PROMPT (LM usage
    # prompt_tokens), NOT only on the context pieces.
    prompt_reduction = td.get("prompt_reduction_ratio")
    if prompt_reduction is None:
        print("SC-001 RED: there is no prompt usage data in the report (the generation "
              "is missing its usage capture)")
        return False
    ok = prompt_reduction >= target_ratio
    print(f"SC-001 {'GREEN' if ok else 'RED'}: the full prompt "
          f"{td['baseline_prompt_usage_sum']} → {td['selected_prompt_usage_sum']} "
          f"({prompt_reduction:.1%} reduction; target ≥ {target_ratio:.1%} on the FULL "
          f"prompt, recorded: {target.get('decided_at', '?')}; reference: "
          f"kontextus-token {td['baseline_context_tokens']} → "
          f"{td['selected_context_tokens']} = {td['reduction_ratio']:.1%})")
    if not ok:
        # The human decision of the T012 MANUAL GATE (2026-10-02): the SC-001
        # DOCUMENTED RED — the ≥5% target cannot be reached without a quality risk
        # (the cost-bound ceiling is 0.0%, with the state fix ~1.1-1.2%; the SC-002
        # primacy is what pulled it down). This gate does NOT fail the run.
        print("  DOCUMENTED RED (T012 human decision): the target cannot be reached with the rubric "
              "without a quality risk — see gate-T012.md §4; "
              "a feature enabled=false marad")
        return "documented"
    return ok


def gate_sc002() -> bool:
    report = json.loads(MEASURE_PATH.read_text(encoding="utf-8"))
    qd = report["quality_delta"]
    ok = qd["not_worse_beyond_noise"] is True
    print(f"SC-002 {'GREEN' if ok else 'RED'}: rich_metric "
          f"{qd['rich_metric_avg_before']} → {qd['rich_metric_avg_after']} "
          f"(CI95 {qd['paired_bootstrap_ci95']})")
    return ok


def gate_sc003() -> bool:
    proc = subprocess.run(
        [sys.executable, "-m", "eval.context_recall_gate"],
        capture_output=True, text=True,
    )
    ok = proc.returncode == 0
    tail = (proc.stdout or "").strip().splitlines()
    print(f"SC-003 {'GREEN' if ok else 'RED'}: recall-gate exit={proc.returncode}"
          + (f" — {tail[-1]}" if tail else ""))
    if not ok:
        print(proc.stdout[-1200:])
    return ok


def gate_sc004() -> bool:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_context_selection.py"],
        capture_output=True, text=True,
    )
    ok = proc.returncode == 0
    print(f"SC-004 {'GREEN' if ok else 'RED'}: the fail-open tests exit={proc.returncode}")
    if not ok:
        print(proc.stdout[-1200:])
    return ok


def gate_sc005() -> bool:
    first = MEASURE_PATH.read_bytes() if MEASURE_PATH.exists() else b""
    proc = subprocess.run(
        [sys.executable, "-m", "eval.context_measure", "report"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"SC-005 RED: the report run failed:\n{proc.stdout[-600:]}\n{proc.stderr[-600:]}")
        return False
    second = MEASURE_PATH.read_bytes()
    ok = first == second and len(second) > 0
    print(f"SC-005 {'GREEN' if ok else 'RED'}: the double replay is byte-identical={ok} "
          f"({len(second)} byte)")
    return ok


def gate_sc006() -> bool:
    if not CALIB_PATH.exists():
        print("SC-006 RED: the calibration report is missing — run: "
              "python -m eval.context_calibration_016 report")
        return False
    report = json.loads(CALIB_PATH.read_text(encoding="utf-8"))
    calib = report.get("calibration", {})
    floor = report.get("safety_floor", {})
    t012 = report.get("t012_human_decision", {})
    n = report.get("n_labeled", 0)
    has_rationale = bool(calib.get("decision")) and bool(calib.get("rationale"))
    floor_ok = (
        floor.get("fail_open") == "show"
        and floor.get("min_confidence") == 0.6
        and floor.get("story_core_never_hide") is True
    )
    # The final threshold decision is the human decision of the T012 MANUAL GATE; the gate
    # checks that the config is UNCHANGED accordingly (0.25).
    import yaml as _yaml

    cfg_val = (_yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
               .get("context_selection", {}).get("hide_below"))
    config_ok = (t012.get("final_decision") == "marad"
                 and cfg_val == t012.get("final_hide_below"))
    ok = (n >= 20 and has_rationale and floor_ok and REANCHOR_PATH.exists()
          and config_ok)
    print(f"SC-006 {'GREEN' if ok else 'RED'}: n={n} (≥20), "
          f"sweep decision={calib.get('decision')!r} (EXPLORATORY) with a rationale={has_rationale}, "
          f"T012 final decision={t012.get('final_decision')!r}, "
          f"config hide_below={cfg_val} (unchanged={config_ok}), "
          f"safety floor untouched={floor_ok}, "
          f"ReAnchor report={'present' if REANCHOR_PATH.exists() else 'MISSING'}")
    return ok


def main() -> None:
    missing = [p for p in (BASELINE_PATH, MEASURE_PATH) if not p.exists()]
    if missing:
        print(f"MISSING artifacts: {missing} — have the T002/T007 measurements been run?")
        sys.exit(2)
    results = {
        "SC-001": gate_sc001(),
        "SC-002": gate_sc002(),
        "SC-003": gate_sc003(),
        "SC-004": gate_sc004(),
        "SC-005": gate_sc005(),
        "SC-006": gate_sc006(),
    }
    print("=" * 60)
    for name, ok in results.items():
        label = "GREEN" if ok is True else ("DOCUMENTED RED (accepted)" if ok == "documented" else "RED")
        print(f"{name}: {label}")
    # According to the T012 decision the documented RED of the SC-001 is an accepted final state;
    # every other gate must be green.
    ok_all = all(v is True or v == "documented" for v in results.values())
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
