# Research: GEPA Optimization for KB Article Quality

## Decision: Use `dspy.GEPA(auto="light")` for the first optimization pass

**Rationale**: The dspy-gepa-optimizer skill explicitly warns: "Running `auto="heavy"` on an untested metric — burn money to learn the metric was bugged. Run `auto="light"` first." Our metric is new and untested, so `auto="light"` (~20-40 full evals) is the safe, cost-effective first pass. If it works, we can scale to `auto="medium"` later.

## Decision: Split gold dataset 3 trainset / 2 valset

**Rationale**: The skill says: "For GEPA, maximize training examples and keep validation just large enough to represent the downstream distribution." With only 5 examples, 3 trainset + 2 valset gives the optimizer enough training data to learn from traces/feedback, while keeping 2 examples to validate the optimized program without overfitting. We do NOT use a 20/80 split (that's for MIPROv2, not GEPA).

## Decision: Use Kimi K3 as reflection_lm (temperature=1.0)

**Rationale**: The skill says: "use the strongest instruction-following model available on your provider. `dspy.LM(...)` is a cheap stub until you actually call it." Kimi K3 is our strongest available model (via Pi Agent). We set `temperature=1.0` for creative proposals, as the skill recommends: "reflection_lm — a strong LM set to `temperature=1.0` for creative proposals." The Qwen (task LM) runs at `default_temperature=0.6` for daily generation (to avoid `repeat` finish_reason).

## Decision: rich_metric returns `dspy.Prediction(score=float, feedback=str)`

**Rationale**: The skill's metric contract is precise: "**Return `dspy.Prediction`, not a dict.**" Our rich_metric will compute a multi-axis score (structure_match, content_accuracy, template_adherence) and generate natural-language feedback (e.g., "Missing 'Target Audience' section", "Used 'N/A' correctly for Inbound section"). This feedback is "load-bearing" — it's what the reflection LM learns from.

## Decision: log_dir="./gepa_logs" for checkpointing

**Rationale**: The skill says: "`log_dir` writes candidate programs + scores per round. To resume an interrupted run, point `log_dir` at the same directory — GEPA picks up from the last checkpoint." We enable this to avoid losing a 30-minute GEPA run to a disconnect.

## Alternatives Considered

- **MIPROv2**: Rejected. Our metric produces rich textual feedback (GEPA's superpower), and our program has multiple predictors (ExtractChange, DraftSections, FormatKB, GenerateKbFromTemplate) that need targeted improvements (GEPA gives per-predictor feedback; MIPRO doesn't).
- **SIMBA**: Rejected. Our program is complex (multi-predictor), and we need per-predictor feedback and Pareto candidate selection (GEPA > SIMBA for this).
- **BetterTogether**: Rejected. Keep plain GEPA as the default first pass; only chain optimizers if we have a specific reason (we don't).
