"""baseline.py — Baseline measurement of the performance of the current (not optimized) program.

It runs the current StoryToKBArticle program on the valset and saves the results
to the runs/baseline.json file (average_score, timestamp).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import dspy
from dspy.evaluate.evaluate import EvaluationResult

from eval.metric import rich_metric


def run_baseline(program, valset, output_path: str | Path = "runs/baseline.json"):
    """Runs the baseline measurement with the current program on the valset.

    Args:
        program: the current (not optimized) dspy.Module (StoryToKBArticle).
        valset: A valset (2 dspy.Example objektum).
        output_path: the path of the output JSON file (default: runs/baseline.json).

    Returns:
        dspy.Evaluate result (the average score + timestamp).
    """
    # LM configuration (globally, as the skill says)
    configure_lm()

    # Creating the dspy.Evaluate on the valset.
    # IMPORTANT: there is no save_as_json — the rich_metric returns a dspy.Prediction(score, feedback)
    # returns (the GEPA contract), and the save_as_json implementation of dspy.Evaluate
    # calls json.dump on the raw metric output, which raises a TypeError for a Prediction.
    evaluator = dspy.Evaluate(
        devset=valset,
        metric=rich_metric,
        num_threads=1,
        display_progress=False,
        provide_traceback=True,
    )

    result = evaluator(program)

    # A result.results (example, prediction, metric_output) tuple-kben a metric_output
    # dspy.Prediction — from this we take the float score and the feedback text,
    # so that our own JSON is guaranteed to be serializable.
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

    # T010c / FR-007: the axis averages — the T012 style threshold refers to these
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

    # dspy.Evaluate gives a percentage (0-100) score; the spec and the tests expect a 0-1 scale.
    return EvaluationResult(score=average_score, results=result.results)


def configure_kimi_lm():
    """Configures the DSPy LM globally for Kimi K3 (for a clean measurement, cache=False)."""
    import dspy

    from eval.gepa_optimize import _RefreshingKimiLM

    lm = _RefreshingKimiLM(
        "openai/k3",
        api_key="",  # the _RefreshingKimiLM refreshes it from the auth.json on every call
        api_base="https://api.kimi.com/coding/v1",
        temperature=1.0,  # K3 only accepts temperature=1
        max_tokens=8000,
        cache=False,
    )
    dspy.configure(lm=lm, track_usage=True)


def main(argv: list[str] | None = None) -> None:
    """The CLI entry point: python -m eval.baseline --model local|kimi [--output ...]."""
    import argparse

    parser = argparse.ArgumentParser(description="Baseline measurement with the StoryToKBArticle program.")
    parser.add_argument("--model", default="local", choices=["local", "kimi"],
                        help="Task model: local (Qwen, llama.cpp) or kimi (K3).")
    parser.add_argument("--dataset", default="data/examples/gold_dataset.md")
    parser.add_argument("--output", default="runs/baseline.json")
    args = parser.parse_args(argv)

    from eval.dataset import load_gold_dataset
    from snow_kb.program import StoryToKBArticle

    trainset, valset = load_gold_dataset(args.dataset)
    print(f"Dataset: {len(trainset)} train / {len(valset)} val examples")

    if args.model == "kimi":
        # run_baseline calls the module-global configure_lm — for Kimi we replace it.
        import eval.baseline as _self

        _self.configure_lm = configure_kimi_lm

    result = run_baseline(StoryToKBArticle(), valset, output_path=args.output)
    print(f"\nBaseline ({args.model}) average score: {result.score:.3f} → {args.output}")


def configure_lm():
    """Configures the DSPy LM globally from the settings (Qwen task LM)."""
    import json
    import os
    from pathlib import Path

    import dspy

    # Reading the Pi Agent auth file (Qwen endpoint)
    pi_auth_path = Path.home() / ".pi" / "agent" / "auth.json"
    auth_data = json.loads(pi_auth_path.read_text(encoding="utf-8"))

    # The Qwen endpoint through the Tailscale serve
    api_key = auth_data.get("zai-glm", {}).get("key") or auth_data.get("kimi-coding", {}).get("apiKey") or auth_data.get("openai-codex", {}).get("access")
    api_base = "http://llm-server.local:8033/v1"

    lm = dspy.LM(
        "openai/Qwen3.6-35B-A3B-NSC-ACE-SABER-Q4_K_M.gguf",
        api_key=api_key,
        api_base=api_base,
        temperature=0.6,
        max_tokens=8000,
        # The measurement must not come from the ~/.dspy_cache (otherwise an earlier,
        # run with a different model is replayed — see
        # the false local baseline of 0.655 from 2026-07-29).
        cache=False,
    )
    dspy.configure(lm=lm, track_usage=True)


if __name__ == "__main__":
    main()
