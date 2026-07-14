# Példa Story az RLM teszteléséhez (Update Set alapján)

Ez a szöveg közvetlenül a te valós integrációs kódodra (Update Set: STRY0010005) épül. 
A Tartalmat csak másold be a megfelelő mezőkbe a ServiceNow Story formon!

---

### Short description
`[KB Generator]: Automate Knowledge Base creation from Stories via AI pipeline`

### Description
`Implemented a fully automated workflow to generate Knowledge Base articles directly from completed ServiceNow Stories. When a developer completes a Story, they can click a UI Action button to send the Story context (including technical specifications and modifications) to an external DSPy/GLM AI pipeline. The pipeline processes the request, generates a formatted HTML KB article, creates it in the ServiceNow KB, and returns the link directly to the Story's work notes.`

### Acceptance criteria
`1. A custom field 'u_technical_specification' is created on the rm_story table to capture deep technical context.
2. A client-callable Script Include 'SnowKbGenerator' exists to handle the REST API integration.
3. A server-side UI Action 'Create KB Article' is available on the Story form, restricted to 'Closed Complete' state.
4. The UI Action successfully updates the Story work_notes with the URL of the newly created KB article.`

### Technical Specification (u_technical_specification)
`The implementation relies on native ServiceNow REST capabilities (sn_ws.RESTMessageV2) communicating with a FastAPI server.
1. The 'SnowKbGenerator' Script Include initializes the API endpoint (http://91.99.175.157:8000/generate-kb) and API key.
2. It uses the native JSON encoder (new JSON().encode()) to construct the payload safely.
3. The POST request includes a 120-second timeout to accommodate the AI generation time.
4. The UI Action script runs server-side, extracts 'current.number', triggers the REST call, parses the JSON response, and writes the 'kb_url' directly into 'current.work_notes' before the automatic form save occurs.`

### Work notes
`2024-07-13 10:00: System - Created Update Set STRY0010005 and marked it as In Progress.
2024-07-13 10:15: System - Added Dictionary and Field Label modifications for 'Technical Specification'.
2024-07-13 10:30: System - Created Script Include 'SnowKbGenerator' with REST outbound logic.
2024-07-13 11:00: System - Created UI Action 'Create KB Article' and configured Form Layout.
2024-07-13 11:30: System - Completed all development tasks. Link to Update Set: https://dev433980.service-now.com/sys_update_set.do?sys_id=f812bd7d2f828310698771ba6fa4e36d`

---
*(Megjegyzés a pipeline-hoz: Bár a szöveg maga kb. 2000 karakter, a te valós `STRY0010005` Update Set-ed 36,000 karakteres! Amikor a gombot megnyomod, a pipeline az Update Set nevét (`STRY0010005`) fogja használni a kód letöltésére és az RLM elindítására.)*
