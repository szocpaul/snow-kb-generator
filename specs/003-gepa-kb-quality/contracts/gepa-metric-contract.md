# Interface Contract: GEPA Metric and Optimization

This contract describes the interface between the eval harness (`eval/`), the DSPy program (`StoryToKBArticle`), and the GEPA optimizer.

## `rich_metric(gold, pred, trace=None, pred_name=None, pred_trace=None) -> dspy.Prediction`

- **Purpose**: Computes a score (0-1) and natural-language feedback by comparing the generated KB article (`pred`) to the expected gold article (`gold`).
- **Signature**:
  ```python
  def rich_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
      # 1. Compute sub-scores — multi-axis beats scalar
      structure_match = ...  # 1.0 if HTML headings match template, 0.0 otherwise
      content_accuracy = ... # 1.0 if facts match gold, 0.0 if hallucinated
      template_adherence = ... # 1.0 if "N/A" used correctly for irrelevant sections
      score = 0.4 * structure_match + 0.4 * content_accuracy + 0.2 * template_adherence

      # 2. Write feedback that teaches the optimizer
      parts = []
      if structure_match < 1.0:
          parts.append(f"Structure mismatch. Expected headings: {expected_headings}. Got: {actual_headings}.")
      if content_accuracy < 1.0:
          parts.append(f"Content mismatch. Expected: {expected_fact}. Got: {actual_fact}.")
      if template_adherence < 1.0:
          parts.append(f"Template violation. Expected 'N/A' for {irrelevant_section}, got: {actual_content}.")
      if not parts:
          parts.append("Correct structure, accurate content, and proper template adherence.")
      feedback = " ".join(parts)

      return dspy.Prediction(score=score, feedback=feedback)
  ```
- **Returns**: `dspy.Prediction(score=float, feedback=str)` (GEPA contract — **NOT a dict**).

## `dspy.Evaluate(devset=valset, metric=rich_metric, ...) -> EvaluationResult`

- **Purpose**: Runs the current (unoptimized) program on the valset and produces baseline results.
- **Inputs**: `devset=valset` (2 examples), `metric=rich_metric`, `num_threads=1`, `provide_traceback=True`.
- **Outputs**: `EvaluationResult` with `.score` (average float) and `.results` (list of `(example, pred, score)` tuples).
- **Side Effects**: Saves baseline results to `runs/baseline.json`.

## `dspy.GEPA(metric=rich_metric, auto="light", reflection_lm=KimiK3, ...) -> GEPA`

- **Purpose**: Optimizes the program using the reflection model to improve Signature instructions based on metric feedback.
- **Inputs**: `metric=rich_metric`, `auto="light"`, `reflection_lm=dspy.LM("openai/kimi-k3", temperature=1.0, max_tokens=32000)`, `candidate_selection_strategy="pareto"`, `track_stats=True`, `log_dir="./gepa_logs"`.
- **Outputs**: Optimized program (dspy.Module with improved Signatures).
- **Side Effects**: Writes candidate programs and scores to `gepa_logs/`, saves optimized program to `artifacts/program.json`.

## Pipeline Orchestration (`eval/gepa_optimize.py`)

1. Load gold dataset from `data/examples/gold_dataset.md` → split into trainset (3) and valset (2).
2. Compute baseline: `dspy.Evaluate(devset=valset, metric=rich_metric)(program)` → save to `runs/baseline.json`.
3. Run GEPA: `optimizer.compile(student=program, trainset=trainset, valset=valset)` → optimized program.
4. Save optimized program to `artifacts/program.json` (state-only format).
5. FastAPI server loads optimized program on startup (from `artifacts/program.json`).
