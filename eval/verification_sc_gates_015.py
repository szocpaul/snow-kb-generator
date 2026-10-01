"""eval/verification_sc_gates_015.py — spec 015 T012: SC-001..SC-005 gate-ek
exit-code-dal.

  SC-001: fixture-integritás — az update set MINDEN neve spot-checkkel létezik
          (scripts_pdi/fixture_verification_gate.py verify, ÉLŐ PDI-hívás)
  SC-002: kalibrációs riport a PDI-natív mintán (n≥30): a threshold-döntés
          indokolt, az aszimmetrikus költség nem rosszabb a baseline-nál,
          szimmetrikus összevetés a riportban
  SC-003: regresszió a meglévő 24 példás mintán — romlás esetén PIROS
          (és a config NEM módosul — ld. a riport decision-jét)
  SC-004: gate-emelés tesztek (T010/T011: közvetlen kliens-hívás gated,
          pontosan 1 döntés + 1 recording, fail-open) — pytest exit code
  SC-005: replay-reprodukálhatóság — a riport kétszer futtatva byte-identikus

Futtatás: python -m eval.verification_sc_gates_015   (exit 0 = minden kapu zöld)
Előfeltétel: T003 után lefutott `python -m eval.verification_labeled_015 build`,
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
    print(f"SC-001 {'ZÖLD' if ok else 'PIROS'}: fixture-integritás exit={proc.returncode}"
          + (f" — {tail[-1]}" if tail else ""))
    if not ok:
        print(proc.stdout[-1500:], proc.stderr[-500:])
    return ok


def gate_sc002(report: dict) -> bool:
    calib = report.get("calibration", {})
    n = report.get("n_cases", 0)
    has_rationale = bool(calib.get("decision")) and bool(calib.get("rationale"))
    symmetric_shown = ("symmetric_cost_before" in calib and "symmetric_cost_after" in calib)
    # a döntés konzisztens: "valtozik" csak szigorú javulással (a build_calibration_report
    # ezt kikényszeríti), "marad" mindig indokolt
    cost_ok = calib.get("cost_after", 1e9) <= calib.get("cost_before", -1e9)
    ok = n >= 30 and has_rationale and symmetric_shown and cost_ok
    print(f"SC-002 {'ZÖLD' if ok else 'PIROS'}: n={n} (≥30), "
          f"döntés={calib.get('decision')!r} indoklással={has_rationale}, "
          f"költség {calib.get('cost_before')} -> {calib.get('cost_after')} "
          f"(aszimmetrikus), szimmetrikus összevetés={'megvan' if symmetric_shown else 'HIÁNYZIK'}")
    if not REANCHOR_REPORT.exists():
        print("  FIGYELEM: a ReAnchor-riport hiányzik — a T007 kalibráció nem futott le.")
        return False
    return ok


def gate_sc003(report: dict) -> bool:
    reg = report.get("regression_sc003", {})
    ok = reg.get("worse_than_baseline") is False
    print(f"SC-003 {'ZÖLD' if ok else 'PIROS'}: régi minta (n={reg.get('n_old_cases')}) "
          f"aszimmetrikus költség {reg.get('baseline_asymmetric_cost')} -> "
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
    print(f"SC-004 {'ZÖLD' if ok else 'PIROS'}: gate-emelés tesztek exit={proc.returncode}")
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
        print(f"SC-005 PIROS: a report futás hibázott:\n{proc.stdout[-800:]}\n{proc.stderr[-800:]}")
        return False
    second = REPORT_PATH.read_bytes()
    ok = first == second and len(second) > 0
    print(f"SC-005 {'ZÖLD' if ok else 'PIROS'}: kétszeri replay byte-identikus={ok} "
          f"({len(second)} byte)")
    return ok


def main() -> None:
    if not REPORT_PATH.exists():
        print("HIÁNYZIK a 015-ös kalibrációs report — futtasd: "
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
        print(f"{name}: {'ZÖLD' if ok else 'PIROS'}")
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
