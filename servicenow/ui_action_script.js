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

var requestBody = new JSON().encode(payload);

var restMessage = new sn_ws.RESTMessageV2();
restMessage.setEndpoint(apiUrl);
restMessage.setHttpMethod('POST');
restMessage.setRequestHeader('Content-Type', 'application/json');
restMessage.setRequestHeader('X-API-Key', apiKey);
restMessage.setRequestBody(requestBody);
restMessage.setRequestTimeout(120000); // 120 second timeout because the GLM generation takes time

try {
    var response = restMessage.execute();
    var httpStatus = response.getStatusCode();
    var responseBody = response.getBody();

    if (httpStatus === 200) {
        var result = JSON.parse(responseBody);
        
        if (result.success && result.kb_url) {
            // 3. On successful generation put the link into the Story work_notes field
            current.work_notes = "KB article created: " + result.kb_url + " (" + result.title + ")";
            current.update(); // Saving the Story
        } else {
            gs.addErrorMessage("Error: the server response was invalid.");
        }
    } else {
        // If the server returned a 500 or another error code
        current.work_notes = "KB article generation FAILED: HTTP " + httpStatus + " - " + responseBody.substring(0, 200);
        current.update();
        gs.addErrorMessage("Error during generation (HTTP " + httpStatus + ")");
    }
} catch (ex) {
    gs.addErrorMessage("An exception was thrown during the REST call: " + ex.message);
}

// 4. Setting the redirect: stay on the Story after the refresh
action.setRedirectURL(current);
action.setReturnURL(current);
