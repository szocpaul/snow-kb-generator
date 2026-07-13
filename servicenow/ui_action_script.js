// ============================================================================
// UI Action Script: Create KB Article (SERVER-SIDE)
// ============================================================================
// This script has to be copied into the "Script" field of the UI Action.
// IMPORTANT: The "Client" field on the UI Action record must be UNCHECKED (false)!
// ============================================================================

// 1. The 'current' variable automatically contains the opened Story
var storyId = current.number;
var storySysId = current.sys_id;

// --- SETTINGS ---
var apiUrl = 'http://192.0.2.10:8000/generate-kb';
var apiKey = 'REPLACE_WITH_RANDOM_KEY';

// 2. Starting the REST call to our VPS server
var payload = {};
payload.story_id = storyId + ''; // coerce to string
payload.push = true;

// Using the standard JSON.stringify
var requestBody = JSON.stringify(payload);

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
            // We do NOT call current.update()!
            // After the UI Action has run, ServiceNow automatically saves the form,
            // so we avoid the double work_notes entry.
            current.work_notes = "KB article created: " + result.kb_url + " (" + result.title + ")";
        } else {
            current.work_notes = "KB article generation failed: Invalid server response.";
            gs.addErrorMessage("Error: the server response was invalid.");
        }
    } else {
        // If the server returned a 500 or another error code
        current.work_notes = "KB article generation FAILED: HTTP " + httpStatus + " - " + responseBody.substring(0, 200);
        gs.addErrorMessage("Error during generation (HTTP " + httpStatus + ")");
    }
} catch (ex) {
    current.work_notes = "KB script exception: " + ex.message;
    gs.addErrorMessage("An exception was thrown during the REST call: " + ex.message);
}

// 4. Setting the redirect: stay on the Story after the refresh
action.setRedirectURL(current);
action.setReturnURL(current);
