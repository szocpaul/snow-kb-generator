# schemas.py — Pydantic adatmodellek (TERV, nincs implementálva)
# ===========================================================================
#
# Felelősség: a ServiceNow-ból jövő és a pipeline-ban keletkező adatok
# típusos szerződése. A DSPy Signatures és a Client is ezekre hivatkoznak.
#
# Megjegyzés: a mezőnevek véglegesítése a signatures-tervvel KÖZÖSEN történik.
# Ez csak a tervezett alak; semmi sem kötelező még.
#
# Tervezett osztályok:
#
#   StoryData
#     A ServiceNow-ból lekért Story (a config.story_fields mezői).
#     short_description: str
#     description: str
#     acceptance_criteria: str
#     work_notes: str              # egyesített journal bejegyzések
#     comments: str                # egyesített kommentek
#     state: str                   # pl. "Closed Complete"
#     number: str                  # pl. "STRY0012345"
#     sys_id: str
#     assigned_to: str             # display value
#
#   ArticleSections
#     A pipeline köztes állapota (a Draft lépés kimenete, a Format lépés bemenete).
#     title: str
#     problem: str                 # mi volt a probléma / miért kellett
#     solution_steps: list[str]    # reprodukálható lépések, sorszámozva
#     summary: str                 # 1-2 mondatos absztrakt
#     audience: str                # helpdesk | end-user | dev
#
#   KBArticle
#     A végső, ServiceNow-ba írandó cikk.
#     title: str
#     html: str                    # ServiceNow-kompatibilis HTML
#     category: str
#     knowledge_base_id: str       # a settings-ből jön alapból
#
# Tervezett enumok (Literal vagy Enum):
#   Audience = Literal["helpdesk", "end-user", "developer"]
#
# Validációs elvek (később field_validator-ral):
#   - solution_steps nem lehet üres lista
#   - html tartalmazzon legalább egy <p> vagy <ol>
#   - title 8..120 karakter
