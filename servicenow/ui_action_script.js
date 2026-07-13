// ============================================================================
// UI Action Script: Create KB Article (SERVER-SIDE)
// ============================================================================
// Ezt a scriptet az UI Action "Script" mezőjébe kell másolni.
// FONTOS: Az UI Action recordon a "Client" mező legyen KIPIPÁLATLAN (false)!
// Ez egy szerver oldali script, így elkerüli a GlideAjax aszinkron korlátozásait
// és pont úgy működik, mint egy háttérscript (sys.scripts.do).
// ============================================================================

// 1. A 'current' változó automatikusan a megnyitott Story-t tartalmazza
var storyId = current.number;
var storySysId = current.sys_id;

// --- BEÁLLÍTÁSOK ---
var apiUrl = 'http://91.99.175.157:8000/generate-kb';
var apiKey = 'snow-kb-test-key-2024';

// 2. REST hívás indítása a VPS szerverünknek
var requestBody = JSON.stringify({
    story_id: storyId,
    push: true
});

var restMessage = new sn_ws.RESTMessageV2();
restMessage.setEndpoint(apiUrl);
restMessage.setHttpMethod('POST');
restMessage.setRequestHeader('Content-Type', 'application/json');
restMessage.setRequestHeader('X-API-Key', apiKey);
restMessage.setRequestBody(requestBody);
restMessage.setRequestTimeout(120000); // 120 másodperc timeout a GLM generálás miatt

try {
    var response = restMessage.execute();
    var httpStatus = response.getStatusCode();
    var responseBody = response.getBody();

    if (httpStatus === 200) {
        var result = JSON.parse(responseBody);
        
        if (result.success && result.kb_url) {
            // 3. Sikeres generálás esetén a link berakása a Story work_notes mezőjébe
            current.work_notes = "KB article created: " + result.kb_url + " (" + result.title + ")";
            current.update(); // Story mentése
            
            gs.addInfoMessage("KB cikk sikeresen létrehozva: " + result.title);
        } else {
            gs.addErrorMessage("Hiba: A szerver válasza érvénytelen volt.");
        }
    } else {
        // Ha a szerver 500-as vagy más hibakódot adott vissza
        current.work_notes = "KB article generation FAILED: HTTP " + httpStatus + " - " + responseBody.substring(0, 200);
        current.update();
        gs.addErrorMessage("Hiba a generálás során (HTTP " + httpStatus + ")");
    }
} catch (ex) {
    gs.addErrorMessage("Kivétel dobódott a REST hívás során: " + ex.message);
}

// 4. Irányítás beállítása: maradjon nyitva a Story-n a frissítés után
action.setRedirectURL(current);
action.setReturnURL(current);
