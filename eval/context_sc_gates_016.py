"""eval/context_sc_gates_016.py — spec 016 T013: SC-001..SC-006 gate-ek
exit-code-dal.

  SC-001: költség — a válogatott futás TELJES PROMPT tokenje (template +
          kontextus, LM usage prompt_tokens) legalább a T003 MANUÁLIS KAPUnál
          rögzített aránnyal (≥5%) kisebb a baseline-nál
          (artifacts/context_sc001_target.json)
  SC-002: minőség-védelem — a rich_metric-delta párosított bootstrap CI95-e
          NEM teljesen 0 alatt (a 013/014-es nem-átfedő-intervallum szabály)
  SC-003: recall-védelem — eval/context_recall_gate.py exit 0 (0/9 kiesés)
  SC-004: fail-open — tests/test_context_selection.py exit 0
  SC-005: replay — a hatásmérés riport kétszer futtatva byte-identikus
  SC-006: kalibráció — min. 20 címkézett darab, döntés + indoklás fájlba,
          a safety floor érintetlen (config: min_confidence/fail-open/FR-004)

Futtatás: python -m eval.context_sc_gates_016   (exit 0 = minden kapu zöld)
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
        print("SC-001 PIROS: hiányzik az SC-001 célérték "
              "(a T003 MANUÁLIS KAPU rögzíti — artifacts/context_sc001_target.json)")
        return False
    target = json.loads(TARGET_PATH.read_text(encoding="utf-8"))
    report = json.loads(MEASURE_PATH.read_text(encoding="utf-8"))
    td = report["token_delta"]
    target_ratio = target["target_reduction_ratio"]
    # A T003 kapu döntése: a cél a TELJES PROMPTON mért csökkenés (LM usage
    # prompt_tokens), NEM csak a kontextus-darabokon.
    prompt_reduction = td.get("prompt_reduction_ratio")
    if prompt_reduction is None:
        print("SC-001 PIROS: nincs prompt-usage adat a riportban (a generálás "
              "usage capture-je hiányzik)")
        return False
    ok = prompt_reduction >= target_ratio
    print(f"SC-001 {'ZÖLD' if ok else 'PIROS'}: teljes prompt "
          f"{td['baseline_prompt_usage_sum']} → {td['selected_prompt_usage_sum']} "
          f"({prompt_reduction:.1%} csökkenés; cél ≥ {target_ratio:.1%} a TELJES "
          f"prompton, rögzítve: {target.get('decided_at', '?')}; referencia: "
          f"kontextus-token {td['baseline_context_tokens']} → "
          f"{td['selected_context_tokens']} = {td['reduction_ratio']:.1%})")
    if not ok:
        # A T012 MANUÁLIS KAPU emberi döntése (2026-10-02): az SC-001
        # DOKUMENTÁLT PIROS — a ≥5% cél a minőség-kockázat nélkül nem érhető el
        # (költség-korlátos plafon 0.0%, state-fixszel ~1.1-1.2%; az SC-002
        # elsődlegessége húzta meg). Ez a gate NEM buktatja a futást.
        print("  DOKUMENTÁLT PIROS (T012 emberi döntés): a cél a rubrikával "
              "minőség-kockázat nélkül nem érhető el — ld. gate-T012.md §4; "
              "a feature enabled=false marad")
        return "documented"
    return ok


def gate_sc002() -> bool:
    report = json.loads(MEASURE_PATH.read_text(encoding="utf-8"))
    qd = report["quality_delta"]
    ok = qd["not_worse_beyond_noise"] is True
    print(f"SC-002 {'ZÖLD' if ok else 'PIROS'}: rich_metric "
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
    print(f"SC-003 {'ZÖLD' if ok else 'PIROS'}: recall-gate exit={proc.returncode}"
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
    print(f"SC-004 {'ZÖLD' if ok else 'PIROS'}: fail-open tesztek exit={proc.returncode}")
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
        print(f"SC-005 PIROS: a report futás hibázott:\n{proc.stdout[-600:]}\n{proc.stderr[-600:]}")
        return False
    second = MEASURE_PATH.read_bytes()
    ok = first == second and len(second) > 0
    print(f"SC-005 {'ZÖLD' if ok else 'PIROS'}: kétszeri replay byte-identikus={ok} "
          f"({len(second)} byte)")
    return ok


def gate_sc006() -> bool:
    if not CALIB_PATH.exists():
        print("SC-006 PIROS: hiányzik a kalibrációs riport — futtasd: "
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
    # A végső küszöb-döntés a T012 MANUÁLIS KAPU emberi döntése; a gate
    # ellenőrzi, hogy a config a döntésnek megfelelően VÁLTOZATLAN (0.25).
    import yaml as _yaml

    cfg_val = (_yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
               .get("context_selection", {}).get("hide_below"))
    config_ok = (t012.get("final_decision") == "marad"
                 and cfg_val == t012.get("final_hide_below"))
    ok = (n >= 20 and has_rationale and floor_ok and REANCHOR_PATH.exists()
          and config_ok)
    print(f"SC-006 {'ZÖLD' if ok else 'PIROS'}: n={n} (≥20), "
          f"sweep-döntés={calib.get('decision')!r} (EXPLORATÍV) indoklással={has_rationale}, "
          f"T012 végső döntés={t012.get('final_decision')!r}, "
          f"config hide_below={cfg_val} (változatlan={config_ok}), "
          f"safety floor érintetlen={floor_ok}, "
          f"ReAnchor-riport={'megvan' if REANCHOR_PATH.exists() else 'HIÁNYZIK'}")
    return ok


def main() -> None:
    missing = [p for p in (BASELINE_PATH, MEASURE_PATH) if not p.exists()]
    if missing:
        print(f"HIÁNYZÓ artifactok: {missing} — a T002/T007 mérések futtak már?")
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
        label = "ZÖLD" if ok is True else ("DOKUMENTÁLT PIROS (elfogadott)" if ok == "documented" else "PIROS")
        print(f"{name}: {label}")
    # A T012 döntés szerint az SC-001 dokumentált PIROS elfogadott végállapot;
    # minden más gate kötelezően zöld.
    ok_all = all(v is True or v == "documented" for v in results.values())
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
