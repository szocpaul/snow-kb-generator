"""eval/audience_sc_gates.py — spec 013 T012: SC-001..SC-004 gate-ek exit-code-dal.

  SC-001: the new decision agrees with the gold label on the gold examples at
          least as often as the baseline (generative) path — per example JSON: artifacts/audience_calibration_report.json
  SC-002: on the confirmatory 0.7 gate selective_risk ≤ 0.15, coverage ≥ 0.7, ECE ≤ 0.10
  SC-003: fail-open test (T006) — pytest exit code
  SC-004: the report run twice is byte-identical (deterministic replay)

Run: python -m eval.audience_sc_gates   (exit 0 = every gate is green)
Prerequisite: `python -m eval.audience_measure capture` has been run.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPORT_PATH = Path("artifacts/audience_calibration_report.json")


def gate_sc001(report: dict) -> bool:
    ok = report["sc001"]["new_not_worse"]
    print(f"SC-001 {'GREEN' if ok else 'RED'}: baseline={report['sc001']['baseline_matches']} "
          f"new={report['sc001']['new_matches']} / {report['sc001']['total_gold']}")
    return ok


def gate_sc002(report: dict) -> bool:
    gates = report["sc002"]["gates"]
    ok = all(gates.values())
    print(f"SC-002 {'GREEN' if ok else 'RED'}: selective_risk={report['sc002']['selective_risk']:.3f} (≤0.15), "
          f"coverage={report['sc002']['coverage']:.3f} (≥0.7), ece={report['sc002']['ece']:.3f} (≤0.10)")
    return ok


def gate_sc003() -> bool:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "tests/test_audience_decision.py::TestDecideAudience::test_fail_open_on_sdk_error",
         "tests/test_audience_decision.py::TestDecideAudience::test_fail_open_on_unexpected_schema",
         "tests/test_audience_decision.py::TestResolveAudience::test_fail_open_returns_none"],
        capture_output=True, text=True,
    )
    ok = proc.returncode == 0
    print(f"SC-003 {'GREEN' if ok else 'RED'}: fail-open tests exit={proc.returncode}")
    if not ok:
        print(proc.stdout[-1500:])
    return ok


def gate_sc004() -> bool:
    first = REPORT_PATH.read_bytes() if REPORT_PATH.exists() else b""
    proc = subprocess.run(
        [sys.executable, "-m", "eval.audience_measure", "report"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"SC-004 RED: the report run failed:\n{proc.stdout[-1000:]}\n{proc.stderr[-1000:]}")
        return False
    second = REPORT_PATH.read_bytes()
    ok = first == second and len(second) > 0
    print(f"SC-004 {'GREEN' if ok else 'RED'}: the double replay is byte-identical={ok} ({len(second)} bytes)")
    return ok


def main() -> None:
    if not REPORT_PATH.exists():
        print("The calibration report is MISSING — run: python -m eval.audience_measure report")
        sys.exit(2)
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    results = {
        "SC-001": gate_sc001(report),
        "SC-002": gate_sc002(report),
        "SC-003": gate_sc003(),
        "SC-004": gate_sc004(),
    }
    print("=" * 60)
    for name, ok in results.items():
        print(f"{name}: {'GREEN' if ok else 'RED'}")
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
