// ============================================================================
// UI Action Script: Create KB Article (CLIENT-SIDE CONFIRM + SERVER-SIDE REST)
// ============================================================================
// ServiceNow setting:
// 1. Client: TRUE (pipa)
// 2. Onclick: confirmCreateKb()
// 3. Script: Copy this code.
// ============================================================================

// --- 1. PART: CLIENT-SIDE SCRIPT (Browser) ---
function confirmCreateKb() {
    // Popup window for the user
    var answer = confirm("Are you sure you want to generate a KB article for this Story?\n(If an article already exists, the system OVERWRITES the old one!)");
    if (!answer) {
        return; // Never mind
    }
    
    // We pass it to the server-side script (the name of the UI Action is needed for it)
    // The name of the button Action (sys_id or name) is needed here. We use the name 'create_kb_server_action'.
    gsftSubmit(null, g_form.getFormElement(), 'create_kb_server_action');
}

// --- 2. PART: SERVER-SIDE SCRIPT (ServiceNow server) ---
if (typeof current !== 'undefined' && current !== null) {
    var storyId = current.number;
    
    // --- SETTINGS ---
    var apiUrl = 'http://192.0.2.10:8000/generate-kb';
    var apiKey = 'REPLACE_WITH_RANDOM_KEY';
    
    // Since the user has already clicked the OK button in the confirm dialog,
    // the server always sends force_update=true (so there is no unnecessary 409 round trip).
    var payload = {};
    payload.story_id = storyId + '';
    payload.push = true;
    payload.force_update = true; 
    
    var restMessage = new sn_ws.RESTMessageV2();
    restMessage.setEndpoint(apiUrl);
    restMessage.setHttpMethod('POST');
    restMessage.setRequestHeader('Content-Type', 'application/json');
    restMessage.setRequestHeader('X-API-Key', apiKey);
    restMessage.setRequestBody(new JSON().encode(payload));
    restMessage.setRequestTimeout(120000);
    
    var response = restMessage.execute();
    var httpStatus = response.getStatusCode();
    var responseBody = response.getBody();
    
    if (httpStatus === 200) {
        var result = JSON.parse(responseBody);
        if (result.success && result.kb_url) {
            current.work_notes = "KB article created/updated: " + result.kb_url + " (" + result.title + ")";
        } else {
             current.work_notes = "KB generation response error.";
        }
    } else {
        current.work_notes = "KB article generation FAILED: HTTP " + httpStatus + " - " + responseBody.substring(0, 200);
        gs.addErrorMessage("Error during generation (HTTP " + httpStatus + ")");
    }
    
    action.setRedirectURL(current);
}
