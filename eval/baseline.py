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

    # dspy.Evaluate gives a percentage (0-100) score; the spec and the tests expect a 0-1 scale.
    return EvaluationResult(score=average_score, results=result.results)


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
    )
    dspy.configure(lm=lm, track_usage=True)
