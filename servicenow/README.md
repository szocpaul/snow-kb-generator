# ServiceNow UI Action: "Create KB" (server-side solution)

This folder contains the ServiceNow-side script that you must copy into the UI Action record.
**This script runs on the ServiceNow server** and calls our FastAPI server on the VPS directly from there. (Much more stable than GlideAjax calls started from the browser).

## Installation steps

### 1. Create the UI Action record
Open ServiceNow and create a new UI Action record (System UI > UI Actions > New).

Fill it in like this:
- **Name:** `Create KB Article`
- **Table:** `rm_story`
- **Client:** `false` (NO checkmark! This is critical, it will run server-side)
- **Form button:** `true` (so that the button is visible)
- **Condition:** `current.state == '3'` (only show it on closed Stories)

### 2. Paste the script
Paste the content of the `ui_action_script.js` file into the UI Action **"Script"** field.

**Check the settings in the script:**
- `apiUrl`: your server address and port (in the repo you only see a placeholder: `http://192.0.2.10:8000/generate-kb`)
- `apiKey`: your server API key — the value of the `.env` field `SNOW_WEBHOOK_API_KEY`. Generate with: `openssl rand -hex 32`. NEVER write the real key into the repo.

### 3. Operation
When a developer presses the button on a closed Story:
1. The ServiceNow server assembles the Story identifier.
2. It sends a REST POST request to your VPS server.
3. The VPS server (FastAPI + DSPy + GLM) generates the KB article.
4. The generated article is uploaded to the ServiceNow KB immediately.
5. The server returns the article URL to ServiceNow.
6. The script automatically writes the KB article link into the Story's `work_notes` field.
7. A success message appears on the screen.

## Troubleshooting
- **Connection refused:** check whether port 8000 is allowed through the VPS firewall (UFW / Hetzner Cloud).
- **Timeout:** generating with the GLM-5.2 model takes 10-20 seconds. The timeout in the script is set to 120 seconds (`120000` ms), which is more than enough.
