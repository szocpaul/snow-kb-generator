# ServiceNow UI Action: "Create KB"

This folder contains the ServiceNow-side scripts that you have to copy
a ServiceNow instance-odra (UI Action record + script).
**These do not run on our server** — they run on the ServiceNow server.

## Installation

### 1. Collect the data

You will need the details of your FastAPI server:
- **API URL**: pl. `http://your-vps-ip:8000/generate-kb`
- **API Key**: the `SNOW_WEBHOOK_API_KEY` that you put into the `.env`

### 2. Creating the UI Action record

Open ServiceNow and create a new UI Action record:

- **Name**: `Create KB Article`
- **Table**: `rm_story` (or `story`, depending on which one exists on your instance)
- **Client**: `true` (client-side script)
- **Onclick**: `createKbArticle()` (the name of the Client Script that you find below)
- **Condition**: `current.state == '3' || current.state == 'Closed Complete'`
  (The button should appear only on closed Stories)

### 3. Client Script (into the UI Action Script field)

Copy the content of `create_kb_client_script.js` into the "Script" field of the UI Action.
Do not forget to change the `API_URL` and `API_KEY` values in it!

## How does it work?

1. The developer opens a closed Story.
2. The "Create KB Article" button appears at the top of the Story form.
3. When the button is clicked, on the ServiceNow client side (in the browser) a `GlideAjax`
   call, which on the server side calls a Script Include.
4. The Script Include (on the ServiceNow server side) makes a REST call to the FastAPI
   szerverednek (`POST /generate-kb`).
5. The FastAPI server runs the pipeline and creates the KB article.
6. The Script Include gets back the KB article link and writes it into the Story
   into the `work_notes` field.

> **Note:** The `create_kb_script_include.js` is a Script Include that must be
> you must create in ServiceNow, because the client-side script cannot directly
> called by a separate external URL (for CORS and security reasons). The Script Include runs on the
> on the server, and there a REST call can already be made.
