# pipeline.py — orchestrátor (TERV, nincs implementálve)
# ===========================================================================
#
# Felelősség: a teljes end-to-end flow összefogása.
# Ez a réteg köti össze a ServiceNow client-et, a DSPy programot és az exportot.
# Maga a program (program.py) nem tud a ServiceNow-ról — az a client dolga.
#
# Tervezett függvények:
#
#   generate_kb_article(
#       story_identifier: str,           # STRY... vagy sys_id
#       dry_run: bool = False,
#       push: bool = True                # False -> csak generál, nem ír SNOW-ba
#   ) -> KBArticle:
#
#     1. settings = load_settings()
#     2. client   = ServiceNowClient(settings, dry_run=dry_run)
#     3. story    = client.get_story(story_identifier)          -> StoryData
#     4. story_text = assemble_story_text(story)                # mezők egyesítése
#     5. dspy.configure(lm=dspy.LM(settings.models.main), track_usage=True)
#     6. program   = StoryToKBArticle()
#     7. pred      = program(story_text=story_text)             -> Prediction
#     8. article   = pred.article                               -> KBArticle
#     9. if push and not dry_run:
#            article.sys_id = client.create_kb_article(article)
#       10. return article
#
#   assemble_story_text(story: StoryData) -> str:
#     A config.story_fields sorrendjében egyetlen szöveggé fűzi a mezőket,
#     fejléccel jelöli a szakaszokat (pl. "## Description: ...").
#     Ez a kontextus, amit ExtractChange kap.
#
# Hibakezelés (tervezett):
#   - StoryNotFound -> tiszta hibaüzenet, kilépés
#   - LM hiba -> újrapróbálkozás (dspy alapból retry-öl, de logoljuk)
#   - create_kb_article sikertelen -> article megmarad lokálisan (artifacts/),
#     nem dobja el a munkát
#
# Megjegyzések:
#   - Az assemble_story_text formázása hat a minőségre -> GEPA előtt fixáljuk,
#     de ne a Signature-okban változzon (külön separált dolog).
#   - Később: batch mód, több Story feldolgozása egyszerre.
