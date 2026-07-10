# servicenow_client.py — ServiceNow Table API client (DESIGN, not implemented)
# ===========================================================================
#
# Responsibility: ALL HTTP communication with ServiceNow happens here.
# The rest of the pipeline does not know about requests/httpx.
#
# Authentication (planned):
#   Basic Auth (username + password) from the .env, or OAuth token (later).
#   Alap URL: https://<SNOW_INSTANCE>/api/now/table/
#
# Planned class: ServiceNowClient
#   Constructor input: settings (from config.py)
#
# Planned methods:
#
#   get_story(story_sys_id_or_number: str) -> StoryData
#       Endpoint: GET /table/story/<sys_id>?sysparm_query=number=<STRY...>
#       Retrieves the fields listed in config.story_fields.
#       sysparm_display_value=true to resolve work notes/references.
#       Error handling: 404 -> StoryNotFound, 401 -> AuthError, timeout -> retry.
#
#   create_kb_article(article: KBArticle) -> str
#       Endpoint: POST /table/kb_knowledge
#       body: {
#         knowledge_base: settings.servicenow.knowledge_base_id,
#         short_description: article.title,
#         text: article.html,            # vagy kb_knowledge.text
#         category: article.category,
#         article_type: "text",
#       }
#       Returns: the new KB sys_id (or article URL).
#
#   (later) list_stories(state="Closed Complete") -> Iterator[StoryData]
#       Batch retrieval with nested pagination (sysparm_limit + offset).
#
# Dry-run support:
#   The Client should have a `dry_run=True` flag (from the settings or the CLI).
#   with dry_run=True get_story reads from a mock file (data/sample_stories/),
#   create_kb_article only logs and returns a dummy sys_id.
#
# Notes:
#   - The Story table name may differ per instance ("story" vs "rm_story").
#     This must go into the config, do not hardcode it.
#   - The work_notes/comments fields are a list of journal entries; these must be merged.
