"""eval/context_recall_gate.py — spec 016 T008: recall-gate (SC-003), exit-code-dal.

A válogatott promptnak TARTALMAZNIA kell a gold cikkek által hivatkozott valós
komponensneveket. „Valós": a gold cikkben kinyert jelölt (a 011/extractor-
refinement kinyerő VÁLTOZATLAN kódjával), ami az EREDETI kontextusban is
megvan (tehát nem hallucináció a goldban, hanem a kontextusból jött).
A whitelistelt generikus nevek nem számítanak.

Szabály: 0/9 kiesés — egyetlen gold példánál sem eshet ki egyetlen valós
név sem a válogatott kontextusból. Kiesés esetén exit 1 + PIROS riport.

TISZTA replay: az artifacts/context_selection_capture.json (T007 capture)
selected szövegeit olvassa — új LLM-hívás nélkül, determinisztikus.

Futtatás: python -m eval.context_recall_gate   (exit 0 = ZÖLD)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.component_inventory import extract_candidates
from eval.context_baseline import GENERATIONS_PATH as BASELINE_GENS_PATH
from eval.context_measure import CAPTURE_PATH
from eval.dataset import load_gold_dataset


def main() -> None:
    if not CAPTURE_PATH.exists():
        print("HIÁNYZIK a selection capture — futtasd: "
              "python -m eval.context_measure capture-selection")
        sys.exit(2)

    capture = json.loads(CAPTURE_PATH.read_text(encoding="utf-8"))
    baseline_gens = json.loads(BASELINE_GENS_PATH.read_text(encoding="utf-8"))
    base_by_id = {r["id"]: r for r in baseline_gens["examples"]}

    trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
    gold_by_id = {f"gold-{i+1}": ex for i, ex in enumerate(trainset + valset)}

    failures = 0
    per_example = []
    for row in capture["examples"]:
        ex_id = row["id"]
        gold = gold_by_id[ex_id]
        original_context = (
            base_by_id[ex_id]["story_text"] + "\n" + base_by_id[ex_id]["update_set_payloads"]
        ).casefold()
        selected_context = (
            row["selected_story_text"] + "\n"
            + row["selected_update_set_payloads"] + "\n"
            + row["selected_related_articles_context"]
        ).casefold()

        candidates = extract_candidates(gold.html or "")
        real_names = [
            c["name"] for c in candidates
            if not c["whitelisted_generic"] and c["name"].casefold() in original_context
        ]
        missing = [n for n in real_names if n.casefold() not in selected_context]
        ok = not missing
        if not ok:
            failures += 1
        per_example.append({
            "id": ex_id,
            "real_names": len(real_names),
            "missing": missing,
            "ok": ok,
        })
        status = "OK " if ok else "KIESÉS"
        print(f"{ex_id}: {len(real_names)} valós név, {len(missing)} kiesés [{status}]"
              + (f" — {missing}" if missing else ""))

    total_missing = sum(len(r["missing"]) for r in per_example)
    print("=" * 60)
    print(f"SC-003 recall-gate: {total_missing} kiesés / "
          f"{len(per_example)} példa (a küszöb: 0)")
    sys.exit(0 if total_missing == 0 else 1)


if __name__ == "__main__":
    main()
