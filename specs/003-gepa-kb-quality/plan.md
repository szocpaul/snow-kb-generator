# Implementation Plan: GEPA Optimization for KB Article Quality

**Branch**: `003-gepa-kb-quality` | **Date**: 2026-07-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-gepa-kb-quality/spec.md`

## Summary

The current KB generation pipeline produces articles that sometimes hallucinate content for irrelevant template sections. To improve quality without manual prompt engineering, the system will use DSPy's GEPA (Genetic-Pareto) optimizer. It loads 5 gold standard example pairs (Story → perfect KB article), measures the current program's performance (baseline), and uses the Kimi K3 reflection model to automatically propose and apply improvements to the Signature instructions based on metric feedback.

## Technical Context

**Language/Version**: Python 3.12 (DSPy pipeline)

**Primary Dependencies**: DSPy 3.2.x (`dspy.GEPA`), Pydantic v2, PyYAML

**Storage**: Gold dataset (`data/examples/gold_dataset.md`), Baseline results (`runs/baseline.json`), Optimized program (`artifacts/program.json`), GEPA logs (`gepa_logs/`)

**Testing**: pytest (eval harness tests, metric tests, dataset split tests)

**Target Platform**: Hetzner VPS (FastAPI server, GEPA runs offline/CLI)

**Project Type**: web-service (AI pipeline optimization)

**Performance Goals**: Baseline eval completes in < 5 minutes (2 valset examples × 1 LM call each); GEPA `auto="light"` completes in < 30 minutes (~20-40 full evals).

**Constraints**: External LM (Qwen/Kimi) and ServiceNow calls must be mocked in tests (Constitution Principle III). The metric must return `dspy.Prediction(score=float, feedback=str)` (GEPA contract). The reflection_lm (Kimi K3) is required at GEPA constructor time (Constitution Principle II).

**Scale/Scope**: 5 gold examples (3 trainset / 2 valset), 1 program (StoryToKBArticle), 3-5 Signatures (ExtractChange, DraftSections, FormatKB, GenerateKbFromTemplate).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Spec-Driven Pipeline Arch)**: ✅ PASS. The GEPA optimization is a separate module (`eval/`), not mixed into the production pipeline. The FastAPI server remains the single transport.
- **Principle II (DSPy-First)**: ✅ PASS. The entire feature is DSPy-native (dspy.GEPA, dspy.Evaluate, dspy.Example, dspy.Prediction). No hardcoded prompts.
- **Principle III (Test-First)**: ✅ PLANNED. The eval harness (dataset split, metric, baseline) will be developed test-first with mocked LM responses.
- **Principle IV (Secrets Hygiene)**: ✅ PASS. No new secrets; the Qwen/Kimi auth is via existing `config.yaml` / `.env` / Pi auth.
- **Principle V (ServiceNow API Isolation)**: ✅ PASS. The GEPA optimization uses only the gold dataset (local files), not live ServiceNow calls.

No violations. Complexity Tracking table omitted.

## Project Structure

### Documentation (this feature)

```text
specs/003-gepa-kb-quality/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── gepa-metric-contract.md  # Interface contract for rich_metric
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
eval/
├── dataset.py           # NEW: Loads gold_dataset.md, splits into trainset/valset (dspy.Example)
├── metric.py            # NEW: rich_metric(gold, pred) → dspy.Prediction(score, feedback)
├── baseline.py          # NEW: dspy.Evaluate(devset=valset, metric=rich_metric) → runs/baseline.json
└── gepa_optimize.py     # NEW: dspy.GEPA(metric, auto="light", reflection_lm=Kimi K3) → artifacts/program.json

tests/
├── test_eval_dataset.py  # NEW: Dataset loading/split validation
├── test_eval_metric.py   # NEW: rich_metric score/feedback validation
└── test_eval_baseline.py # NEW: dspy.Evaluate integration test (mocked LM)
```

**Structure Decision**: The `eval/` directory is introduced as a dedicated module for all optimization-related code, keeping it separate from the production `src/` pipeline. This adheres to Constitution Principle I (modular replacement).
