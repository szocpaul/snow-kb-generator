# Quickstart: KB Duplicate Prevention Validation

This guide describes how to validate the duplicate prevention feature end-to-end.

## Prerequisites

- The FastAPI server is running (e.g., `uvicorn snow_kb.server:app`).
- The ServiceNow instance has the new `u_source_story` field on the `kb_knowledge` table.
- The updated UI Action script is deployed.
- The pytest suite is green (baseline validation).

## Validation Scenario 1: First-Time Creation (No Duplicate)

1. Open a completed Story that has no linked KB article.
2. Click "Create KB Article".
3. **Expected**: A new KB article is created. Its `u_source_story` field contains the Story number. The Story work_notes contain the link.

## Validation Scenario 2: Duplicate Prevention (Abort)

1. Open the Story from Scenario 1 (which now has a linked article).
2. Click "Create KB Article".
3. When the confirmation dialog appears, select **Cancel**.
4. **Expected**: No API call is made to the server. The work_notes remain unchanged. No new article exists.

## Validation Scenario 3: Regeneration (Update in Place)

1. Open the Story from Scenario 1.
2. Click "Create KB Article".
3. When the confirmation dialog appears, select **OK / Confirm**.
4. **Expected**: The pipeline regenerates the content. The *existing* KB article (same `sys_id`) is updated with the new title and HTML body. The total number of KB articles linked to this Story remains exactly **1**.

## Automated Validation

Run the test suite to verify the logic programmatically:

```bash
pytest tests/test_servicenow_client.py -v -k "existing or update"
pytest tests/test_pipeline.py -v -k "force_update or duplicate"
```

All tests must pass without hitting the live ServiceNow instance or the GLM API.
