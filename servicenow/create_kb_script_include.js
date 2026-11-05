// ============================================================================
// Script Include: SnowKbGenerator
// ============================================================================
// This script must be copied into a new Script Include record in ServiceNow.
// Name: SnowKbGenerator
// Client callable: true (because of the UI Action GlideAjax call)
//
// This script runs on the server and makes an HTTP REST call to the FastAPI
// pipeline.
// ============================================================================

var SnowKbGenerator = Class.create();
SnowKbGenerator.prototype = {
    initialize: function() {
        // --- SETTINGS ---
        // Put your FastAPI server address and API key here!
        this.API_URL = 'http://YOUR_VPS_IP:8000/generate-kb';
        this.API_KEY = 'YOUR_API_KEY_HERE';
    },

    /**
     * Starts the KB generation for the given Story.
     * @param {string} storyId - The Story number (e.g. STRY0010012)
     * @param {string} storySysId - The Story sys_id
     * @return {string} JSON response {success, kb_url, title, message}
     */
    generateKb: function(storyId, storySysId) {
        // Assemble the HTTP request body
        var requestBody = JSON.stringify({
            story_id: storyId,
            push: true
        });

        // REST call to the FastAPI server
        var restMessage = new sn_ws.RESTMessageV2();
        restMessage.setEndpoint(this.API_URL);
        restMessage.setHttpMethod('POST');
        restMessage.setRequestHeader('Content-Type', 'application/json');
        restMessage.setRequestHeader('X-API-Key', this.API_KEY);
        restMessage.setRequestBody(requestBody);

        // Set the timeout (60 seconds — the GLM generation takes time)
        restMessage.setRequestTimeout(60000);

        var response = restMessage.execute();
        var httpStatus = response.getStatusCode();
        var responseBody = response.getBody();

        // Process the response
        if (httpStatus === 200) {
            var result = JSON.parse(responseBody);

            // If successful, put the KB link into the Story's work_notes field
            if (result.success && result.kb_url) {
                this._addWorkNote(storySysId, "KB article created: " + result.kb_url + " (" + result.title + ")");
            }

            return JSON.stringify(result);
        } else {
            // Error
            var errorMsg = 'HTTP ' + httpStatus + ': ' + responseBody;
            this._addWorkNote(storySysId, "KB article generation FAILED: " + errorMsg.substring(0, 200));
            return JSON.stringify({
                success: false,
                message: errorMsg
            });
        }
    },

    /**
     * Adds a work note to the Story.
     * @param {string} storySysId - The Story sys_id
     * @param {string} note - The work note text
     */
    _addWorkNote: function(storySysId, note) {
        try {
            var gr = new GlideRecord('rm_story');
            if (gr.get(storySysId)) {
                // update the work_notes field
                gr.work_notes = gr.getValue('work_notes') + '\n' + note;
                gr.update();
            }
        } catch (ex) {
            // If there is an error while writing the work note, we do not throw
            gs.log('SnowKbGenerator work_note error: ' + ex.message);
        }
    },

    type: 'SnowKbGenerator'
};
