// ============================================================================
// UI Action Script: Create KB Article (SERVER-SIDE)
// ============================================================================
// This script runs on the ServiceNow server and calls our
// FastAPI server on the VPS. It handles the 200, 409 (Duplicate),
// 422 (Missing Group) and other error codes.
// ============================================================================

// 1. The 'current' variable automatically contains the opened Story
var storyId = current.number;

// --- SETTINGS ---
// The key matches the .env SNOW_WEBHOOK_API_KEY field. Provide the real value
// in ServiceNow (UI Action property or Script Include global); in the repo
// there is only a placeholder.
var apiUrl = 'http://192.0.2.10:8000/generate-kb';
var apiKey = 'REPLACE_WITH_RANDOM_KEY';

// 2. Build the payload
var payload = {};
payload.story_id = storyId + ''; // coerce to string
payload.push = true;
// By clicking the UI Action button the user has already approved the generation,
// so we send force_update=true to overwrite an existing article if there is one.
payload.force_update = true; 

// 3. Start the REST call to our VPS server
var restMessage = new sn_ws.RESTMessageV2();
restMessage.setEndpoint(apiUrl);
restMessage.setHttpMethod('POST');
restMessage.setRequestHeader('Content-Type', 'application/json');
restMessage.setRequestHeader('X-API-Key', apiKey);
restMessage.setRequestBody(JSON.stringify(payload));
restMessage.setRequestTimeout(120000); // 120 second timeout because the GLM generation takes time

var response = restMessage.execute();
var httpStatus = response.getStatusCode();
var responseBody = response.getBody();

// 4. Process the response based on the HTTP status code
if (httpStatus === 200) {
    // Successful generation or update
    var result = JSON.parse(responseBody);
    if (result.success && result.kb_url) {
        current.work_notes = "KB article created/updated: " + result.kb_url + " (" + result.title + ")";
    } else {
        current.work_notes = "KB generation finished, but response was invalid.";
    }
} else if (httpStatus === 422) {
    // Unprocessable Entity (e.g. the Assignment Group is missing)
    var errData = JSON.parse(responseBody).detail;
    current.work_notes = "Generation aborted: " + (errData.message || 'Missing mandatory data (e.g. Assignment Group).');
    gs.addErrorMessage("Error: the Assignment Group field is mandatory for the Story!");
} else if (httpStatus === 409) {
    // Conflict (a KB article already exists for the Story)
    current.work_notes = "Warning: a KB article already exists for this Story. Clicking the button again overwrites the existing one.";
    gs.addInfoMessage("A KB article already exists. Click the button again to overwrite it!");
} else {
    // Other errors (e.g. 500 Internal Server Error, or 0 Connection Refused)
    current.work_notes = "An error occurred (HTTP " + httpStatus + "): " + responseBody.substring(0, 150);
    gs.addErrorMessage("Error during generation (HTTP " + httpStatus + ")");
}

// 5. Navigation setting: keep the Story open after the update
action.setRedirectURL(current);
action.setReturnURL(current);
