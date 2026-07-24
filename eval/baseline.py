"""baseline.py — Baseline mérés a jelenlegi (nem optimalizált) program teljesítményéről.

Lefuttatja a jelenlegi StoryToKBArticle programot a valset-en, és elmenti az eredményeket
a runs/baseline.json fájlba (average_score, timestamp).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import dspy
from dspy.evaluate.evaluate import EvaluationResult

from eval.metric import rich_metric


def run_baseline(program, valset, output_path: str | Path = "runs/baseline.json"):
    """Lefuttatja a baseline mérést a jelenlegi programon a valset-en.

    Args:
        program: A jelenlegi (nem optimalizált) dspy.Module (StoryToKBArticle).
        valset: A valset (2 dspy.Example objektum).
        output_path: A kimeneti JSON fájl útvonala (alapértelmezett: runs/baseline.json).

    Returns:
        dspy.Evaluate result (átlagos score + timestamp).
    """
    # LM konfigurálása (globálisan, ahogy a skill szerint)
    configure_lm()

    # dspy.Evaluate létrehozása a valset-en.
    # FONTOS: nincs save_as_json — a rich_metric dspy.Prediction(score, feedback)-et
    # ad vissza (GEPA contract), és a dspy.Evaluate save_as_json implementációja
    # json.dump-ot hív a nyers metric-kimenetre, ami TypeError-t dob Predictionre.
    evaluator = dspy.Evaluate(
        devset=valset,
        metric=rich_metric,
        num_threads=1,
        display_progress=False,
        provide_traceback=True,
    )

    result = evaluator(program)

    # A result.results (example, prediction, metric_output) tuple-kben a metric_output
    # dspy.Prediction — ebből nyerjük ki a float score-t és a feedback szöveget,
    # így a saját JSON-unk garantáltan szerializálható.
    per_example = []
    scores = []
    for _example, _prediction, metric_output in result.results:
        if isinstance(metric_output, dspy.Prediction):
            score = float(metric_output.score)
            feedback = str(metric_output.feedback)
        else:
            score = float(metric_output)
            feedback = ""
        scores.append(score)
        per_example.append({"score": score, "feedback": feedback})

    average_score = sum(scores) / len(scores) if scores else 0.0

    baseline_data = {
        "average_score": average_score,
        "per_example": per_example,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(baseline_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # A dspy.Evaluate százalékos (0-100) score-t ad; a spec és a tesztek 0-1 skálát várnak.
    return EvaluationResult(score=average_score, results=result.results)


def configure_lm():
    """Globálisan konfigurálja a DSPy LM-et a settings-ből (Qwen task LM)."""
    import json
    import os
    from pathlib import Path

    import dspy

    # A Pi Agent auth fájl olvasása (Qwen endpoint)
    pi_auth_path = Path.home() / ".pi" / "agent" / "auth.json"
    auth_data = json.loads(pi_auth_path.read_text(encoding="utf-8"))

    # A Qwen endpoint Tailscale serve-en keresztül
    api_key = auth_data.get("zai-glm", {}).get("key") or auth_data.get("kimi-coding", {}).get("apiKey") or auth_data.get("openai-codex", {}).get("access")
    api_base = "http://desktop-c5ikame-1.tailee6bc1.ts.net:8033/v1"

    lm = dspy.LM(
        "openai/Qwen3.6-35B-A3B-NSC-ACE-SABER-Q4_K_M.gguf",
        api_key=api_key,
        api_base=api_base,
        temperature=0.6,
        max_tokens=8000,
    )
    dspy.configure(lm=lm, track_usage=True)
