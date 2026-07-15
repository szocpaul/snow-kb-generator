# Data Model: KB Duplicate Prevention & Update

## Entity: Knowledge Base Article (`kb_knowledge`)

The existing ServiceNow KB article record gains one new custom field to enable duplicate prevention.

| Field | Type | Description | New? |
|-------|------|-------------|------|
| `sys_id` | String (32) | System identifier (existing). | No |
| `short_description` | String | Article title (existing, updated on regeneration). | No |
| `text` | String (HTML) | Article body (existing, updated on regeneration). | No |
| `knowledge_base` | String (sys_id ref) | Target KB (existing). | No |
| **`u_source_story`** | **String** | **The originating Story number (e.g., `STRY0010005`). Used to detect duplicates.** | **YES** |

## Validation Rules

- **VR-001**: Before creation, the system queries `kb_knowledge` where `u_source_story = {story_number}`.
- **VR-002**: If a record is found, the system MUST NOT create a new record; it MUST update the found `sys_id` (gated by user confirmation).
- **VR-003**: The `u_source_story` field MUST be populated on both initial creation and after any update operation.

## State Transitions

This feature does not introduce new entity states; it alters the *flow* of creation vs. update based on the existence check.
