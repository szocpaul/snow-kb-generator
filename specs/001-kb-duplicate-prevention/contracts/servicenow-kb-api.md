# Interface Contract: ServiceNow KB API Interactions

This contract describes the new/modified methods on `ServiceNowClient` (`src/snow_kb/servicenow_client.py`) and the FastAPI request schema (`src/snow_kb/server.py`) to support duplicate prevention.

## FastAPI Endpoint: `POST /generate-kb`

**Request Body (Modified):**

```json
{
  "story_id": "STRY0010005",
  "push": true,
  "force_update": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `story_id` | string | (required) | Story number or sys_id. |
| `push` | bool | `true` | Whether to write to the KB. |
| `force_update` | bool | `false` | **NEW.** If true, overwrites an existing linked article instead of erroring. |

**Response (Success):**

```json
{
  "success": true,
  "story_id": "STRY0010005",
  "kb_sys_id": "abc123...",
  "kb_url": "https://...",
  "title": "...",
  "message": "KB article created." | "KB article updated."
}
```

**Response (Duplicate Detected, no force_update):**

```json
{
  "success": false,
  "story_id": "STRY0010005",
  "kb_sys_id": "abc123...",
  "kb_url": "https://...",
  "message": "Duplicate KB article exists. Confirm to update."
}
```
*(HTTP 409 Conflict)*

## `ServiceNowClient` Method Contract

### `find_existing_kb_article(story_number: str) -> str | None`
- **Query**: `GET /api/now/table/kb_knowledge?sysparm_query=u_source_story={story_number}&sysparm_limit=1&sysparm_fields=sys_id`
- **Returns**: The `sys_id` of the existing article, or `None` if not found.

### `create_kb_article(article: KBArticle, story_sys_id: str = "", existing_sys_id: str = "") -> str` (Modified)
- If `existing_sys_id` is provided: Executes `PATCH /api/now/table/kb_knowledge/{existing_sys_id}` with the new `short_description` and `text`. Returns the `existing_sys_id`.
- If `existing_sys_id` is empty: Executes `POST /api/now/table/kb_knowledge` (current behavior), ensuring `u_source_story` is set in the payload. Returns the new `sys_id`.
