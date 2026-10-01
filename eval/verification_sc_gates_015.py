"""eval/verification_sc_gates_015.py — spec 015 T012: SC-001..SC-005 gate-ek
exit-code-dal.

  SC-001: fixture integrity — EVERY name of the update set exists per the spot-check
          (scripts_pdi/fixture_verification_gate.py verify, a LIVE PDI call)
  SC-002: the calibration report on the PDI-native sample (n≥30): the threshold decision
          is justified, the asymmetric cost is not worse than the baseline,
          the symmetric comparison is in the report
  SC-003: regression on the existing 24-example sample — on a degradation RED
          (and the config is NOT modified — see the decision of the report)
  SC-004: the gate-lift tests (T010/T011: the direct client call is gated,
          exactly 1 decision + 1 recording, fail-open) — the pytest exit code
  SC-005: replay reproducibility — the report run twice is byte-identical

Run: python -m eval.verification_sc_gates_015   (exit 0 = every gate is green)
Prerequisite: `python -m eval.verification_labeled_015 build` has been run after T003,
             `python -m eval.verification_measure_015 capture` + `report`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPORT_PATH = Path("artifacts/verification_calibration_report_015.json")
REANCHOR_REPORT = Path("artifacts/verification_reanchor_report_015.json")


def gate_sc001() -> bool:
    proc = subprocess.run(
        [sys.executable, "scripts_pdi/fixture_verification_gate.py", "verify"],
        capture_output=True, text=True,
    )
    ok = proc.returncode == 0
    tail = (proc.stdout or "").strip().splitlines()
    print(f"SC-001 {'GREEN' if ok else 'RED'}: fixture integrity exit={proc.returncode}"
          + (f" — {tail[-1]}" if tail else ""))
    if not ok:
        print(proc.stdout[-1500:], proc.stderr[-500:])
    return ok


def gate_sc002(report: dict) -> bool:
    calib = report.get("calibration", {})
    n = report.get("n_cases", 0)
    has_rationale = bool(calib.get("decision")) and bool(calib.get("rationale"))
    symmetric_shown = ("symmetric_cost_before" in calib and "symmetric_cost_after" in calib)
    # the decision is consistent: "changes" only with a strict improvement (build_calibration_report
    # enforces this), "stays" is always justified
    cost_ok = calib.get("cost_after", 1e9) <= calib.get("cost_before", -1e9)
    ok = n >= 30 and has_rationale and symmetric_shown and cost_ok
    print(f"SC-002 {'GREEN' if ok else 'RED'}: n={n} (≥30), "
          f"decision={calib.get('decision')!r} with a rationale={has_rationale}, "
          f"cost {calib.get('cost_before')} -> {calib.get('cost_after')} "
          f"(asymmetric), symmetric comparison={'present' if symmetric_shown else 'MISSING'}")
    if not REANCHOR_REPORT.exists():
        print("  WARNING: the ReAnchor report is missing — the T007 calibration has not been run.")
        return False
    return ok


def gate_sc003(report: dict) -> bool:
    reg = report.get("regression_sc003", {})
    ok = reg.get("worse_than_baseline") is False
    print(f"SC-003 {'GREEN' if ok else 'RED'}: the old sample (n={reg.get('n_old_cases')}) "
          f"asymmetric cost {reg.get('baseline_asymmetric_cost')} -> "
          f"{reg.get('asymmetric_cost')} a {reg.get('threshold')} thresholdon")
    return ok


def gate_sc004() -> bool:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "tests/test_verification_gate_client.py",
         "tests/test_verification_gate.py",
         "tests/test_verification_asymmetric.py"],
        capture_output=True, text=True,
    )
    ok = proc.returncode == 0
    print(f"SC-004 {'GREEN' if ok else 'RED'}: the gate-lift tests exit={proc.returncode}")
    if not ok:
        print(proc.stdout[-1500:])
    return ok


def gate_sc005() -> bool:
    first = REPORT_PATH.read_bytes() if REPORT_PATH.exists() else b""
    proc = subprocess.run(
        [sys.executable, "-m", "eval.verification_measure_015", "report"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"SC-005 RED: the report run failed:\n{proc.stdout[-800:]}\n{proc.stderr[-800:]}")
        return False
    second = REPORT_PATH.read_bytes()
    ok = first == second and len(second) > 0
    print(f"SC-005 {'GREEN' if ok else 'RED'}: the double replay is byte-identical={ok} "
          f"({len(second)} byte)")
    return ok


def main() -> None:
    if not REPORT_PATH.exists():
        print("The 015 calibration report is MISSING — run: "
              "python -m eval.verification_measure_015 report")
        sys.exit(2)
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    results = {
        "SC-001": gate_sc001(),
        "SC-002": gate_sc002(report),
        "SC-003": gate_sc003(report),
        "SC-004": gate_sc004(),
        "SC-005": gate_sc005(),
    }
    print("=" * 60)
    for name, ok in results.items():
        print(f"{name}: {'GREEN' if ok else 'RED'}")
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
