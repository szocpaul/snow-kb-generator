# program.py — StoryToKBArticle(dspy.Module) (TERV, nincs implementálva)
# ===========================================================================
#
# Felelősség: a három DSPy Signature-t (signatures.py) egyetlen összetett
# Module-láncba fűzni. Ez a "program", amit baseline-olunk és GEPA-zunk.
#
# Tervezett osztály: StoryToKBArticle(dspy.Module)
#
#   __init__:
#     self.extract = dspy.ChainOfThought(ExtractChange)   # névvel ellátva!
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
#            category=<config alapértelmezett>, ...))
#
# GEPA szempontok:
#   - Minden prediktor NEVET kap -> GEPA tudja cél-irányítani a reflection-t.
#   - A belső lépések közötti adatátadás TÍPUSOS legyen (schemas.py).
#   - A program.save() működjön state-only (program.json) és full-program
#     (könyvtár) módban is -> deploy-barát.
#
# Nyitott kérdések:
#   - A category honnan jöjjön? (config alapértelmezés vs. Extract javaslat)
#   - Legyen-e fallback: ha a FormatKB hibás HTML-t ad, újra próbálkozunk?
#       -> Először nem; a rich metric ezt büntesse, és a GEPA javítson rajta.
#   - Több nyelv támogatása (article nyelve)? -> config flag, később.
