// ============================================================================
// UI Action Script: Create KB Article (SERVER-SIDE)
// ============================================================================

// 1. The 'current' variable automatically contains the opened Story
var storyId = current.number;
var storySysId = current.sys_id;

// --- SETTINGS ---
var apiUrl = 'http://192.0.2.10:8000/generate-kb';
var apiKey = 'REPLACE_WITH_RANDOM_KEY';

// 2. Reading the force update. To be safe: string conversion and trim.
var forceUpdateRaw = current.getValue('u_kb_force_update');
var forceUpdate = false;
if (forceUpdateRaw !== null && (forceUpdateRaw.toString().trim() === 'true' || forceUpdateRaw === true || forceUpdateRaw === '1')) {
    forceUpdate = true;
}

var payload = {};
payload.story_id = storyId + '';
payload.push = true;
payload.force_update = forceUpdate;

// 3. Starting the REST call
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

// 4. Processing the response
if (httpStatus === 409) {
    // Duplicate! We set the flag to true so that the next click overwrites it.
    current.setValue('u_kb_force_update', 'true');
    current.work_notes = "A KB article already exists for this Story. Pressing the button again OVERWRITES the old one.";
    gs.addInfoMessage("A KB article already exists. Click the button AGAIN to overwrite it!");
    
} else if (httpStatus === 200) {
    var result = JSON.parse(responseBody);
    if (result.success && result.kb_url) {
        // Successful creation or update. We reset the flag!
        current.setValue('u_kb_force_update', 'false');
        current.work_notes = "KB article created/updated: " + result.kb_url + " (" + result.title + ")";
    }
} else {
    // We reset it also in the error case
    current.setValue('u_kb_force_update', 'false');
    current.work_notes = "KB article generation FAILED: HTTP " + httpStatus + " - " + responseBody.substring(0, 200);
    gs.addErrorMessage("Error during generation (HTTP " + httpStatus + ")");
}

action.setRedirectURL(current);
action.setReturnURL(current);
