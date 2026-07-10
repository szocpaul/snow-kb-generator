# servicenow_client.py — ServiceNow Table API kliens (TERV, nincs implementálva)
# ===========================================================================
#
# Felelősség: a ServiceNow-mal való ÖSSZES HTTP kommunikáció itt zajlik.
# A pipeline többi része nem tud a requests/httpx-ről.
#
# Hitelesítés (tervezett):
#   Basic Auth (username + password) a .env-ből, vagy OAuth token (később).
#   Alap URL: https://<SNOW_INSTANCE>/api/now/table/
#
# Tervezett osztály: ServiceNowClient
#   Konstruktor bemenete: settings (a config.py-ból)
#
# Tervezett metódusok:
#
#   get_story(story_sys_id_or_number: str) -> StoryData
#       Végpont: GET /table/story/<sys_id>?sysparm_query=number=<STRY...>
#       Lekéri a config.story_fields-ben felsorolt mezőket.
#       sysparm_display_value=true a munkajegyzetek/hivatkozások feloldásához.
#       Hibakezelés: 404 -> StoryNotFound, 401 -> AuthError, timeout -> retry.
#
#   create_kb_article(article: KBArticle) -> str
#       Végpont: POST /table/kb_knowledge
#       body: {
#         knowledge_base: settings.servicenow.knowledge_base_id,
#         short_description: article.title,
#         text: article.html,            # vagy kb_knowledge.text
#         category: article.category,
#         article_type: "text",
#       }
#       Visszatér: az új KB sys_id (vagy article URL).
#
#   (később) list_stories(state="Closed Complete") -> Iterator[StoryData]
#       Batch lekérés döngyölt pagination-nel (sysparm_limit + offset).
#
# Dry-run támogatás:
#   A Client kapjon egy `dry_run=True` flag-et (a settings-ből vagy CLI-ből).
#   dry_run=True esetén get_story mock fájlból olvas (data/sample_stories/),
#   create_kb_article csak log-ol és egy dummy sys_id-t ad vissza.
#
# Megjegyzések:
#   - A Story tábla neve instance-onként eltérhet ("story" vs "rm_story").
#     Ezt config-ba kell tenni, ne hardcode-oljuk.
#   - A work_notes/comments mezők list of journal entry; ezeket egyesíteni kell.
