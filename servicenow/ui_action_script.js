// ============================================================================
// UI Action Script: Create KB Article (SERVER-SIDE)
// ============================================================================
// This script has to be copied into the "Script" field of the UI Action.
// IMPORTANT: The "Client" field on the UI Action record must be UNCHECKED (false)!
// This is a server-side script, so it avoids the asynchronous limitations of GlideAjax
// and it works exactly like a background script (sys.scripts.do).
// ============================================================================

// 1. The 'current' variable automatically contains the opened Story
var storyId = current.number;
var storySysId = current.sys_id;

// --- SETTINGS ---
var apiUrl = 'http://192.0.2.10:8000/generate-kb';
var apiKey = 'REPLACE_WITH_RANDOM_KEY';

// 2. Starting the REST call to our VPS server
// We use the ServiceNow built-in JSON encoder for stability
var payload = {};
payload.story_id = storyId + ''; // coerce to string
payload.push = true;
payload.force_update = false; // By default we do not overwrite

// Duplicate handling: first we check whether an article already exists
var restMessage = new sn_ws.RESTMessageV2();
restMessage.setEndpoint(apiUrl);
restMessage.setHttpMethod('POST');
restMessage.setRequestHeader('Content-Type', 'application/json');
restMessage.setRequestHeader('X-API-Key', apiKey);
restMessage.setRequestBody(new JSON().encode(payload));
restMessage.setRequestTimeout(120000); // 120 second timeout because the GLM generation takes time

var response = restMessage.execute();
var httpStatus = response.getStatusCode();
var responseBody = response.getBody();

if (httpStatus === 409) {
    // US2/US3: Duplicate detected. We ask the user.
    var dupData = JSON.parse(responseBody).detail;
    var kbUrl = dupData.kb_url;
    
    // User confirmation (UI Action specific)
    // Since we run on the server side, confirm() does not work directly.
    // Instead we write the information into work_notes, and on the next button press
    // (force_update=true) is what is sent.
    current.work_notes = "Warning: a KB article already exists for this Story: " + kbUrl +
                         ". If you want to regenerate, click the button again (the system will overwrite it).";
    current.update();
    gs.addInfoMessage("A KB article already exists. See the work_notes field. Click the button again to regenerate.");
    
} else if (httpStatus === 200) {
    var result = JSON.parse(responseBody);
    if (result.success && result.kb_url) {
        // 3. On successful generation put the link into the Story work_notes field
        // We do NOT call current.update()!
        current.work_notes = "KB article created: " + result.kb_url + " (" + result.title + ")";
    }
} else {
    // If the server returned a 500 or another error code
    current.work_notes = "KB article generation FAILED: HTTP " + httpStatus + " - " + responseBody.substring(0, 200);
    gs.addErrorMessage("Error during generation (HTTP " + httpStatus + ")");
}

// 4. Setting the redirect: stay on the Story after the refresh
action.setRedirectURL(current);
action.setReturnURL(current);
