# Research: KB Duplicate Prevention & Update

## Decision: Use a dedicated custom field (`u_source_story`) for linkage

**Rationale**: Querying the `work_notes` string (Option A from spec clarification) is brittle because journal fields can be edited or cleared. Querying the KB title (Option B) is unreliable because the GLM generates slightly different titles each time. A dedicated metadata field on the `kb_knowledge` table provides an exact, programmatic 1:1 link between a Story and its KB article, surviving work_notes edits and title variations.

## Decision: Use PATCH (sys_id-targeted) to update existing articles

**Rationale**: When the user confirms regeneration (Spec FR-006), the system must "overwrite the content of the existing article record (same system identifier)". The ServiceNow Table API supports `PATCH /api/now/table/kb_knowledge/{sys_id}` to update specific fields (`short_description`, `text`) in place without altering the `sys_id` or creating a version conflict. This aligns with Constitution Principle V (centralized HTTP).

## Decision: Handle UI confirmation server-side via a `force_update` boolean

**Rationale**: The ServiceNow UI Action script runs synchronously on the server. Rather than implementing a complex multi-step async handshake, the UI Action script will contain a simple `if (existing_article) { confirm() }` logic. If confirmed, it sends `{"story_id": "...", "push": true, "force_update": true}` to the FastAPI server. This keeps the transport (`server.py`) simple and pushes the business logic to `pipeline.py` (Constitution Principle I).

## Alternatives Considered

- **ServiceNow Flow Designer for confirmation UI**: Rejected. Requires premium subscription features and is harder to version-control than the existing UI Action script approach.
- **Creating a new KB article and retiring the old one**: Rejected per spec clarification. The user explicitly chose to update the existing article in place to avoid clutter.
