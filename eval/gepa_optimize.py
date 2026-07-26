"""gepa_optimize.py — GEPA optimalizáció a StoryToKBArticle programhoz.

Lefuttatja a GEPA optimalizációt a Kimi K3 reflection modell segítségével, és
elmenti az optimalizált programot az artifacts/program.json fájlba.

CLI használat (quickstart Scenario 3-4):
    python -m eval.gepa_optimize --auto light
"""

from __future__ import annotations

import json
from pathlib import Path

import dspy

from eval.metric import rich_metric


def run_gepa_optimization(program, trainset, valset):
    """Létrehozza a GEPA optimizert a Kimi K3 reflection modell segítségével.

    A compile-t NEM futtatja — azt külön kell meghívni (ld. compile_with_gepa),
    mert az valódi dspy.Module-t és LM hívásokat igényel.

    Args:
        program: A jelenlegi (nem optimalizált) dspy.Module (StoryToKBArticle).
        trainset: A trainset (3 dspy.Example objektum).
        valset: A valset (2 dspy.Example objektum).

    Returns:
        A konfigurált dspy.GEPA optimizer példány.
    """
    # LM konfigurálása (globálisan, ahogy a skill szerint)
    configure_lm()

    # GEPA optimizer létrehozása a Kimi K3 reflection modell segítségével
    return dspy.GEPA(
        metric=rich_metric,
        auto="light",
        reflection_lm=_create_reflection_lm(),
        candidate_selection_strategy="pareto",
        track_stats=True,
        log_dir="./gepa_logs",
        seed=0,
    )


def compile_with_gepa(optimizer, program, trainset, valset):
    """Lefuttatja a GEPA compile-t és visszaadja az optimalizált programot.

    Args:
        optimizer: A run_gepa_optimization() által visszaadott dspy.GEPA példány.
        program: A nem optimalizált dspy.Module (StoryToKBArticle).
        trainset: A trainset (dspy.Example objektumok).
        valset: A valset (dspy.Example objektumok).

    Returns:
        Az optimalizált dspy.Module (a GEPA compile eredménye).
    """
    return optimizer.compile(
        student=program,
        trainset=trainset,
        valset=valset,
    )


def save_optimized_program(optimized_program, output_path: str | Path = "artifacts/program.json"):
    """Elmenti az optimalizált programot az artifacts/program.json fájlba.

    Args:
        optimized_program: Az optimalizált dspy.Module (a GEPA compile eredménye).
        output_path: A kimeneti JSON fájl útvonala (alapértelmezett: artifacts/program.json).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    optimized_program.save(str(output_path), save_program=False)


def extract_applied_suggestions(optimized_program) -> list[str]:
    """Kinyeri az alkalmazott reflection javaslatokat az optimalizált programból.

    Args:
        optimized_program: Az optimalizált dspy.Module (a GEPA compile eredménye).

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
    """Létrehozza a Kimi K3 reflection modellt (temperature=1.0)."""
    import json
    from pathlib import Path

    # A Pi Agent auth fájl olvasása (Kimi K3 endpoint)
    pi_auth_path = Path.home() / ".pi" / "agent" / "auth.json"
    auth_data = json.loads(pi_auth_path.read_text(encoding="utf-8"))

    # A Kimi K3 endpoint (Pi Agent Kimi előfizetés)
    api_key = auth_data.get("kimi-coding", {}).get("apiKey") or auth_data.get("zai-glm", {}).get("key") or auth_data.get("openai-codex", {}).get("access")

    return dspy.LM(
        "openai/kimi-k3",
        api_key=api_key,
        temperature=1.0,
        max_tokens=32000,
    )


def configure_lm():
    """Globálisan konfigurálja a DSPy LM-et a settings-ből (Qwen task LM)."""
    import json
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


# ---------------------------------------------------------------------------
# CLI belépési pont (python -m eval.gepa_optimize --auto light)
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """T012-T014: GEPA compile + javaslatok kinyerése + optimalizált program mentése."""
    import argparse

    parser = argparse.ArgumentParser(description="GEPA optimalizáció a StoryToKBArticle programhoz.")
    parser.add_argument("--auto", default="light", choices=["light", "medium", "heavy"],
                        help="GEPA budget preset (alapértelmezett: light).")
    parser.add_argument("--dataset", default="data/examples/gold_dataset.md",
                        help="A gold dataset markdown fájl útvonala.")
    parser.add_argument("--output", default="artifacts/program.json",
                        help="Az optimalizált program kimeneti JSON fájlja.")
    args = parser.parse_args(argv)

    from eval.baseline import run_baseline
    from eval.dataset import load_gold_dataset
    from snow_kb.program import StoryToKBArticle

    # 1. Dataset betöltése
    trainset, valset = load_gold_dataset(args.dataset)
    print(f"Dataset: {len(trainset)} train / {len(valset)} val példa")

    # 2. Baseline mérés (ha még nincs runs/baseline.json)
    baseline_path = Path("runs/baseline.json")
    if baseline_path.exists():
        baseline_score = json.loads(baseline_path.read_text(encoding="utf-8"))["average_score"]
        print(f"Baseline (meglévő runs/baseline.json): {baseline_score:.3f}")
    else:
        configure_lm()
        program = StoryToKBArticle()
        baseline = run_baseline(program, valset)
        baseline_score = baseline.score
        print(f"Baseline (frissen mérve): {baseline_score:.3f}")

    # 3. GEPA optimizer létrehozása + compile (T012)
    program = StoryToKBArticle()
    optimizer = run_gepa_optimization(program, trainset, valset)
    print("GEPA compile fut... (auto=%s)" % args.auto)
    optimized_program = compile_with_gepa(optimizer, program, trainset, valset)

    # 4. Alkalmazott reflection javaslatok kinyerése (T013)
    suggestions = extract_applied_suggestions(optimized_program)
    print("\nAlkalmazott javaslatok:")
    for s in suggestions:
        print(f"  - {s}")

    # 5. Optimalizált program kiértékelése a valset-en
    optimized_eval = run_baseline(optimized_program, valset, output_path="runs/optimized.json")
    print(f"\nOptimized score: {optimized_eval.score:.3f} (baseline: {baseline_score:.3f})")

    # 6. Mentés (T014)
    save_optimized_program(optimized_program, args.output)
    print(f"Optimalizált program elmentve: {args.output}")


if __name__ == "__main__":
    main()
