# metric.py — rich feedback metric for GEPA (DESIGN, not implemented)
# ===========================================================================
#
# Responsibility: to evaluate the quality of the generated KB article on a 0..1 scale,
# with DETAILED feedback. The feedback is "load-bearing" — the GEPA learns from it
# a GEPA reflection LM.
#
# CRITICAL: dspy.Prediction(score=..., feedback=...) format!
#   (A plain dict breaks the dspy.Evaluate aggregation.)
#
# Planned function:
#
#   rich_metric(gold, pred, trace=None, pred_name=None, pred_trace=None)
#       -> dspy.Prediction(score: float, feedback: str)
#
#       pred.article  -> the generated KBArticle
#       gold.article  -> the reference KBArticle (or rubric fields)
#
# Evaluation axes (in a comment — they still have to be weighted):
#
#   1. Accuracy
#        Does the article reflect the actual changes of the Story?
#        There is no invented step, no omitted critical point.
#        (It can be an LLM-as-judge, or a structured check.)
#
#   2. Reproducibility
#        Are the solution_steps actually executable for someone?
#        Do concrete tools/menus/elements appear?
#
#   3. Audience fit
#        Does the language and depth fit the audience?
#        (helpdesk: step by step; end-user: less jargon; dev: more technical)
#
#   4. Structure
#        The HTML is valid, contains title/problem/solution sections.
#        The solution_steps are numbered/ordered.
#
#   5. Conciseness
#        There is no unnecessary poetic filler, but it is not incomplete either.
#
# Feedback (feedback) — NATURAL LANGUAGE:
#   "The title is too generic ('Bug fix'). Step 3 is missing the screenshot reference.
#    The audience is 'helpdesk', but the solution uses developer jargon
#    (e.g. 'restart a worker pool' without it being written down)."
#
# Trace mode (trace is not None):
#   If it is called by Evaluate with a trace, we are stricter (for bootstrap).
#   If not (normal eval), more lenient. This is the dspy convention.
#
# Weighting (suggestion, to be refined):
#   score = 0.30*accuracy + 0.25*reproducibility + 0.20*audience
#         + 0.15*structure + 0.10*conciseness
#
# Notes:
#   - The feedback must BE SPECIFIC (quote, step number) — not general praise.
#   - The judge can have its own LM (settings.models.reflection or a custom one).
#   - If there is no gold article, only rubric-based evaluation (without the gold trace).
