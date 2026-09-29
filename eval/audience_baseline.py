"""eval/audience_baseline.py — spec 013 T003: baseline audience-rögzítés.

A JELENLEGI (generatív) út audience-döntései a 9 gold példán, változatlan kóddal:
a production StoryToKBArticle.extract lépése (ChainOfThought(ExtractChange)),
az analyze_changes előlépéssel együtt, ahogy a program.forward csinálja.
Az artifacts/program.json nem létezik → a base program a production viselkedés.

Futtatás (dev mód — lokális LLM, Kimi-token nélkül):
    SNOW_KB_DEV_MODE=1 python -m eval.audience_baseline

Kimenet: artifacts/audience_baseline.json (per-példa: number, audience, story hash).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path

import dspy

from eval.dataset import load_gold_dataset
from snow_kb.config import load_settings
from snow_kb.pipeline import build_lm
from snow_kb.program import ANALYZE_CHANGES_QUERY, StoryToKBArticle

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUT_PATH = Path("artifacts/audience_baseline.json")
GOLD_PATH = Path("data/examples/gold_dataset.md")


def main() -> None:
    settings = load_settings()
    logger.info("task_model=%s api_base=%s", settings.pipeline.task_model, settings.pipeline.api_base)

    trainset, valset = load_gold_dataset(GOLD_PATH)
    examples = trainset + valset
    logger.info("%d gold példa betöltve", len(examples))

    lm = build_lm(settings)
    program = StoryToKBArticle()  # base program = jelenlegi production viselkedés

    results = []
    with dspy.context(lm=lm):
        for i, ex in enumerate(examples, 1):
            story_text = ex.story_text
            full_context = story_text
            if getattr(ex, "update_set_payloads", ""):
                payload_snippet = ex.update_set_payloads[:50000]
                analysis = program.analyze_changes(
                    update_set_xml=payload_snippet, query=ANALYZE_CHANGES_QUERY
                )
                full_context += "\n\n## Update Set Technical Summary (via LLM)\n"
                full_context += analysis.technical_summary

            started = time.perf_counter()
            extracted = program.extract(story_text=full_context)
            latency_ms = (time.perf_counter() - started) * 1000.0

            story_json = json.dumps({"story_text": story_text}, sort_keys=True)
            results.append({
                "example_index": i,
                "story_sha256": hashlib.sha256(story_json.encode()).hexdigest(),
                "audience": extracted.audience,
                "latency_ms": round(latency_ms, 1),
                "task_model": settings.pipeline.task_model,
            })
            logger.info("[%d/9] audience=%s (%.0f ms)", i, extracted.audience, latency_ms)

    OUT_PATH.write_text(json.dumps({
        "spec": "013-audience-typed-decision / T003",
        "task_model": settings.pipeline.task_model,
        "api_base": settings.pipeline.api_base,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": results,
    }, indent=2), encoding="utf-8")
    logger.info("Baseline rögzítve: %s", OUT_PATH)


if __name__ == "__main__":
    main()
