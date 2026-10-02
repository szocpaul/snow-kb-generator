"""eval/context_baseline.py — spec 016 T002: baseline-mérés (Phase 0).

A gold példák kontextusának darabolása + per-darab token-leltár + rich_metric
baseline ÚJRAMÉRVE cache=False-szal, DEV MÓDBAN (lokális Qwen) — az after-mérés
(T007) UGYANEZZEL a modellel és UGYANEZZEL a token-számlálási módszerrel fut
(tasks.md T002 részletszabályok).

Token-számlálás: a lokális llama.cpp szerver /tokenize endpointja (a Qwen3.8-27B
valódi tokenizere). A módszer a riportban jelölve; a T007 after-mérésnek
UGYANEZZEL kell dolgoznia.

Capture/report szétválasztás (a 015-ös minta):
    SNOW_KB_DEV_MODE=1 python -m eval.context_baseline capture-generations
        # élő generálás a 9 gold példán (LASSÚ, lokális Qwen, cache=False)
    python -m eval.context_baseline capture-tokens
        # darabolás + /tokenize hívások (élő endpoint kell)
    python -m eval.context_baseline report
        # TISZTA replay: a capture-fájlokból számol, byte-identikus riport

Kimenetek:
    artifacts/context_baseline_generations.json  (capture: nyers generálások)
    artifacts/context_baseline_tokens.json       (capture: per-darab tokenek)
    artifacts/context_baseline.json              (report: a T003 kapu alapja)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

GENERATIONS_PATH = Path("artifacts/context_baseline_generations.json")
TOKENS_PATH = Path("artifacts/context_baseline_tokens.json")
REPORT_PATH = Path("artifacts/context_baseline.json")

DATASET_PATH = Path("data/examples/gold_dataset.md")

# A task-modell és LM-beállítások — a T007 after-mérésnek UGYANEZEKKEL kell futnia.
TASK_MODEL = r"openai/models\Qwen3.8-27B-UD-Q4_K_M.gguf"
API_BASE = "http://desktop-c5ikame-1.tailee6bc1.ts.net:8033/v1"
TOKENIZE_URL = "http://desktop-c5ikame-1.tailee6bc1.ts.net:8033/tokenize"
TEMPERATURE = 0.6
MAX_TOKENS = 8000

TOKEN_METHOD = "llama.cpp /tokenize (Qwen3.8-27B-UD-Q4_K_M.gguf, valódi tokenizer)"


def _configure_lm():
    """Lokális Qwen task LM, cache=False (a 2026-08-20 baseline_qwen38 minta)."""
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
# capture-generations: a 9 gold példa generálása (LASSÚ, élő LLM)
# ---------------------------------------------------------------------------

def cmd_capture_generations() -> None:
    import dspy

    from eval.dataset import load_gold_dataset
    from snow_kb.program import StoryToKBArticle

    trainset, valset = load_gold_dataset(DATASET_PATH)
    examples = trainset + valset
    print(f"{len(examples)} gold példa generálása (lokális Qwen, cache=False)...")

    _configure_lm()
    program = StoryToKBArticle()

    rows = []
    for idx, ex in enumerate(examples, 1):
        print(f"[{idx}/{len(examples)}] generálás...", flush=True)
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
        except Exception as exc:  # noqa: BLE001 — a usage opcionális
            usage = {"usage_error": f"{type(exc).__name__}: {exc}"}
        rows.append({
            "id": f"gold-{idx}",
            "story_text": ex.story_text,
            "update_set_payloads": getattr(ex, "update_set_payloads", "") or "",
            "generated_html": article.html,
            "usage": usage,
        })
        print(f"  kész: {len(article.html)} karakter html, usage={usage}", flush=True)

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
    print(f"Generálások elmentve: {GENERATIONS_PATH}")


# ---------------------------------------------------------------------------
# capture-tokens: darabolás + per-darab token-leltár (élő /tokenize endpoint)
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
    print(f"Token-leltár elmentve: {TOKENS_PATH}")


# ---------------------------------------------------------------------------
# report: TISZTA replay a capture-fájlokból (determinisztikus)
# ---------------------------------------------------------------------------

def _noise_heuristic(piece: dict) -> str:
    """Determinisztikus zaj-jelölt heurisztika (a T003 kapu review-jához).

    NEM döntés — csak jelölés. A valódi zaj-arány a kalibrált válogatás
    dolga lesz; itt a nyilvánvaló eseteket gyűjtjük:
      - story meta-mezők (state, assigned_to stb.): nem tartalom
      - üres / ~üres darabok
      - related_article sorok (a gold példákban nincs — jelölve)
    """
    if piece["source_type"] == "story_meta":
        return "metadata-field"
    if piece["char_len"] < 40:
        return "near-empty"
    return ""


def build_report(gens_doc: dict, tokens_doc: dict) -> dict:
    from eval.dataset import load_gold_dataset
    from eval.metric import rich_metric

    trainset, valset = load_gold_dataset(DATASET_PATH)
    gold_by_id = {f"gold-{i+1}": ex for i, ex in enumerate(trainset + valset)}

    per_example = []
    total_context_tokens = 0
    total_noise_tokens = 0
    scores = []
    for gen_row, tok_row in zip(gens_doc["examples"], tokens_doc["examples"]):
        assert gen_row["id"] == tok_row["id"], "capture-fájlok sorszáma eltér"
        ex_id = gen_row["id"]
        gold = gold_by_id[ex_id]
        pred = type("P", (), {"html": gen_row["generated_html"], "article": None})()
        metric_out = rich_metric(gold, pred)
        score = float(metric_out.score)
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
            "A baseline DEV-MÓDÚ lokális Qwennel készült; az after-mérés (T007) "
            "ugyanezzel a modellel és token-módszerrel fut (tasks.md T002).",
            "A noise_hint determinisztikus heurisztika (metadata-mező, near-empty) "
            "— NEM kalibrált döntés; a T003 kapu review-ja dönt az SC-001 "
            "célértékről.",
            "A gold példákban related_articles_context nincs (a gold dataset "
            "nem tartalmaz ilyet) — a kapcsolódó-cikk zaj a prod kontextusban "
            "jelenik meg, a baseline nem méri.",
            "Update set payload csak a gold-5 példában van.",
        ],
    }


def cmd_report() -> None:
    gens_doc = json.loads(GENERATIONS_PATH.read_text(encoding="utf-8"))
    tokens_doc = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
    report = build_report(gens_doc, tokens_doc)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Baseline riport: {REPORT_PATH}")
    print(f"  rich_metric átlag: {report['rich_metric_baseline_avg']}")
    print(f"  összes kontextus-token: {report['total_context_tokens']}")
    print(f"  zaj-jelölt token: {report['total_noise_hint_tokens']} "
          f"({report['noise_hint_ratio']:.1%})")


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] not in ("capture-generations", "capture-tokens", "report"):
        print(__doc__)
        sys.exit(2)
    if argv[0] == "capture-generations":
        cmd_capture_generations()
    elif argv[0] == "capture-tokens":
        cmd_capture_tokens()
    else:
        cmd_report()


if __name__ == "__main__":
    main()
