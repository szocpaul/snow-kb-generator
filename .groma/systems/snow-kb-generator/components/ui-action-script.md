---
type: C4 Component
title: Create KB Article trigger (ServiceNow-side)
status: stable
groma:
  id: ui-action-script
  parent: snow-kb-generator
  code:
    - scanner: javascript
      file: servicenow/ui_action_script.js
    - scanner: javascript
      file: servicenow/create_kb_script_include.js
  technology: ServiceNow server-side JavaScript
description: Scripts that live inside the ServiceNow instance and call the webhook server when a developer clicks the button.
---

Owns servicenow/ui_action_script.js and servicenow/create_kb_script_include.js. The UI Action is the deployed path: a form button on closed Stories (state=3) that POSTs the story id with the API key to the FastAPI server, then writes the returned KB link into work notes and surfaces 409/422 errors to the user. The Script Include is the earlier GlideAjax-style variant kept as a reference. These run in the ServiceNow runtime, not in the Python application; the scanner cannot establish that container boundary, so this component is recorded at system level.
