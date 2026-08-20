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
            # T010c / FR-007: a rich_metric az axes-t is a Predictionbe teszi
            axes = metric_output.get("axes")
        else:
            score = float(metric_output)
            feedback = ""
            axes = None
        scores.append(score)
        entry = {"score": score, "feedback": feedback}
        if axes:
            entry["axes"] = {k: float(v) for k, v in axes.items()}
        per_example.append(entry)

    average_score = sum(scores) / len(scores) if scores else 0.0

    # T010c / FR-007: tengelyenkénti átlagok — a T012 style-küszöb ezekre hivatkozik
    axis_averages = {}
    axis_names = ["structure", "content", "template", "hallucination", "style"]
    for name in axis_names:
        vals = [e["axes"][name] for e in per_example if e.get("axes") and name in e["axes"]]
        if vals:
            axis_averages[name] = sum(vals) / len(vals)

    baseline_data = {
        "average_score": average_score,
        "axis_averages": axis_averages,
        "per_example": per_example,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(baseline_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # A dspy.Evaluate százalékos (0-100) score-t ad; a spec és a tesztek 0-1 skálát várnak.
    return EvaluationResult(score=average_score, results=result.results)


def configure_kimi_lm():
    """Globálisan konfigurálja a DSPy LM-et Kimi K3-ra (tiszta méréshez, cache=False)."""
    import dspy

    from eval.gepa_optimize import _RefreshingKimiLM

    lm = _RefreshingKimiLM(
        "openai/k3",
        api_key="",  # a _RefreshingKimiLM minden hívásnál frissíti az auth.json-ból
        api_base="https://api.kimi.com/coding/v1",
        temperature=1.0,  # a K3 csak temperature=1-et fogad el
        max_tokens=8000,
        cache=False,
    )
    dspy.configure(lm=lm, track_usage=True)


def main(argv: list[str] | None = None) -> None:
    """CLI belépési pont: python -m eval.baseline --model local|kimi [--output ...]."""
    import argparse

    parser = argparse.ArgumentParser(description="Baseline mérés a StoryToKBArticle programmal.")
    parser.add_argument("--model", default="local", choices=["local", "kimi"],
                        help="Task modell: local (Qwen, llama.cpp) vagy kimi (K3).")
    parser.add_argument("--dataset", default="data/examples/gold_dataset.md")
    parser.add_argument("--output", default="runs/baseline.json")
    args = parser.parse_args(argv)

    from eval.dataset import load_gold_dataset
    from snow_kb.program import StoryToKBArticle

    trainset, valset = load_gold_dataset(args.dataset)
    print(f"Dataset: {len(trainset)} train / {len(valset)} val példa")

    if args.model == "kimi":
        # A run_baseline a modul-globális configure_lm-et hívja — Kimi-nél lecseréljük.
        import eval.baseline as _self

        _self.configure_lm = configure_kimi_lm

    result = run_baseline(StoryToKBArticle(), valset, output_path=args.output)
    print(f"\nBaseline ({args.model}) átlag score: {result.score:.3f} → {args.output}")


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
        r"openai/models\Qwen3.8-27B-UD-Q4_K_M.gguf",  # 2026-08-12: modellcsere (llama.cpp amúgy is a betöltött modellt szolgálja, a név csak azonosító)
        api_key=api_key,
        api_base=api_base,
        temperature=0.6,
        max_tokens=8000,
        # A mérés ne a ~/.dspy_cache-ből jöjjön (különben egy korábbi,
        # más modellel készült futás eredményét játssza vissza — lásd
        # a 2026-07-29-i fals 0.655-ös lokális baseline-t).
        cache=False,
    )
    dspy.configure(lm=lm, track_usage=True)


if __name__ == "__main__":
    main()
