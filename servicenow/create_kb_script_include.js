// ============================================================================
// Script Include: SnowKbGenerator
// ============================================================================
// Ezt a scriptet egy új Script Include recordba kell másolni a ServiceNow-ban.
// Name: SnowKbGenerator
// Client callable: true (a UI Action GlideAjax hívása miatt)
//
// Ez a script a szerveren fut, és HTTP REST hívást intéz a FastAPI pipeline-hez.
// ============================================================================

var SnowKbGenerator = Class.create();
SnowKbGenerator.prototype = {
    initialize: function() {
        // --- BEÁLLÍTÁSOK ---
        // Ide írd a FastAPI szervered címét és API kulcsát!
        this.API_URL = 'http://YOUR_VPS_IP:8000/generate-kb';
        this.API_KEY = 'YOUR_API_KEY_HERE';
    },

    /**
     * Elindítja a KB generálást a megadott Story-hoz.
     * @param {string} storyId - A Story száma (pl. STRY0010012)
     * @param {string} storySysId - A Story sys_id-ja
     * @return {string} JSON válasz {success, kb_url, title, message}
     */
    generateKb: function(storyId, storySysId) {
        // HTTP kérés összeállítása
        var requestBody = JSON.stringify({
            story_id: storyId,
            push: true
        });

        // REST hívás a FastAPI szerverhez
        var restMessage = new sn_ws.RESTMessageV2();
        restMessage.setEndpoint(this.API_URL);
        restMessage.setHttpMethod('POST');
        restMessage.setRequestHeader('Content-Type', 'application/json');
        restMessage.setRequestHeader('X-API-Key', this.API_KEY);
        restMessage.setRequestBody(requestBody);

        // Timeout beállítása (60 másodperc — a GLM generálás időbe telik)
        restMessage.setRequestTimeout(60000);

        var response = restMessage.execute();
        var httpStatus = response.getStatusCode();
        var responseBody = response.getBody();

        // Válasz feldolgozása
        if (httpStatus === 200) {
            var result = JSON.parse(responseBody);

            // Ha sikeres, belerakjuk a KB linket a Story work_notes mezőjébe
            if (result.success && result.kb_url) {
                this._addWorkNote(storySysId, "KB article created: " + result.kb_url + " (" + result.title + ")");
            }

            return JSON.stringify(result);
        } else {
            // Hiba
            var errorMsg = 'HTTP ' + httpStatus + ': ' + responseBody;
            this._addWorkNote(storySysId, "KB article generation FAILED: " + errorMsg.substring(0, 200));
            return JSON.stringify({
                success: false,
                message: errorMsg
            });
        }
    },

    /**
     * Work note hozzáadása a Story-hoz.
     * @param {string} storySysId - A Story sys_id-ja
     * @param {string} note - A work note szövege
     */
    _addWorkNote: function(storySysId, note) {
        try {
            var gr = new GlideRecord('rm_story');
            if (gr.get(storySysId)) {
                // work_notes mező frissítése
                gr.work_notes = gr.getValue('work_notes') + '\n' + note;
                gr.update();
            }
        } catch (ex) {
            // Ha hiba van a work note írásakor, nem dobunk kivételt
            gs.log('SnowKbGenerator work_note error: ' + ex.message);
        }
    },

    type: 'SnowKbGenerator'
};
