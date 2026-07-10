# metric.py — rich feedback metric GEPA-hoz (TERV, nincs implementálva)
# ===========================================================================
#
# Felelősség: a generált KB cikk minőségét 0..1 skálán értékelni,
# RÉSZLETES visszajelzéssel. A feedback "load-bearing" — ebből tanul
# a GEPA reflection LM.
#
# KRITIKUS: dspy.Prediction(score=..., feedback=...) formátum!
#   (Egy sima dict összeomlasztja a dspy.Evaluate aggregációt.)
#
# Tervezett függvény:
#
#   rich_metric(gold, pred, trace=None, pred_name=None, pred_trace=None)
#       -> dspy.Prediction(score: float, feedback: str)
#
#       pred.article  -> a generált KBArticle
#       gold.article  -> a referencia KBArticle (vagy rubrik-mezők)
#
# Értékelési tengelyek (kommentben — majd össze kell súlyozni):
#
#   1. Pontosság (accuracy)
#        A cikk tükrözi-e a Story tényleges változásait?
#        Nincs kitalált lépés, nincs elhagyott kritikus pont.
#        (Lehet LLM-as-judge, vagy strukturált ellenőrzés.)
#
#   2. Reprodukálhatóság (reproducibility)
#        A solution_steps tényleg végrehajtható-e valaki számára?
#        Konkrét eszközök/menük/elemek szerepelnek?
#
#   3. Célközönség (audience fit)
#        A nyelv és mélység illeszkedik-e az audience-hoz?
#        (helpdesk: lépésről lépésre; end-user: kevesebb zsargon; dev: technikaibb)
#
#   4. Struktúra (structure)
#        HTML érvényes, tartalmaz title/problem/solution szakaszokat.
#        A solution_steps számozott/rendezett.
#
#   5. Tömörség (conciseness)
#        Nincs felesleges költői kitöltés, de nem is hiányos.
#
# Visszajelzés (feedback) — TERMÉSZETES NYELV:
#   "A cím túl általános ('Bug fix'). A 3. lépés hiányzik a screenshot-hivatkozás.
#    Az audience 'helpdesk', de a megoldás developer zsargont használ
#    (pl. 'restart a worker pool' anélkül, hogy le lenne írva)."
#
# Trace-mód (trace is not None):
#   Ha az Evaluate trace-zel hívja, szigorúbb vagyunk (bootstrap-hez).
#   Ha nem (normál eval), lazább. Ez a dspy konvenció.
#
# Súlyozás (javaslat, finomítandó):
#   score = 0.30*pontosság + 0.25*reprodukálhatóság + 0.20*közönség
#         + 0.15*struktúra + 0.10*tömörség
#
# Megjegyzések:
#   - A feedback-ben LEGYEN KONKRÉTUM (idézet, lépésszám) — nem általános dicséret.
#   - Lehet külön LM a judge-nek (settings.models.reflection vagy saját).
#   - Ha nincs gold article, csak rubrik-alapú (trace Gold nélkül) értékelés.
