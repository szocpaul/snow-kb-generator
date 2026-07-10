# schemas.py — Pydantic data models (DESIGN, not implemented)
# ===========================================================================
#
# Responsibility: the data coming from ServiceNow and generated in the pipeline
# typed contract. The DSPy Signatures and the Client also refer to these.
#
# Note: finalizing the field names happens TOGETHER with the signatures design.
# This is only the planned shape; nothing is mandatory yet.
#
# Planned classes:
#
#   StoryData
#     The Story fetched from ServiceNow (the fields of config.story_fields).
#     short_description: str
#     description: str
#     acceptance_criteria: str
#     work_notes: str              # merged journal entries
#     comments: str                # merged comments
#     state: str                   # pl. "Closed Complete"
#     number: str                  # pl. "STRY0012345"
#     sys_id: str
#     assigned_to: str             # display value
#
#   ArticleSections
#     The intermediate state of the pipeline (output of the Draft step, input of the Format step).
#     title: str
#     problem: str                 # what the problem was / why it was needed
#     solution_steps: list[str]    # reproducible steps, numbered
#     summary: str                 # 1-2 mondatos absztrakt
#     audience: str                # helpdesk | end-user | dev
#
#   KBArticle
#     The final article to be written to ServiceNow.
#     title: str
#     html: str                    # ServiceNow-kompatibilis HTML
#     category: str
#     knowledge_base_id: str       # comes from the settings by default
#
# Tervezett enumok (Literal vagy Enum):
#   Audience = Literal["helpdesk", "end-user", "developer"]
#
# Validation principles (later with field_validator):
#   - solution_steps must not be an empty list
#   - html should contain at least one <p> or <ol>
#   - title 8..120 characters
