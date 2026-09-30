"""component_inventory.py — Baseline inventory of the component name candidates (spec 014, T003).

The existing gold articles + (optionally) a freshly generated article sample
component name candidates with the 011 pattern (quoted names, CamelCase,
dotted identifiers), and writes a per example JSON to artifacts/.

The extraction repeats the regular expressions of eval/metric.py's
_find_hallucinated_components WITHOUT MODIFICATION (spec 014 T003: "unchanged
code") — the T007 refactors it into a shared place (src/snow_kb/verification.py).

Run (DEV mode, local LLM for the generated sample):
    SNOW_KB_DEV_MODE=1 python -m eval.component_inventory            # gold only
    SNOW_KB_DEV_MODE=1 python -m eval.component_inventory --generate 3  # + 3 fresh articles

Output: artifacts/component_inventory.json
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from eval.dataset import load_gold_dataset
from eval.metric import COMPONENT_NAME_WHITELIST

_WHITELIST_CF: set[str] = {w.casefold() for w in COMPONENT_NAME_WHITELIST}


def extract_candidates(html: str) -> list[dict]:
    """Extracts the component name candidates with the 011 pattern (a metric.py replica).

    It returns the candidates with a type hint and a whitelist flag — the
    story verification does NOT happen here (that is the job of the 011 axis), here we
    need the RAW candidate list for the instance verification (T004).
    """
    text = re.sub(r"<[^>]+>", " ", html)  # drop the tags + the attribute URLs
    text = re.sub(r"https?://\S+", " ", text)  # the visible URLs
    text = re.sub(r"\b\S+@\S+\b", " ", text)  # the email addresses

    candidates: list[dict] = []

    def _add(name: str, kind: str) -> None:
        name = name.strip()
        if not name:
            return
        if any(c["name"] == name for c in candidates):
            return
        candidates.append({
            "name": name,
            "kind": kind,
            "whitelisted_generic": name.casefold() in _WHITELIST_CF,
        })

    # the quoted names (starting with a capital, between simple quotes)
    for m in re.findall(r"'([A-Z][A-Za-z0-9 _.:/-]{2,50})'", text):
        _add(m, "quoted")
    # the dotted identifiers (a segment of at least 2 characters is needed — 'e.g' drops out)
    for d in re.findall(r"\b([a-z]+[a-z0-9]*(?:\.[a-z0-9_]+)+)\b", text):
        if any(len(seg) >= 2 for seg in d.split(".")):
            _add(d, "dotted")
    # the CamelCase identifiers
    for m in re.findall(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b", text):
        _add(m, "camelcase")

    return candidates


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Component name baseline inventory (spec 014 T003).")
    parser.add_argument("--dataset", default="data/examples/gold_dataset.md")
    parser.add_argument("--generate", type=int, default=0,
                        help="Also inventories this many freshly generated articles (the first N gold examples).")
    parser.add_argument("--output", default="artifacts/component_inventory.json")
    args = parser.parse_args(argv)

    trainset, valset = load_gold_dataset(args.dataset)
    all_examples = trainset + valset

    inventory: list[dict] = []
    for idx, ex in enumerate(all_examples):
        candidates = extract_candidates(ex.html or "")
        inventory.append({
            "id": f"gold-{idx+1}",
            "source": "gold",
            "candidates": candidates,
        })
        print(f"gold-{idx+1}: {len(candidates)} candidates")

    if args.generate > 0:
        import dspy

        from snow_kb.config import load_settings
        from snow_kb.pipeline import build_lm
        from snow_kb.program import StoryToKBArticle

        settings = load_settings()
        lm = build_lm(settings)
        program = StoryToKBArticle()
        subset = all_examples[: args.generate]
        with dspy.context(lm=lm):
            for idx, ex in enumerate(subset):
                pred = program(
                    story_text=ex.story_text,
                    template_context=ex.template_context,
                    update_set_payloads=getattr(ex, "update_set_payloads", "") or "",
                )
                html = ""
                if getattr(pred, "article", None) is not None:
                    html = pred.article.html or ""
                elif getattr(pred, "html", None):
                    html = pred.html
                candidates = extract_candidates(html)
                inventory.append({
                    "id": f"generated-{idx+1}",
                    "source": "generated",
                    "gold_ref": f"gold-{idx+1}",
                    "candidates": candidates,
                })
                print(f"generated-{idx+1}: {len(candidates)} candidates")

    report = {
        "spec": "014-component-instance-verification",
        "task": "T003",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset,
        "examples": inventory,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {len(inventory)} examples → {out}")


if __name__ == "__main__":
    main()
