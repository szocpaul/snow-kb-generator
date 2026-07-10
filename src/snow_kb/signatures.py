# signatures.py — DSPy Signatures (DESIGN, not implemented)
# ===========================================================================
#
# Responsibility: to describe the Input/Output contracts of the pipeline steps.
# Every instruction comes from the Signature class docstring — THERE ARE NO
# hardcode-olt prompt-string.
#
# Planned Signatures (reconciling field names with schemas.py):
#
#   ExtractChange
#     """Analyze a completed ServiceNow Story and extract what changed,
#        for whom, and the reproducible steps."""
#     Input:  story_text: str          # the full Story text (merged)
#     Output:  change_summary: str      # what changed, 1-2 sentences
#                key_steps: list[str]    # reproducible steps
#                audience: str           # helpdesk | end-user | dev
#     Predictor: ChainOfThought (reasoning needed for the extraction)
#
#   DraftSections
#     """Draft Knowledge Base article sections from the extracted change info,
#        tailored to the audience."""
#     Input:  change_summary, key_steps, audience
#     Output:  title, problem, solution_steps (list[str]), summary
#     Prediktor: ChainOfThought
#
#   FormatKB
#     """Format drafted sections into ServiceNow-compatible HTML."""
#     Input:  title, problem, solution_steps, summary
#     Output:  html: str
#     Predictor: Predict (transformation, no reasoning needed)
#
# Open questions (decision in the implementation step):
#   - Should ExtractChange get a single story_text, or the Story fields
#     as a separate InputField (short_description, description, ...)?
#       -> separate fields are more accurate, but they increase the size of the Signature.
#   - key_steps / solution_steps: list[str] vagy egyetlen Markdown-string?
#       -> list[str] is clean, but requires a DSPy Pydantic type.
#   - Should category / knowledge_base be determined in the pipeline, or come from the config?
#       -> by default config, but ExtractChange can optionally suggest it.
#   - Should there be a separate Signature for title generation (the title is often critical)?
#
# GEPA consideration: every Signature goes into its own predictor in program.py,
#   named, so that GEPA can target them separately.
