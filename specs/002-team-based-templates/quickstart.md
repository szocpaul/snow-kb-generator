# Quickstart: Team-Based KB Templates Validation

This guide describes how to validate the team-based template feature end-to-end.

## Prerequisites

- The FastAPI server is running.
- ServiceNow PDI has multiple Knowledge Bases (e.g., "IT", "Network").
- The `kb_knowledge_base.text` fields contain distinct HTML templates/examples for the teams.
- The pytest suite is green.

## Validation Scenario 1: Correct Team Template Usage

1. Open a completed Story with `assignment_group` set to "Network" (or similar).
2. Click "Create KB Article".
3. **Expected**: The system fetches the "Network" KB template. The generated KB article strictly follows the Network team's structure (headings, format) defined in their `text` field.

## Validation Scenario 2: Missing Assignment Group Blocking

1. Open a completed Story.
2. Clear the `assignment_group` field (leave it empty).
3. Click "Create KB Article".
4. **Expected**: The ServiceNow UI Action receives an HTTP 422 error. A message is displayed: "Cannot generate KB: Assignment Group is missing." No article is generated.

## Validation Scenario 3: Dynamic Template Update

1. Go to ServiceNow -> Knowledge -> Knowledge Bases.
2. Open the "Network" KB and modify the `text` field (change the required headings).
3. Save it.
4. Generate a new KB article for a Network Story.
5. **Expected**: The newly generated article reflects the updated template structure immediately.

## Automated Validation

Run the test suite to verify the logic programmatically:

```bash
pytest tests/test_servicenow_client.py -v -k "team_template"
pytest tests/test_pipeline.py -v -k "missing_group"
```

All tests must pass without hitting the live ServiceNow instance or the GLM API.
