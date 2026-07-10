# dataset.py — train/val/test halmazok (TERV, nincs implementálva)
# ===========================================================================
#
# Felelősség: gold (Story -> KB) példapárokból DSPy Example halmazokat
# építeni a baseline-hoz és a GEPA optimalizációhoz.
#
# Forrás (tervezett):
#   data/examples/*.json — minden fájl egy példapár:
#     {
#       "story": { ...StoryData mezők... },
#       "gold_article": { "title", "html", "category", ... }
#     }
#   Ezeket kézzel vagy már meglévő KB cikkekből gyűjtjük.
#
# Tervezett függvények:
#
#   load_examples(path="data/examples") -> list[dspy.Example]:
#       Beolvassa a JSON-eket, példánként:
#         ex = dspy.Example(
#                story_text=assemble_story_text(story),
#                article=KBArticle(**gold_article)
#              ).with_inputs("story_text")
#       Csak a program bemenet-mezőjét ("story_text") jelöljük inputnak.
#
#   split_examples(examples, train=0.6, val=0.2, test=0.2, seed=0)
#       -> (trainset, valset, testset)
#       Stratified split az audience / category alapján, ha lehet.
#
# GEPA-specifikus elvek (dspy-evaluation-harness):
#   - trainset minél nagyobb (GEPA sok példát igényel)
#   - valset csak a downstream viselkedés reprezentálására elég nagy
#   - testset ELREJTVE — csak a végén, jelentéshez használjuk
#
# Megjegyzések:
#   - Ha kevés gold adat van, fake/bootstrap példákat is generálhatunk,
#     de ezeket külön jelöljük (tag: "synthetic"), hogy a valset tisztta maradjon.
#   - Az assemble_story_text formázása EGYSÉGES legyen a pipeline.py-val.
