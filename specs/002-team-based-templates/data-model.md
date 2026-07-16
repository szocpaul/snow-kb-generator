# Data Model: Team-Based KB Templates

## Entity: Story (`rm_story`)

The Story record gains importance as the routing trigger.

| Field | Type | Description | New? |
|-------|------|-------------|------|
| `number` | String | Story number (existing). | No |
| `assignment_group` | String (sys_id ref) | The team responsible. **Used to select the template.** | Existing field, new usage |

## Entity: Knowledge Base (`kb_knowledge_base`)

Acts as the storage entity for the team's specific HTML template.

| Field | Type | Description | New? |
|-------|------|-------------|------|
| `sys_id` | String (32) | System identifier (existing). | No |
| **`ownership_group`** | **Reference (`sys_user_group`)** | **Points to the Assignment Group. This creates the 1:1 mapping.** | **YES (Manual Action)** |
| **`text`** | **String (HTML)** | **Stores the team's template/example article (Few-Shot context).** | Existing field, new usage |

## Validation Rules

- **VR-001**: The pipeline MUST verify `assignment_group` is present on the Story. If missing/empty, raise `MissingAssignmentGroupError`.
- **VR-002**: The pipeline queries `kb_knowledge_base` where `ownership_group` matches the Story's `assignment_group`. If no KB is found, it falls back to default or warns.

## DSPy Signature Context (Logical Model)

The `DraftSections` and `FormatKB` Signatures gain a dynamic input:

| Field | Type | Description |
|-------|------|-------------|
| `template_context` | String | The HTML/text example fetched from the KB `text` field. Acts as a few-shot guide for the LM. |
