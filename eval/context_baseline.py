"""eval/context_baseline.py — spec 016 T002: the baseline measurement (Phase 0).

Chunking the context of the gold examples + a per piece token inventory + the rich_metric
baseline RE-MEASURED with cache=False, in DEV MODE (local Qwen) — the after measurement
(T007) runs with the SAME model and the SAME token counting method
(the detailed rules of tasks.md T002).

Token counting: the /tokenize endpoint of the local llama.cpp server (the real tokenizer of
Qwen3.8-27B). The method is marked in the report; the T007 after measurement
It must work with exactly the same.

Capture/report separation (the 015 pattern):
    SNOW_KB_DEV_MODE=1 python -m eval.context_baseline capture-generations
        # live generation on the 9 gold examples (SLOW, local Qwen, cache=False)
    python -m eval.context_baseline capture-tokens
        # chunking + /tokenize calls (a live endpoint is required)
    SNOW_KB_DEV_MODE=1 python -m eval.context_baseline capture-metrics
        # live: rich_metric (it calls the style judge LM) on the stored generations
    python -m eval.context_baseline report
        # PURE replay: computed from the capture files, byte-identical report

Kimenetek:
    artifacts/context_baseline_generations.json  (capture: the raw generations)
    artifacts/context_baseline_tokens.json       (capture: per-darab tokenek)
    artifacts/context_baseline.json              (report: a T003 kapu alapja)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

GENERATIONS_PATH = Path("artifacts/context_baseline_generations.json")
TOKENS_PATH = Path("artifacts/context_baseline_tokens.json")
METRICS_PATH = Path("artifacts/context_baseline_metrics.json")
REPORT_PATH = Path("artifacts/context_baseline.json")

DATASET_PATH = Path("data/examples/gold_dataset.md")

# The task model and the LM settings — the T007 after measurement must run with THE SAME.
TASK_MODEL = r"openai/models\Qwen3.8-27B-UD-Q4_K_M.gguf"
API_BASE = "http://llm-server.local:8033/v1"
TOKENIZE_URL = "http://llm-server.local:8033/tokenize"
TEMPERATURE = 0.6
MAX_TOKENS = 8000

TOKEN_METHOD = "llama.cpp /tokenize (Qwen3.8-27B-UD-Q4_K_M.gguf, real tokenizer)"


def _configure_lm():
    """The local Qwen task LM, cache=False (the 2026-08-20 baseline_qwen38 sample)."""
    import dspy

    lm = dspy.LM(
        TASK_MODEL,
        api_key="not-needed",
        api_base=API_BASE,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        cache=False,
    )
    dspy.configure(lm=lm, track_usage=True)


# ---------------------------------------------------------------------------
# capture-generations: the generation of the 9 gold examples (SLOW, live LLM)
# ---------------------------------------------------------------------------

def cmd_capture_generations() -> None:
    import dspy

    from eval.dataset import load_gold_dataset
    from snow_kb.program import StoryToKBArticle

    trainset, valset = load_gold_dataset(DATASET_PATH)
    examples = trainset + valset
    print(f"generating {len(examples)} gold examples (local Qwen, cache=False)...")

    _configure_lm()
    program = StoryToKBArticle()

    rows = []
    for idx, ex in enumerate(examples, 1):
        print(f"[{idx}/{len(examples)}] generating...", flush=True)
        with dspy.context(cache=False):
            pred = program(
                story_text=ex.story_text,
                update_set_payloads=getattr(ex, "update_set_payloads", "") or "",
                template_context=ex.template_context,
                related_articles_context="",
                category="General",
                knowledge_base_id="baseline",
            )
        article = pred.article
        usage = {}
        try:
            lm_usage = pred.get_lm_usage() or {}
            for _model, u in lm_usage.items():
                usage = {
                    "prompt_tokens": u.get("prompt_tokens"),
                    "completion_tokens": u.get("completion_tokens"),
                    "total_tokens": u.get("total_tokens"),
                }
        except Exception as exc:  # noqa: BLE001 — the usage is optional
            usage = {"usage_error": f"{type(exc).__name__}: {exc}"}
        rows.append({
            "id": f"gold-{idx}",
            "story_text": ex.story_text,
            "update_set_payloads": getattr(ex, "update_set_payloads", "") or "",
            "generated_html": article.html,
            "usage": usage,
        })
        print(f"  done: {len(article.html)} characters of html, usage={usage}", flush=True)

    doc = {
        "capture": "generations",
        "model": TASK_MODEL,
        "api_base": API_BASE,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "cache": False,
        "examples": rows,
    }
    GENERATIONS_PATH.write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"Generations saved: {GENERATIONS_PATH}")


# ---------------------------------------------------------------------------
# capture-tokens: chunking + a per piece token inventory (live /tokenize endpoint)
# ---------------------------------------------------------------------------

def _count_tokens(text: str) -> int:
    import requests

    resp = requests.post(TOKENIZE_URL, json={"content": text}, timeout=60)
    resp.raise_for_status()
    return len(resp.json()["tokens"])


def cmd_capture_tokens() -> None:
    from snow_kb.context_selection import split_context_into_pieces

    gens = json.loads(GENERATIONS_PATH.read_text(encoding="utf-8"))["examples"]
    rows = []
    for ex in gens:
        pieces = split_context_into_pieces(
            story_text=ex["story_text"],
            update_set_payloads=ex["update_set_payloads"],
            related_articles_context="",
        )
        piece_rows = []
        for piece in pieces:
            n = _count_tokens(piece.text)
            piece_rows.append({
                "piece_id": piece.piece_id,
                "source_type": piece.source_type,
                "label": piece.label,
                "char_len": len(piece.text),
                "tokens": n,
            })
            print(f"  {ex['id']} {piece.piece_id}: {n} token", flush=True)
        rows.append({"id": ex["id"], "pieces": piece_rows})

    doc = {
        "capture": "tokens",
        "token_method": TOKEN_METHOD,
        "examples": rows,
    }
    TOKENS_PATH.write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"Token inventory saved: {TOKENS_PATH}")


# ---------------------------------------------------------------------------
# capture-metrics: rich_metric on the stored generations (live LM for the style judge)
# ---------------------------------------------------------------------------

def capture_metrics_for(gens_path: Path, out_path: Path) -> None:
    """rich_metric (together with the style judge) on the stored generations.

    rich_metric is NOT a pure function (it calls the style judge LM) — therefore the
    metric is made at CAPTURE time, and the report only reads the stored points
    (so the report stays a PURE replay, SC-005). The baseline and the after measurement
    have their metric made with the SAME judge LM (local Qwen).
    """
    from eval.dataset import load_gold_dataset
    from eval.metric import rich_metric

    gens = json.loads(gens_path.read_text(encoding="utf-8"))["examples"]
    trainset, valset = load_gold_dataset(DATASET_PATH)
    gold_by_id = {f"gold-{i+1}": ex for i, ex in enumerate(trainset + valset)}

    _configure_lm()
    rows = []
    for ex in gens:
        ex_id = ex["id"]
        print(f"[{ex_id}] rich_metric (style judge: 3 samples)...", flush=True)
        pred = type("P", (), {"html": ex["generated_html"], "article": None})()
        out = rich_metric(gold_by_id[ex_id], pred)
        rows.append({
            "id": ex_id,
            "score": float(out.score),
            "feedback": str(out.feedback),
        })
        print(f"  score={float(out.score):.4f}", flush=True)
    doc = {"capture": "metrics", "judge_lm": TASK_MODEL,
           "examples": rows}
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    print(f"Metrics saved: {out_path}")


def cmd_capture_metrics() -> None:
    capture_metrics_for(GENERATIONS_PATH, METRICS_PATH)


# ---------------------------------------------------------------------------
# report: a PURE replay from the capture files (deterministic)
# ---------------------------------------------------------------------------

def _noise_heuristic(piece: dict) -> str:
    """A deterministic noise candidate heuristic (for the review of the T003 gate).

    It is NOT a decision — only a marker. The real noise ratio is the job of the calibrated selection;
    here we only collect the obvious cases:
      - story meta fields (state, assigned_to etc.): not content
      - empty / ~empty pieces
      - related_article lines (not in the gold examples — marked)
    """
    if piece["source_type"] == "story_meta":
        return "metadata-field"
    if piece["char_len"] < 40:
        return "near-empty"
    return ""


def build_report(gens_doc: dict, tokens_doc: dict,
                 metrics_doc: dict | None = None) -> dict:
    if metrics_doc is None:
        metrics_doc = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    score_by_id = {r["id"]: float(r["score"]) for r in metrics_doc["examples"]}

    per_example = []
    total_context_tokens = 0
    total_noise_tokens = 0
    scores = []
    for gen_row, tok_row in zip(gens_doc["examples"], tokens_doc["examples"]):
        assert gen_row["id"] == tok_row["id"], "the row order of the capture files differs"
        ex_id = gen_row["id"]
        score = score_by_id[ex_id]
        scores.append(score)

        pieces = []
        ctx_tokens = 0
        noise_tokens = 0
        for p in tok_row["pieces"]:
            reason = _noise_heuristic(p)
            ctx_tokens += p["tokens"]
            if reason:
                noise_tokens += p["tokens"]
            pieces.append({**p, "noise_hint": reason})
        total_context_tokens += ctx_tokens
        total_noise_tokens += noise_tokens
        per_example.append({
            "id": ex_id,
            "rich_metric_score": round(score, 4),
            "context_tokens": ctx_tokens,
            "noise_hint_tokens": noise_tokens,
            "usage": gen_row.get("usage", {}),
            "pieces": pieces,
        })

    n = len(per_example)
    return {
        "spec": "016-context-selection / T002 baseline",
        "model": gens_doc["model"],
        "api_base": gens_doc["api_base"],
        "temperature": gens_doc["temperature"],
        "max_tokens": gens_doc["max_tokens"],
        "cache": gens_doc["cache"],
        "token_method": tokens_doc["token_method"],
        "n_examples": n,
        "rich_metric_baseline_avg": round(sum(scores) / n, 4),
        "rich_metric_baseline_scores": [round(s, 4) for s in scores],
        "total_context_tokens": total_context_tokens,
        "total_noise_hint_tokens": total_noise_tokens,
        "noise_hint_ratio": round(total_noise_tokens / total_context_tokens, 4)
        if total_context_tokens else 0.0,
        "per_example": per_example,
        "notes": [
            "The baseline was made in DEV MODE with the local Qwen; the after measurement (T007) "
            "runs with the same model and token method (tasks.md T002).",
            "The noise_hint is a deterministic heuristic (metadata field, near-empty) "
            "— NOT a calibrated decision; the review of the T003 gate decides on the SC-001 "
            "target value.",
            "There is no related_articles_context in the gold examples (the gold dataset "
            "does not contain such) — the related article noise appears in the production context "
            "and the baseline does not measure it.",
            "The update set payload is only in the gold-5 example.",
        ],
    }


def cmd_report() -> None:
    gens_doc = json.loads(GENERATIONS_PATH.read_text(encoding="utf-8"))
    tokens_doc = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
    metrics_doc = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    report = build_report(gens_doc, tokens_doc, metrics_doc)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Baseline riport: {REPORT_PATH}")
    print(f"  rich_metric average: {report['rich_metric_baseline_avg']}")
    print(f"  total context tokens: {report['total_context_tokens']}")
    print(f"  noise candidate tokens: {report['total_noise_hint_tokens']} "
          f"({report['noise_hint_ratio']:.1%})")


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    cmds = ("capture-generations", "capture-tokens", "capture-metrics", "report")
    if not argv or argv[0] not in cmds:
        print(__doc__)
        sys.exit(2)
    if argv[0] == "capture-generations":
        cmd_capture_generations()
    elif argv[0] == "capture-tokens":
        cmd_capture_tokens()
    elif argv[0] == "capture-metrics":
        cmd_capture_metrics()
    else:
        cmd_report()


if __name__ == "__main__":
    main()
