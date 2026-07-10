# pipeline.py — orchestrator (DESIGN, not implemented)
# ===========================================================================
#
# Responsibility: taking care of the entire end-to-end flow.
# This layer connects the ServiceNow client, the DSPy program and the export.
# The program itself (program.py) knows nothing about ServiceNow — that is the client's job.
#
# Planned functions:
#
#   generate_kb_article(
#       story_identifier: str,           # STRY... vagy sys_id
#       dry_run: bool = False,
#       push: bool = True                # False -> only generates, does not write to SNOW
#   ) -> KBArticle:
#
#     1. settings = load_settings()
#     2. client   = ServiceNowClient(settings, dry_run=dry_run)
#     3. story    = client.get_story(story_identifier)          -> StoryData
#     4. story_text = assemble_story_text(story)                # merging the fields
#     5. dspy.configure(lm=dspy.LM(settings.models.main), track_usage=True)
#     6. program   = StoryToKBArticle()
#     7. pred      = program(story_text=story_text)             -> Prediction
#     8. article   = pred.article                               -> KBArticle
#     9. if push and not dry_run:
#            article.sys_id = client.create_kb_article(article)
#       10. return article
#
#   assemble_story_text(story: StoryData) -> str:
#     It weaves the fields into a single text in the order of config.story_fields,
#     marks the sections with a heading (e.g. "## Description: ...").
#     This is the context that ExtractChange receives.
#
# Error handling (planned):
#   - StoryNotFound -> clean error message, exit
#   - LM error -> retry (dspy retries by default, but we log it)
#   - create_kb_article fails -> the article remains locally (artifacts/),
#     does not throw the work away
#
# Notes:
#   - The formatting of assemble_story_text affects the quality -> we fix it before GEPA,
#     but let it not change in the Signatures (a separate thing).
#   - Later: batch mode, processing multiple Stories at once.
