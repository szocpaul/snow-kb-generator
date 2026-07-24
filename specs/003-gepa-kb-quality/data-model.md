# Data Model: GEPA Optimization for KB Article Quality

## Entity: Gold Dataset Example

A single training/validation example pair used for GEPA optimization.

| Field | Type | Description | New? |
|-------|------|-------------|------|
| `story_number` | String | The Story number (e.g., `STRY0010001`). | No |
| `story_text` | String | The assembled Story text (short_description, description, acceptance_criteria, technical_specification, work_notes, comments). | No |
| `assignment_group` | String | The team (e.g., "Integration Team"). | No |
| `expected_html` | String (HTML) | The perfect KB article (HTML structure following KBA1-KBA11). | No |
| `expected_sections` | dict | Parsed sections from expected_html (title, overview, inbound, outbound, usage, testing, known_issues, investigation). | No |

## Entity: Baseline Result

The performance measurement of the current (unoptimized) program on the valset.

| Field | Type | Description | New? |
|-------|------|-------------|------|
| `average_score` | Float | Average score (0-1) across all valset examples. | No |
| `per_example` | list | List of `{story_number, score, feedback}` objects. | No |
| `timestamp` | String (ISO) | When the baseline was measured. | No |

## Entity: Optimized Program

The improved program after GEPA optimization.

| Field | Type | Description | New? |
|-------|------|-------------|------|
| `program_path` | String | Path to `artifacts/program.json` (state-only format). | No |
| `average_score` | Float | Average score (0-1) of the optimized program on the valset. | No |
| `improvement` | Float | Score difference (optimized - baseline). | No |
| `applied_suggestions` | list | List of concrete reflection suggestions applied to Signatures. | No |

## Validation Rules

- **VR-001**: The gold dataset MUST contain 5 complete example pairs (Story + expected KB article) following the Integration Team Template structure (KBA1-KBA11).
- **VR-002**: The trainset (3 examples) and valset (2 examples) MUST be disjoint (no overlap).
- **VR-003**: The rich_metric MUST return `dspy.Prediction(score=float, feedback=str)` (GEPA contract).
- **VR-004**: The optimized program MUST achieve a higher average_score on the valset than the baseline (or the system reports no improvement).

## DSPy-Specific Model (Logical Model)

The GEPA optimization uses these DSPy types:

| Field | Type | Description |
|-------|------|-------------|
| `dspy.Example` | `dspy.Example(story_text=..., html=...).with_inputs("story_text")` | Training/validation example. |
| `dspy.Prediction` | `dspy.Prediction(score=..., feedback=...)` | Metric result (score + feedback). |
| `dspy.Evaluate` | `dspy.Evaluate(devset=valset, metric=rich_metric, ...)` | Baseline evaluator. |
| `dspy.GEPA` | `dspy.GEPA(metric=..., auto="light", reflection_lm=...)` | Optimizer. |
