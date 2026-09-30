"""eval/verification_sc_gates.py — spec 014 T013: SC-001..SC-004 gate-ek exit-code-dal.

  SC-001: a gold cikkeken 0 false "nem létezik" jelölés (a report sc001 blokkjából)
  SC-002: confirmatory 0.7-es kapunál selective_risk ≤ 0.15, coverage ≥ 0.7
          (a ≥20 példás címkézett mintán — 013-as tanulság)
  SC-003: fail-open tesztek (T006/T008/T010) — pytest exit code
  SC-004: a report kétszer futtatva byte-identikus (determinisztikus replay)

Futtatás: python -m eval.verification_sc_gates   (exit 0 = minden kapu zöld)
Előfeltétel: lefutott `python -m eval.verification_measure capture` + `report`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPORT_PATH = Path("artifacts/verification_calibration_report.json")


def gate_sc001(report: dict) -> bool:
    ok = report["sc001"]["zero_false_positive"]
    n = len(report["sc001"]["false_positives"])
    print(f"SC-001 {'ZÖLD' if ok else 'PIROS'}: false_positive_gold={n} / "
          f"{report['sc001']['total_gold']}")
    if not ok:
        for fp in report["sc001"]["false_positives"]:
            print(f"  - {fp['example']}: {fp['feedback'][:200]}")
    return ok


def gate_sc002(report: dict) -> bool:
    gates = report["sc002"]["gates"]
    ok = all(gates.values())
    print(f"SC-002 {'ZÖLD' if ok else 'PIROS'}: n={report['n_cases']} (≥20), "
          f"selective_risk={report['sc002']['selective_risk']:.3f} (≤0.15), "
          f"coverage={report['sc002']['coverage']:.3f} (≥0.7)")
    return ok and report["n_cases"] >= 20


def gate_sc003() -> bool:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "tests/test_verification.py::TestSpotChecker::test_error_is_unknown_fail_open",
         "tests/test_verification.py::TestVerifyComponentNames::test_instance_unreachable_fail_open",
         "tests/test_verification.py::TestCalibratedLayer::test_sdk_failure_fails_open_to_deterministic",
         "tests/test_verification_gate.py::TestVerificationGate::test_instance_unreachable_fail_open",
         "tests/test_eval_metric.py::TestInstanceAxis::test_lookup_failure_fail_open"],
        capture_output=True, text=True,
    )
    ok = proc.returncode == 0
    print(f"SC-003 {'ZÖLD' if ok else 'PIROS'}: fail-open tesztek exit={proc.returncode}")
    if not ok:
        print(proc.stdout[-1500:])
    return ok


def gate_sc004() -> bool:
    first = REPORT_PATH.read_bytes() if REPORT_PATH.exists() else b""
    proc = subprocess.run(
        [sys.executable, "-m", "eval.verification_measure", "report"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"SC-004 PIROS: a report futás hibázott:\n{proc.stdout[-1000:]}\n{proc.stderr[-1000:]}")
        return False
    second = REPORT_PATH.read_bytes()
    ok = first == second and len(second) > 0
    print(f"SC-004 {'ZÖLD' if ok else 'PIROS'}: kétszeri replay byte-identikus={ok} "
          f"({len(second)} byte)")
    return ok


def main() -> None:
    if not REPORT_PATH.exists():
        print("HIÁNYZIK a kalibrációs report — futtasd: "
              "python -m eval.verification_measure report")
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
        print(f"{name}: {'ZÖLD' if ok else 'PIROS'}")
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
