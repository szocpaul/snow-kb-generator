"""eval/verification_baseline_015.py — spec 015 T004: the baseline comes first.

The asymmetric cost of the CURRENT threshold (0.7) on the existing 24-example
labelled sample — from the per-case rows of the 014 replay report, WITHOUT a new
live call (deterministic: the report comes from the replay, SC-005 hygiene).

This is the basis of the T008 regression gate (SC-003): the new (or staying)
threshold must not degrade on this same sample.

Run: python -m eval.verification_baseline_015
Output: artifacts/verification_asymmetric_baseline.json
"""

from __future__ import annotations

import json
from pathlib import Path

from eval.verification_asymmetric import cost_summary

SOURCE_REPORT = Path("artifacts/verification_calibration_report.json")  # 014 replay-report
OUT_PATH = Path("artifacts/verification_asymmetric_baseline.json")
CURRENT_THRESHOLD = 0.7  # a config.yaml verification_gate.confidence_threshold erteke


def main() -> None:
    if not SOURCE_REPORT.exists():
        raise SystemExit(f"Hianyzik a 014-es replay-report: {SOURCE_REPORT} — "
                         "futtasd: python -m eval.verification_measure report")
    report = json.loads(SOURCE_REPORT.read_text(encoding="utf-8"))
    rows = [{"predicted": r["predicted"], "expected": r["expected"]}
            for r in report["per_case"]]
    summary = cost_summary(rows)
    out = {
        "spec": "015-asymmetric-verification-gate / T004 baseline",
        "source": str(SOURCE_REPORT),
        "threshold": CURRENT_THRESHOLD,
        "n_cases": summary["n"],
        "asymmetric": summary,
        "note": "Baseline-elobb: a jelenlegi 0.7-es threshold aszimmetrikus "
                "cost on the existing 24-example sample. The T008 regression gate "
                "compares the new (or staying) threshold measurement with this (SC-003).",
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(f"Baseline: n={summary['n']}, aszimmetrikus koltseg={summary['total_cost']:.0f} "
          f"(fp_exists={summary['false_pos_exists']}x10, fn={summary['false_neg']}x1), "
          f"szimmetrikus={summary['symmetric_cost']:.0f}")
    print(f"Kiirva: {OUT_PATH}")


if __name__ == "__main__":
    main()
