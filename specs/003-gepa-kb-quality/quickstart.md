# Quickstart: GEPA Optimization Validation

This guide describes how to validate the GEPA optimization feature end-to-end.

## Prerequisites

- The gold dataset (`data/examples/gold_dataset.md`) exists and contains 5 complete example pairs.
- The Qwen model (llama.cpp) is running and accessible (for daily generation baseline).
- The Kimi K3 model (Pi Agent) is available for reflection (GEPA optimization).
- The pytest suite is green (baseline validation).

## Validation Scenario 1: Gold Dataset Loading and Split

1. Run the dataset loading script: `python -c "from eval.dataset import load_gold_dataset; train, val = load_gold_dataset(); print(f'Train: {len(train)}, Val: {len(val)}')"`
2. **Expected**: Output shows `Train: 3, Val: 2` with no errors. Each example contains a complete Story and a matching KB article.

## Validation Scenario 2: Baseline Performance Measurement

1. Run the baseline evaluation: `python -m eval.baseline`
2. **Expected**: The current (unoptimized) program runs on the valset. The output shows the average score (e.g., `Average Score: 0.65`) and per-example feedback (e.g., `"Missing 'Target Audience' section"`). Results are saved to `runs/baseline.json`.

## Validation Scenario 3: GEPA Optimization

1. Run the GEPA optimization: `python -m eval.gepa_optimize --auto light`
2. **Expected**: The optimizer runs on the trainset (3 examples). The reflection model (Kimi K3) analyzes baseline feedback and proposes concrete improvements (e.g., `"Preserve 'Target Audience' section"`, `"Use 'N/A' for missing sections"`). The optimized program achieves a higher average score on the valset than the baseline (e.g., `Optimized Score: 0.85`).

## Validation Scenario 4: Optimized Program Export and Deployment

1. Save the optimized program: `python -c "from eval.gepa_optimize import save_optimized_program; save_optimized_program()"`
2. Restart the FastAPI server: `pkill -f uvicorn && uvicorn snow_kb.server:app --host 0.0.0.0 --port 8000`
3. Generate a KB article via the FastAPI server: `curl -X POST http://localhost:8000/generate-kb -H "Content-Type: application/json" -H "X-API-Key: ..." -d '{"story_id": "STRY0010010"}'`
4. **Expected**: The generated KB article uses the optimized Signatures (improved instructions) and achieves higher quality (better structure, no hallucinations, proper "N/A" usage).

## Automated Validation

Run the test suite to verify the eval harness logic programmatically:

```bash
pytest tests/test_eval_dataset.py -v
pytest tests/test_eval_metric.py -v
pytest tests/test_eval_baseline.py -v
```

All tests must pass without hitting the live Qwen/Kimi models or the ServiceNow API (mocked responses).
