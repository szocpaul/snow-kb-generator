"""component_inventory.py — Baseline-leltár a komponensnév-jelöltekről (spec 014, T003).

A meglévő gold cikkek + (opcionálisan) egy frissen generált cikkminta
komponensnév-jelöltjeit nyeri ki a 011-es mintával (idézett nevek, CamelCase,
dotted azonosítók), és per-példa JSON-t ír az artifacts/ alá.

A kinyerés a eval/metric.py _find_hallucinated_components reguláris
kifejezéseit ismétli meg VÁLTOZTATÁS NÉLKÜL (a spec 014 T003: "változatlan
kóddal") — a T007 refaktorálja közös helyre (src/snow_kb/verification.py).

Futtatás (DEV mód, lokális LLM a generált mintához):
    SNOW_KB_DEV_MODE=1 python -m eval.component_inventory            # csak gold
    SNOW_KB_DEV_MODE=1 python -m eval.component_inventory --generate 3  # + 3 friss cikk

Kimenet: artifacts/component_inventory.json
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
    """Komponensnév-jelöltek kinyerése a 011-es mintával (metric.py replika).

    Visszaadja a jelölteket típus-tippel és whitelist-jelöléssel — a
    story-ellenőrzés NEM itt történik (az a 011-es tengely dolga), itt a
    NYERS jelöltlista kell az instance-ellenőrzéshez (T004).
    """
    text = re.sub(r"<[^>]+>", " ", html)  # tagek + attribútum-URL-ek eldobása
    text = re.sub(r"https?://\S+", " ", text)  # látható URL-ek
    text = re.sub(r"\b\S+@\S+\b", " ", text)  # email címek

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

    # idézett nevek (nagybetűvel kezdődő, szimpla idézőjel között)
    for m in re.findall(r"'([A-Z][A-Za-z0-9 _.:/-]{2,50})'", text):
        _add(m, "quoted")
    # dotted azonosítók (min. 2 karakteres szegmens kell — az 'e.g' kiesik)
    for d in re.findall(r"\b([a-z]+[a-z0-9]*(?:\.[a-z0-9_]+)+)\b", text):
        if any(len(seg) >= 2 for seg in d.split(".")):
            _add(d, "dotted")
    # CamelCase azonosítók
    for m in re.findall(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b", text):
        _add(m, "camelcase")

    return candidates


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Komponensnév baseline-leltár (spec 014 T003).")
    parser.add_argument("--dataset", default="data/examples/gold_dataset.md")
    parser.add_argument("--generate", type=int, default=0,
                        help="Ennyi frissen generált cikket is leltároz (az első N gold példára).")
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
        print(f"gold-{idx+1}: {len(candidates)} jelölt")

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
                print(f"generated-{idx+1}: {len(candidates)} jelölt")

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
    print(f"\nLeírt {len(inventory)} példa → {out}")


if __name__ == "__main__":
    main()
