# dataset.py — train/val/test sets (DESIGN, not implemented)
# ===========================================================================
#
# Responsibility: DSPy Example sets from gold (Story -> KB) example pairs
# to build for the baseline and for the GEPA optimization.
#
# Source (planned):
#   data/examples/*.json — each file is an example pair:
#     {
#       "story": { ...StoryData fields... },
#       "gold_article": { "title", "html", "category", ... }
#     }
#   We collect these manually or from already existing KB articles.
#
# Planned functions:
#
#   load_examples(path="data/examples") -> list[dspy.Example]:
#       Reads the JSONs per example:
#         ex = dspy.Example(
#                story_text=assemble_story_text(story),
#                article=KBArticle(**gold_article)
#              ).with_inputs("story_text")
#       Only the input field of the program ("story_text") is marked as input.
#
#   split_examples(examples, train=0.6, val=0.2, test=0.2, seed=0)
#       -> (trainset, valset, testset)
#       Stratified split based on audience / category, if possible.
#
# GEPA-specifikus elvek (dspy-evaluation-harness):
#   - trainset as large as possible (GEPA needs many examples)
#   - valset just large enough to represent the downstream behavior
#   - testset HIDDEN — we use it only at the end, for the report
#
# Notes:
#   - If there is little gold data, we can also generate fake/bootstrap examples,
#     but we mark these separately (tag: "synthetic") so that the valset stays clean.
#   - The formatting of assemble_story_text must be UNIFORM with pipeline.py.
