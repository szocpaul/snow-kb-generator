"""gepa_optimize.py — GEPA optimization for the StoryToKBArticle program.

It runs the GEPA optimization with the help of the Kimi K3 reflection model, and
saves the optimized program to the artifacts/program.json file.
"""

from __future__ import annotations

import json
from pathlib import Path

import dspy

from eval.metric import rich_metric


def run_gepa_optimization(program, trainset, valset):
    """Runs the GEPA optimization with the Kimi K3 reflection model.

    Args:
        program: the current (not optimized) dspy.Module (StoryToKBArticle).
        trainset: A trainset (3 dspy.Example objektum).
        valset: A valset (2 dspy.Example objektum).

    Returns:
        (optimizer, optimized_program) tuple — the GEPA optimizer and the optimized program.
    """
    # LM configuration (globally, as the skill says)
    configure_lm()

    # Creating the GEPA optimizer with the help of the Kimi K3 reflection model
    optimizer = dspy.GEPA(
        metric=rich_metric,
        auto="light",
        reflection_lm=_create_reflection_lm(),
        candidate_selection_strategy="pareto",
        track_stats=True,
        log_dir="./gepa_logs",
        seed=0,
    )

    # Running the GEPA compile on the trainset and valset examples
    optimized_program = optimizer.compile(
        student=program,
        trainset=trainset,
        valset=valset,
    )

    return optimizer, optimized_program


def save_optimized_program(optimized_program, output_path: str | Path = "artifacts/program.json"):
    """Saves the optimized program to the artifacts/program.json file.

    Args:
        optimized_program: the optimized dspy.Module (the result of the GEPA compile).
        output_path: the path of the output JSON file (default: artifacts/program.json).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    optimized_program.save(str(output_path), save_program=False)


def extract_applied_suggestions(optimized_program) -> list[str]:
    """Extracts the applied reflection suggestions from the optimized program.

    Args:
        optimized_program: the optimized dspy.Module (the result of the GEPA compile).

    Returns:
        A list of concrete reflection suggestions applied to Signatures.
    """
    suggestions = []

    # A detailed_results tartalmazza az alkalmazott javaslatokat
    if hasattr(optimized_program, "detailed_results") and optimized_program.detailed_results:
        # A val_aggregate_scores tartalmazza a legjobb programokat
        if hasattr(optimized_program.detailed_results, "val_aggregate_scores"):
            scores = optimized_program.detailed_results.val_aggregate_scores
            if scores:
                suggestions.append(f"Best validation score: {max(scores)}")

    # A best_outputs_valset tartalmazza a legjobb kimeneteket
    if hasattr(optimized_program, "detailed_results") and optimized_program.detailed_results:
        if hasattr(optimized_program.detailed_results, "best_outputs_valset"):
            best_outputs = optimized_program.detailed_results.best_outputs_valset
            if best_outputs:
                suggestions.append(f"Best outputs: {len(best_outputs)} examples")

    return suggestions


def _create_reflection_lm():
    """Creates the Kimi K3 reflection model (temperature=1.0)."""
    import json
    from pathlib import Path

    # Reading the Pi Agent auth file (Kimi K3 endpoint)
    pi_auth_path = Path.home() / ".pi" / "agent" / "auth.json"
    auth_data = json.loads(pi_auth_path.read_text(encoding="utf-8"))

    # The Kimi K3 endpoint (Pi Agent Kimi subscription)
    api_key = auth_data.get("kimi-coding", {}).get("apiKey") or auth_data.get("zai-glm", {}).get("key") or auth_data.get("openai-codex", {}).get("access")

    return dspy.LM(
        "openai/kimi-k3",
        api_key=api_key,
        temperature=1.0,
        max_tokens=32000,
    )


def configure_lm():
    """Configures the DSPy LM globally from the settings (Qwen task LM)."""
    import json
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
