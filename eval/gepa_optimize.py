"""gepa_optimize.py — GEPA optimization for the StoryToKBArticle program.

It runs the GEPA optimization with the help of the Kimi K3 reflection model, and
saves the optimized program to the artifacts/program.json file.

CLI usage (quickstart Scenario 3-4):
    python -m eval.gepa_optimize --auto light
"""

from __future__ import annotations

import json
from pathlib import Path

import dspy

from eval.metric import rich_metric


def run_gepa_optimization(program, trainset, valset):
    """Creates the GEPA optimizer with the help of the Kimi K3 reflection model.

    It does NOT run the compile — that must be called separately (see compile_with_gepa),
    because it needs a real dspy.Module and LM calls.

    Args:
        program: the current (not optimized) dspy.Module (StoryToKBArticle).
        trainset: A trainset (3 dspy.Example objektum).
        valset: A valset (2 dspy.Example objektum).

    Returns:
        The configured dspy.GEPA optimizer instance.
    """
    # LM configuration (globally, as the skill says)
    configure_lm()

    # Creating the GEPA optimizer with the help of the Kimi K3 reflection model
    return dspy.GEPA(
        metric=rich_metric,
        auto="light",
        reflection_lm=_create_reflection_lm(),
        candidate_selection_strategy="pareto",
        instruction_proposer=_create_instruction_proposer(),
        track_stats=True,
        log_dir="./gepa_logs",
        seed=0,
    )


_EVIDENCE_FIRST_GUIDANCE = """\
Include only sections the story supports with concrete evidence; if a section has no
supporting evidence, omit it entirely (no 'N/A' placeholders). For an outbound-only
story, omit the 'Inbound Technical Implementation' section (and vice versa); shared
components belong to the direction the story implements. Never invent KB article
numbers or titles — use only references provided in the inputs."""


def _create_instruction_proposer():
    """SkilledProposer (anti-overfitting) az evidence-first guidance-szel (spec 007).

    Fallback: if the package is not available, the stock proposer (None) + a warning.
    """
    try:
        from skilled_proposer import SkilledProposer

        return SkilledProposer(additional_instructions=_EVIDENCE_FIRST_GUIDANCE)
    except ImportError:
        import warnings

        warnings.warn(
            "skilled-proposer is not installed — using the stock GEPA proposer. "
            "Installation: ../.venv/bin/pip install skilled-proposer"
        )
        return None


def compile_with_gepa(optimizer, program, trainset, valset):
    """Runs the GEPA compile and returns the optimized program.

    Args:
        optimizer: the dspy.GEPA instance returned by run_gepa_optimization().
        program: the non-optimized dspy.Module (StoryToKBArticle).
        trainset: A trainset (dspy.Example objektumok).
        valset: A valset (dspy.Example objektumok).

    Returns:
        The optimized dspy.Module (the result of the GEPA compile).
    """
    return optimizer.compile(
        student=program,
        trainset=trainset,
        valset=valset,
    )


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

    # The Kimi K3 endpoint (Pi Agent Kimi subscription, OAuth token, OpenAI-compatible)
    api_key = auth_data.get("kimi-coding", {}).get("access") or auth_data.get("kimi-coding", {}).get("apiKey")

    return dspy.LM(
        "openai/k3",
        api_key=api_key,
        api_base="https://api.kimi.com/coding/v1",
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


# ---------------------------------------------------------------------------
# CLI entry point (python -m eval.gepa_optimize --auto light)
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """T012-T014: the GEPA compile + extracting the suggestions + saving the optimized program."""
    import argparse

    parser = argparse.ArgumentParser(description="GEPA optimization for the StoryToKBArticle program.")
    parser.add_argument("--auto", default="light", choices=["light", "medium", "heavy"],
                        help="GEPA budget preset (default: light).")
    parser.add_argument("--dataset", default="data/examples/gold_dataset.md",
                        help="The path of the gold dataset markdown file.")
    parser.add_argument("--output", default="artifacts/program.json",
                        help="The output JSON file of the optimized program.")
    args = parser.parse_args(argv)

    from eval.baseline import run_baseline
    from eval.dataset import load_gold_dataset
    from snow_kb.program import StoryToKBArticle

    # 1. Loading the dataset
    trainset, valset = load_gold_dataset(args.dataset)
    print(f"Dataset: {len(trainset)} train / {len(valset)} val examples")

    # 2. The baseline measurement (if there is no runs/baseline.json yet)
    baseline_path = Path("runs/baseline.json")
    if baseline_path.exists():
        baseline_score = json.loads(baseline_path.read_text(encoding="utf-8"))["average_score"]
        print(f"Baseline (existing runs/baseline.json): {baseline_score:.3f}")
    else:
        configure_lm()
        program = StoryToKBArticle()
        baseline = run_baseline(program, valset)
        baseline_score = baseline.score
        print(f"Baseline (freshly measured): {baseline_score:.3f}")

    # 3. Creating the GEPA optimizer + compile (T012)
    program = StoryToKBArticle()
    optimizer = run_gepa_optimization(program, trainset, valset)
    print("GEPA compile fut... (auto=%s)" % args.auto)
    optimized_program = compile_with_gepa(optimizer, program, trainset, valset)

    # 4. Extracting the applied reflection suggestions (T013)
    suggestions = extract_applied_suggestions(optimized_program)
    print("\nAlkalmazott javaslatok:")
    for s in suggestions:
        print(f"  - {s}")

    # 5. Evaluating the optimized program on the valset
    optimized_eval = run_baseline(optimized_program, valset, output_path="runs/optimized.json")
    print(f"\nOptimized score: {optimized_eval.score:.3f} (baseline: {baseline_score:.3f})")

    # 6. Saving (T014)
    save_optimized_program(optimized_program, args.output)
    print(f"Optimized program saved: {args.output}")


if __name__ == "__main__":
    main()
