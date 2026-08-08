"""compare.py — Compares two runs/*.json files axis by axis (T012 gate, SC-004).

Usage:
    python -m eval.compare runs/baseline.json runs/optimized.json

Exit code 0 if the optimized style average is >= baseline + 0.05 and the other axes
degrade by at most -0.02. Otherwise exit code 1 + the list of the failed axes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

AXES = ["structure", "content", "template", "hallucination", "style"]


def load_axis_averages(path: str | Path) -> dict[str, float]:
    """Reads the axis averages from a runs/*.json file (T010c format).

    It prefers the top-level axis_averages; if that is missing, it computes them
    from the per_example axes. If there is no per-axis data at all, it raises
    SystemExit — this gate intentionally does not run with the pre-T010c files.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("axis_averages"):
        return {a: float(data["axis_averages"][a]) for a in AXES if a in data["axis_averages"]}
    per = [e["axes"] for e in data.get("per_example", []) if e.get("axes")]
    if not per:
        raise SystemExit(
            f"ERROR: {path} does not contain per-axis data. "
            "Re-run the measurement with the post-T010c eval/baseline.py."
        )
    return {a: sum(float(e[a]) for e in per) / len(per) for a in AXES}


def compare(
    baseline_path: str | Path,
    optimized_path: str | Path,
    style_min_delta: float = 0.05,
    max_regression: float = 0.02,
) -> bool:
    """Compares the two runs; True if every threshold is met (T012 / SC-004)."""
    base = load_axis_averages(baseline_path)
    opt = load_axis_averages(optimized_path)

    all_ok = True
    for axis in AXES:
        delta = opt[axis] - base[axis]
        if axis == "style":
            passed = delta >= style_min_delta
            rule = f">= +{style_min_delta:.2f}"
        else:
            passed = delta >= -max_regression
            rule = f">= -{max_regression:.2f}"
        all_ok = all_ok and passed
        mark = "OK  " if passed else "FAIL"
        print(f"[{mark}] {axis:<14} baseline={base[axis]:.3f}  optimized={opt[axis]:.3f}  "
              f"delta={delta:+.3f}  (threshold: {rule})")

    print()
    print("RESULT:", "GREEN — the T012 thresholds are met" if all_ok
          else "RED — the T012 thresholds are NOT met")
    return all_ok


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", help="A baseline runs/*.json (the T010 reference)")
    parser.add_argument("optimized", help="The optimized runs/*.json (after GEPA)")
    parser.add_argument("--style-min-delta", type=float, default=0.05)
    parser.add_argument("--max-regression", type=float, default=0.02)
    args = parser.parse_args(argv)

    ok = compare(args.baseline, args.optimized, args.style_min_delta, args.max_regression)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
