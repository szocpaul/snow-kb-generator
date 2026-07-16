# Research: Team-Based KB Templates

## Decision: Map Assignment Group via a Reference Field on KB Knowledge Base

**Rationale**: The `assignment_group` field on the Story (e.g., "Network Team") needs to be mapped to a specific `kb_knowledge_base` record that holds their template. Since team names and KB IDs are instance-specific, we cannot hardcode this mapping in Python, and string matching (title = group name) is brittle.

**Solution**: The ServiceNow `kb_knowledge_base` table will have a custom reference field (e.g., `u_assignment_group`) that points to the `sys_user_group` record. The `servicenow_client.py` will implement `get_team_template(assignment_group)` that queries the KB where `u_assignment_group = {assignment_group_sys_id}` and returns its `text` field. This provides a direct, robust 1:1 link.

## Decision: Pass template as a dynamic `InputField` (Few-Shot)

**Rationale**: The Constitution (Principle II) forbids hardcoded prompts. Instead of baking the Network template into the Signature docstring, we add a new input field `template_context` to the DSPy Signature. The pipeline fetches the HTML text from ServiceNow and passes it dynamically at runtime. DSPy natively supports few-shot examples passed this way.

## Decision: Introduce `errors.py` for custom exceptions

**Rationale**: Blocking the pipeline due to a missing `assignment_group` is a domain-specific error, distinct from a ServiceNow API failure (`ServiceNowError`). Creating a dedicated `MissingAssignmentGroupError` in `src/snow_kb/errors.py` allows the FastAPI server to catch it specifically and return a `422 Unprocessable Entity` with a clear UI message.

## Alternatives Considered

- **Store templates in `config.yaml` on the VPS**: Rejected per user decision (Q1: B). Users want to edit templates directly in ServiceNow.
- **AI guesses the team from Story text**: Rejected per user decision (Q2: C). Assignment Group is mandatory; guessing is unnecessary.
- **Merge the template into the Signature docstring dynamically**: Rejected. Modifying Signature classes at runtime is anti-pattern in DSPy and breaks GEPA optimization. Passing as an `InputField` is the standard approach.
