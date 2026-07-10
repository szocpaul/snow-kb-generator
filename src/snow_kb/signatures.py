# signatures.py — DSPy Signatures (TERV, nincs implementálva)
# ===========================================================================
#
# Felelősség: a pipeline lépéseinek Input/Output szerződéseit leírni.
# Minden utasítás a Signature osztály docstring-jéből jön — NINCSEN
# hardcode-olt prompt-string.
#
# Tervezett Signatures (mezőnevek egyeztetése a schemas.py-val):
#
#   ExtractChange
#     """Analyze a completed ServiceNow Story and extract what changed,
#        for whom, and the reproducible steps."""
#     Bemenet:  story_text: str          # a teljes Story szöveg (összevont)
#     Kimenet:  change_summary: str      # mi változott, 1-2 mondat
#                key_steps: list[str]    # reprodukálható lépések
#                audience: str           # helpdesk | end-user | dev
#     Prediktor: ChainOfThought (indoklás kell a kinyeréshez)
#
#   DraftSections
#     """Draft Knowledge Base article sections from the extracted change info,
#        tailored to the audience."""
#     Bemenet:  change_summary, key_steps, audience
#     Kimenet:  title, problem, solution_steps (list[str]), summary
#     Prediktor: ChainOfThought
#
#   FormatKB
#     """Format drafted sections into ServiceNow-compatible HTML."""
#     Bemenet:  title, problem, solution_steps, summary
#     Kimenet:  html: str
#     Prediktor: Predict (transzformáció, nem kell érvelés)
#
# Nyitott kérdések (döntés az implementációs lépésben):
#   - ExtractChange egyetlen story_text-et kapjon, vagy a Story mezőit
#     külön InputField-ként (short_description, description, ...)?
#       -> külön mezők pontosabbak, de növelik a Signature méretét.
#   - key_steps / solution_steps: list[str] vagy egyetlen Markdown-string?
#       -> list[str] tiszta, de DSPy Pydantic-típust igényel.
#   - category / knowledge_base a pipeline-ban derüljön ki, vagy config-ból jöjjön?
#       -> alapból config, de opcionálisan ExtractChange javasolhat.
#   - Legyen-e külön Signature a cím-generálásra (cím gyakran kritikus)?
#
# GEPA szempont: minden Signature önálló prediktorba kerül a program.py-ban,
#   névvel ellátva, hogy a GEPA külön célozhassa őket.
