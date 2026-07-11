// ============================================================================
// UI Action Client Script: Create KB Article
// ============================================================================
// This script must be copied into the "Script" field of the UI Action.
// The script runs in the browser when the user clicks the button.
// ============================================================================

function createKbArticle() {
    // Confirmation
    var answer = confirm("Do you really want to generate a KB article for this Story?");
    if (!answer) {
        return;
    }

    // Get the Story number and sys_id
    var storyNumber = g_form.getValue('number');
    var storySysId = g_form.getUniqueValue();

    // Message to the user
    g_form.addInfoMessage("KB article generation in progress... this may take 15-20 seconds.");

    // Disable the button while it runs
    var action = g_form.getControl('create_kb_article'); // UI Action sys_id or name
    if (action) {
        action.disabled = true;
    }

    // GlideAjax call to the Script Include
    // (The client must not call an external URL for security reasons,
    // so we call the server-side Script Include)
    var ga = new GlideAjax('SnowKbGenerator');
    ga.addParam('sysparm_name', 'generateKb');
    ga.addParam('sysparm_story_id', storyNumber);
    ga.addParam('sysparm_story_sys_id', storySysId);
    ga.getXML(callBack);

    function callBack(response) {
        // Re-enable the button
        if (action) {
            action.disabled = false;
        }

        var result;
        try {
            // Read the ServiceNow GlideAjax response safely
            var answerText = response.responseXML.documentElement.getAttribute('answer');
            
            // If ServiceNow has double-escaped the JSON (a common error)
            if (typeof answerText === 'string' && answerText.startsWith("{")) {
                result = JSON.parse(answerText);
            } else {
                // If for some reason it still comes as an object
                result = answerText;
            }
        } catch (e) {
            g_form.addErrorMessage("Error while processing the server response: " + e.message);
            return;
        }

        if (result && result.success) {
            // Successful generation
            var kbUrl = result.kb_url || '';
            var title = result.title || 'KB article';

            // Show the link
            if (kbUrl) {
                g_form.addInfoMessage("KB article created: <a href='" + kbUrl + "' target='_blank'>" + title + "</a>");
            } else {
                g_form.addInfoMessage("KB article generated (without push): " + title);
            }

            // Reload the page so the work_notes field is refreshed (it already happened server-side)
            window.location.reload();
        } else {
            // Error
            var errorMsg = (result && result.message) ? result.message : 'An unknown error occurred during generation.';
            g_form.addErrorMessage("Error: " + errorMsg);
        }
    }
}
