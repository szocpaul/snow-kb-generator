"""eval/context_measure.py — spec 016 T007: hatásmérés a gold példákon.

Válogatott futás vs baseline (T002): per-példa és összesített token-delta +
rich_metric-delta. A minőség NEM romolhat a zaj-sávon túl (SC-002); a riport
kétszeri replay-futtatása byte-identikus (SC-005).

Capture/report szétválasztás (a 015-ös minta):
    python -m eval.context_measure capture-selection
        # élő: system_one Score-döntések (TYPESAFE_API_KEY) + summarize a
        # lokális endpointon + /tokenize — artifacts/context_selection_capture.json
    SNOW_KB_DEV_MODE=1 python -m eval.context_measure capture-generations
        # élő: cikkgenerálás a VÁLOGATOTT kontextussal (LASSÚ, lokális Qwen,
        # cache=False — ugyanaz az LM-setup, mint a T002 baseline)
    SNOW_KB_DEV_MODE=1 python -m eval.context_measure capture-metrics
        # élő: rich_metric (style judge) a válogatott generálásokon
    python -m eval.context_measure report
        # TISZTA replay: a capture-fájlokból számol, byte-identikus riport

A threshold-sweep NEM itt történik (az a T011 kalibráció); ez a mérés a
jelenlegi config-küszöbökkel fut.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.context_baseline import (
    API_BASE,
    DATASET_PATH,
    GENERATIONS_PATH as BASELINE_GENS_PATH,
    MAX_TOKENS,
    TASK_MODEL,
    TEMPERATURE,
    TOKEN_METHOD,
    METRICS_PATH as BASELINE_METRICS_PATH,
    TOKENS_PATH as BASELINE_TOKENS_PATH,
    _configure_lm,
    _count_tokens,
    capture_metrics_for,
)

CAPTURE_PATH = Path("artifacts/context_selection_capture.json")
SEL_GENS_PATH = Path("artifacts/context_selection_generations.json")
SEL_METRICS_PATH = Path("artifacts/context_selection_metrics.json")
REPORT_PATH = Path("artifacts/context_selection_report.json")
MEASUREMENT_RECORDING = Path("artifacts/context_selection_measurement.jsonl")


# ---------------------------------------------------------------------------
# capture-selection: Score-döntések + summarize + tokenek (élő)
# ---------------------------------------------------------------------------

def cmd_capture_selection() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    from eval.verification_measure import _RecordingClient  # 014-es újrahasznosítás
    from snow_kb.config import load_settings
    from snow_kb.context_selection import select_context, split_context_into_pieces

    gens = json.loads(BASELINE_GENS_PATH.read_text(encoding="utf-8"))["examples"]
    settings = load_settings(dry_run=True)
    # a mérés a config küszöbeivel fut, de KÜLÖN recording-fájlba (a 015 minta)
    object.__setattr__(settings.context_selection, "enabled", True)
    object.__setattr__(settings.context_selection, "recording_path",
                       str(MEASUREMENT_RECORDING))

    from typesafe_sdk import TypeSafeClient

    client = _RecordingClient(TypeSafeClient(), MEASUREMENT_RECORDING)

    rows = []
    for ex in gens:
        ex_id = ex["id"]
        print(f"[{ex_id}] válogatás...", flush=True)
        pieces = split_context_into_pieces(
            story_text=ex["story_text"],
            update_set_payloads=ex["update_set_payloads"],
            related_articles_context="",
        )
        result = select_context(
            story_text=ex["story_text"],
            update_set_payloads=ex["update_set_payloads"],
            related_articles_context="",
            settings=settings,
            client=client,
            pieces=pieces,
        )
        piece_rows = []
        for piece, decision in zip(pieces, result.decisions):
            piece_rows.append({
                "piece_id": piece.piece_id,
                "source_type": piece.source_type,
                "label": piece.label,
                "verdict": decision.verdict,
                "relevance": decision.relevance,
                "confidence": decision.confidence,
                "reason": decision.reason,
                "summarized": decision.summarized,
            })
        selected_story = result.story_text
        selected_us = result.update_set_payloads
        rows.append({
            "id": ex_id,
            "pieces": piece_rows,
            "selected_story_text": selected_story,
            "selected_update_set_payloads": selected_us,
            "selected_related_articles_context": result.related_articles_context,
            "selected_story_tokens": _count_tokens(selected_story),
            "selected_update_set_tokens": _count_tokens(selected_us) if selected_us else 0,
        })
        n_hide = sum(1 for p in piece_rows if p["verdict"] == "hide")
        n_sum = sum(1 for p in piece_rows if p["verdict"] == "summarize")
        print(f"  {len(pieces)} darab: {n_hide} hide, {n_sum} summarize; "
              f"story {rows[-1]['selected_story_tokens']} token", flush=True)

    doc = {
        "capture": "selection",
        "model": settings.context_selection.model,
        "hide_below": settings.context_selection.hide_below,
        "summarize_below": settings.context_selection.summarize_below,
        "min_confidence": settings.context_selection.min_confidence,
        "summarizer_endpoint": settings.context_selection.summarizer_endpoint,
        "token_method": TOKEN_METHOD,
        "examples": rows,
    }
    CAPTURE_PATH.write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"Selection capture: {CAPTURE_PATH}")


# ---------------------------------------------------------------------------
# capture-generations: cikkgenerálás a válogatott kontextussal (LASSÚ)
# ---------------------------------------------------------------------------

def cmd_capture_generations() -> None:
    import dspy

    from eval.dataset import load_gold_dataset
    from snow_kb.program import StoryToKBArticle

    capture = json.loads(CAPTURE_PATH.read_text(encoding="utf-8"))
    trainset, valset = load_gold_dataset(DATASET_PATH)
    gold_by_id = {f"gold-{i+1}": ex for i, ex in enumerate(trainset + valset)}

    _configure_lm()
    program = StoryToKBArticle()

    rows = []
    examples = capture["examples"]
    for idx, row in enumerate(examples, 1):
        ex_id = row["id"]
        gold = gold_by_id[ex_id]
        print(f"[{idx}/{len(examples)}] {ex_id} generálás (válogatott)...", flush=True)
        with dspy.context(cache=False):
            pred = program(
                story_text=row["selected_story_text"],
                update_set_payloads=row["selected_update_set_payloads"],
                template_context=gold.template_context,
                related_articles_context=row["selected_related_articles_context"],
                category="General",
                knowledge_base_id="measurement",
            )
        usage = {}
        try:
            lm_usage = pred.get_lm_usage() or {}
            for _model, u in lm_usage.items():
                usage = {
                    "prompt_tokens": u.get("prompt_tokens"),
                    "completion_tokens": u.get("completion_tokens"),
                    "total_tokens": u.get("total_tokens"),
                }
        except Exception as exc:  # noqa: BLE001
            usage = {"usage_error": f"{type(exc).__name__}: {exc}"}
        rows.append({
            "id": ex_id,
            "generated_html": pred.article.html,
            "usage": usage,
        })
        print(f"  kész: usage={usage}", flush=True)

    doc = {
        "capture": "generations-selected",
        "model": TASK_MODEL,
        "api_base": API_BASE,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "cache": False,
        "examples": rows,
    }
    SEL_GENS_PATH.write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"Válogatott generálások: {SEL_GENS_PATH}")


def cmd_capture_metrics() -> None:
    """rich_metric a válogatott generálásokon (a baseline-val azonos judge-LM)."""
    capture_metrics_for(SEL_GENS_PATH, SEL_METRICS_PATH)


# ---------------------------------------------------------------------------
# report: TISZTA replay (determinisztikus, SC-005)
# ---------------------------------------------------------------------------

def _paired_bootstrap_ci(deltas: list[float], *, samples: int = 2000,
                         seed: int = 42) -> tuple[float, float]:
    """Párosított bootstrap 95%-os CI a delta-átlagra (fix seed → determinisztikus).

    A 013/014-es „nem-átfedő zaj-intervallum" szabály konkrét megfelelője:
    a minőség-romlás csak akkor „valós" (a zaj-sávon túli), ha a teljes CI
    0 alatt van.
    """
    import random

    rng = random.Random(seed)
    n = len(deltas)
    means = []
    for _ in range(samples):
        sample = [deltas[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(0.025 * samples)]
    hi = means[min(samples - 1, int(0.975 * samples))]
    return lo, hi


def build_report() -> dict:
    baseline_gens = json.loads(BASELINE_GENS_PATH.read_text(encoding="utf-8"))
    baseline_tokens = json.loads(BASELINE_TOKENS_PATH.read_text(encoding="utf-8"))
    baseline_metrics = json.loads(BASELINE_METRICS_PATH.read_text(encoding="utf-8"))
    capture = json.loads(CAPTURE_PATH.read_text(encoding="utf-8"))
    sel_gens = json.loads(SEL_GENS_PATH.read_text(encoding="utf-8"))
    sel_metrics = json.loads(SEL_METRICS_PATH.read_text(encoding="utf-8"))

    baseline_score_by_id = {r["id"]: float(r["score"]) for r in baseline_metrics["examples"]}
    sel_score_by_id = {r["id"]: float(r["score"]) for r in sel_metrics["examples"]}
    all_ids = sorted(baseline_score_by_id, key=lambda x: int(x.split("-")[1]))
    baseline_by_id = {r["id"]: r for r in baseline_gens["examples"]}
    baseline_tok_by_id = {r["id"]: r for r in baseline_tokens["examples"]}
    capture_by_id = {r["id"]: r for r in capture["examples"]}
    sel_gen_by_id = {r["id"]: r for r in sel_gens["examples"]}

    per_example = []
    deltas: list[float] = []
    for ex_id in all_ids:
        base = baseline_by_id[ex_id]
        base_tok = baseline_tok_by_id[ex_id]
        cap = capture_by_id[ex_id]
        sel = sel_gen_by_id[ex_id]

        baseline_ctx_tokens = sum(p["tokens"] for p in base_tok["pieces"])
        selected_ctx_tokens = cap["selected_story_tokens"] + cap["selected_update_set_tokens"]

        score_before = baseline_score_by_id[ex_id]
        score_after = sel_score_by_id[ex_id]
        deltas.append(score_after - score_before)

        verdicts = [p["verdict"] for p in cap["pieces"]]
        per_example.append({
            "id": ex_id,
            "baseline_context_tokens": baseline_ctx_tokens,
            "selected_context_tokens": selected_ctx_tokens,
            "context_token_delta": selected_ctx_tokens - baseline_ctx_tokens,
            "baseline_prompt_usage": base.get("usage", {}).get("prompt_tokens"),
            "selected_prompt_usage": sel.get("usage", {}).get("prompt_tokens"),
            "rich_metric_before": round(score_before, 4),
            "rich_metric_after": round(score_after, 4),
            "rich_metric_delta": round(score_after - score_before, 4),
            "verdicts": {
                "hide": verdicts.count("hide"),
                "summarize": verdicts.count("summarize"),
                "show": verdicts.count("show"),
            },
        })

    n = len(per_example)
    total_base = sum(r["baseline_context_tokens"] for r in per_example)
    total_sel = sum(r["selected_context_tokens"] for r in per_example)
    avg_before = sum(r["rich_metric_before"] for r in per_example) / n
    avg_after = sum(r["rich_metric_after"] for r in per_example) / n
    ci_lo, ci_hi = _paired_bootstrap_ci(deltas)
    not_worse = ci_hi >= 0.0  # a romlás csak akkor „valós", ha a CI 0 alatt van

    base_prompt = [r["baseline_prompt_usage"] for r in per_example if r["baseline_prompt_usage"]]
    sel_prompt = [r["selected_prompt_usage"] for r in per_example if r["selected_prompt_usage"]]

    return {
        "spec": "016-context-selection / T007 hatásmérés",
        "selection": {
            "model": capture["model"],
            "hide_below": capture["hide_below"],
            "summarize_below": capture["summarize_below"],
            "min_confidence": capture["min_confidence"],
            "summarizer_endpoint": capture["summarizer_endpoint"],
        },
        "token_method": TOKEN_METHOD,
        "generation": {"model": TASK_MODEL, "temperature": TEMPERATURE,
                       "max_tokens": MAX_TOKENS, "cache": False},
        "n_examples": n,
        "token_delta": {
            "baseline_context_tokens": total_base,
            "selected_context_tokens": total_sel,
            "delta": total_sel - total_base,
            "reduction_ratio": round(1 - total_sel / total_base, 4) if total_base else 0.0,
            "baseline_prompt_usage_sum": sum(base_prompt) if base_prompt else None,
            "selected_prompt_usage_sum": sum(sel_prompt) if sel_prompt else None,
        },
        "quality_delta": {
            "rich_metric_avg_before": round(avg_before, 4),
            "rich_metric_avg_after": round(avg_after, 4),
            "avg_delta": round(avg_after - avg_before, 4),
            "paired_bootstrap_ci95": [round(ci_lo, 4), round(ci_hi, 4)],
            "not_worse_beyond_noise": not_worse,
            "rule": "SC-002: a romlás csak akkor valós, ha a párosított "
                    "bootstrap CI95 teljes egészében 0 alatt van "
                    "(a 013/014-es nem-átfedő-intervallum szabály).",
        },
        "per_example": per_example,
        "notes": [
            "A baseline és a válogatott futás UGYANAZZAL a modellel, "
            "LM-beállításokkal és token-módszerrel készült (tasks.md T002).",
            "A riport TISZTA replay a capture-fájlokból — kétszeri futtatás "
            "byte-identikus (SC-005).",
            "A selected_context_tokens a válogatás UTÁNI story+update set "
            "tokenek; a summarize-költség (lokális endpoint) nincs benne — "
            "a summarize darabok a capture-fájlban jelölve.",
        ],
    }


def cmd_report() -> None:
    report = build_report()
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    td = report["token_delta"]
    qd = report["quality_delta"]
    print(f"Hatásmérés riport: {REPORT_PATH}")
    print(f"  kontextus-token: {td['baseline_context_tokens']} → "
          f"{td['selected_context_tokens']} ({td['reduction_ratio']:.1%} csökkenés)")
    print(f"  rich_metric: {qd['rich_metric_avg_before']} → "
          f"{qd['rich_metric_avg_after']} (CI95 {qd['paired_bootstrap_ci95']}, "
          f"nem rosszabb: {qd['not_worse_beyond_noise']})")


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    cmds = ("capture-selection", "capture-generations", "capture-metrics", "report")
    if not argv or argv[0] not in cmds:
        print(__doc__)
        sys.exit(2)
    if argv[0] == "capture-selection":
        cmd_capture_selection()
    elif argv[0] == "capture-generations":
        cmd_capture_generations()
    elif argv[0] == "capture-metrics":
        cmd_capture_metrics()
    else:
        cmd_report()


if __name__ == "__main__":
    main()
