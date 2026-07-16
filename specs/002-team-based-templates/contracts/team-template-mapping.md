# Interface Contract: Team Template Mapping

This contract describes how the `assignment_group` links to a template, and the API methods added to support it.

## `ServiceNowClient` Method Contract

### `get_team_template(assignment_group: str) -> str | None`
- **Purpose**: Fetches the team-specific HTML template.
- **Query**: `GET /api/now/table/kb_knowledge_base?sysparm_query=ownership_group={assignment_group_sys_id}&sysparm_limit=1&sysparm_fields=text`
- **Returns**: The `text` field (HTML template) of the matched KB, or `None` if no match is found.
- *(Note: If the instance uses a different mapping logic, e.g., a reference field on `sys_user_group`, the query is adjusted to follow that reference.)*

## FastAPI Endpoint: `POST /generate-kb` (Error Handling)

When the pipeline raises `MissingAssignmentGroupError`:

**Response (Missing Team):**
```json
{
  "detail": {
    "message": "Cannot generate KB: Assignment Group is missing on the Story."
  }
}
```
*(HTTP 422 Unprocessable Entity)*

## Pipeline Orchestration (`pipeline.py`)

1. Fetch Story.
2. Read `story.assignment_group`.
3. If empty: `raise MissingAssignmentGroupError`
4. Call `client.get_team_template(story.assignment_group)`
5. Pass the returned template string to `program(story_text=..., template_context=...)`.
6. Proceed to KB creation/update.
