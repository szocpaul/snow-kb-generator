# program.py — StoryToKBArticle(dspy.Module) (DESIGN, not implemented)
# ===========================================================================
#
# Responsibility: the three DSPy Signatures (signatures.py) into a single composite
# into a Module chain. This is the "program" that we baseline and GEPA-optimize.
#
# Planned class: StoryToKBArticle(dspy.Module)
#
#   __init__:
#     self.extract = dspy.ChainOfThought(ExtractChange)   # named!
#     self.draft   = dspy.ChainOfThought(DraftSections)
#     self.format  = dspy.Predict(FormatKB)
#
#   forward(story_text: str) -> dspy.Prediction:
#     1. ext = self.extract(story_text=story_text)
#     2. sec = self.draft(change_summary=ext.change_summary,
#                          key_steps=ext.key_steps,
#                          audience=ext.audience)
#     3. fmt = self.format(title=sec.title,
#                          problem=sec.problem,
#                          solution_steps=sec.solution_steps,
#                          summary=sec.summary)
#     4. return dspy.Prediction(
#          article=KBArticle(
#            title=sec.title, html=fmt.html,
#            category=<config default>, ...))
#
# GEPA szempontok:
#   - Every predictor gets a NAME -> GEPA can target the reflection.
#   - The data transfer between the inner steps must be TYPED (schemas.py).
#   - program.save() should work state-only (program.json) and full-program
#     also in (directory) mode -> deploy friendly.
#
# Open questions:
#   - Where should category come from? (config default vs. Extract suggestion)
#   - Should there be a fallback: if FormatKB gives bad HTML, do we retry?
#       -> Not at first; the rich metric should penalize this, and GEPA should improve on it.
#   - Support for multiple languages (article language)? -> config flag, later.
