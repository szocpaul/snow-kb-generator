"""compare.py — Két runs/*.json tengelyenkénti összevetése (T012 gate, SC-004).

Használat:
    python -m eval.compare runs/baseline.json runs/optimized.json

Exit code 0, ha az optimized style-átlag >= baseline + 0.05, és a többi tengely
max -0.02 romlás. Egyébként exit code 1 + a bukott tengelyek listája.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

AXES = ["structure", "content", "template", "hallucination", "style"]


def load_axis_averages(path: str | Path) -> dict[str, float]:
    """Beolvassa a tengely-átlagokat egy runs/*.json fájlból (T010c formátum).

    A top-level axis_averages-t preferálja; ha hiányzik, a per_example axes-ből
    számolja. Ha per-axis adat egyáltalán nincs, SystemExit-t dob — a T010c
    előtti fájlokkal ez a gate szándékosan nem fut.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("axis_averages"):
        return {a: float(data["axis_averages"][a]) for a in AXES if a in data["axis_averages"]}
    per = [e["axes"] for e in data.get("per_example", []) if e.get("axes")]
    if not per:
        raise SystemExit(
            f"HIBA: {path} nem tartalmaz per-axis adatot. "
            "Futtasd újra a mérést a T010c utáni eval/baseline.py-jel."
        )
    return {a: sum(float(e[a]) for e in per) / len(per) for a in AXES}


def compare(
    baseline_path: str | Path,
    optimized_path: str | Path,
    style_min_delta: float = 0.05,
    max_regression: float = 0.02,
) -> bool:
    """Összeveti a két futást; True, ha minden küszöb teljesül (T012 / SC-004)."""
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
              f"delta={delta:+.3f}  (küszöb: {rule})")

    print()
    print("EREDMÉNY:", "ZÖLD — a T012 küszöbök teljesülnek" if all_ok
          else "PIROS — a T012 küszöbök NEM teljesülnek")
    return all_ok


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", help="A baseline runs/*.json (T010-es referencia)")
    parser.add_argument("optimized", help="Az optimized runs/*.json (GEPA utáni)")
    parser.add_argument("--style-min-delta", type=float, default=0.05)
    parser.add_argument("--max-regression", type=float, default=0.02)
    args = parser.parse_args(argv)

    ok = compare(args.baseline, args.optimized, args.style_min_delta, args.max_regression)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
