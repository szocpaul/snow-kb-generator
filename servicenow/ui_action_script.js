// ============================================================================
// UI Action Script: Create KB Article (SERVER-SIDE)
// ============================================================================

// 1. A 'current' változó automatikusan a megnyitott Story-t tartalmazza
var storyId = current.number;
var storySysId = current.sys_id;

// --- BEÁLLÍTÁSOK ---
var apiUrl = 'http://91.99.175.157:8000/generate-kb';
var apiKey = 'snow-kb-test-key-2024';

// 2. Force update olvasása. Biztosra megyünk: string konvertálás és trim.
var forceUpdateRaw = current.getValue('u_kb_force_update');
var forceUpdate = false;
if (forceUpdateRaw !== null && (forceUpdateRaw.toString().trim() === 'true' || forceUpdateRaw === true || forceUpdateRaw === '1')) {
    forceUpdate = true;
}

var payload = {};
payload.story_id = storyId + '';
payload.push = true;
payload.force_update = forceUpdate;

// 3. REST hívás indítása
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

// 4. Válasz feldolgozása
if (httpStatus === 409) {
    // Duplikáció! Beállítjuk a flag-et true-ra, hogy a következő kattintás felülírjon.
    current.setValue('u_kb_force_update', 'true');
    current.work_notes = "Ehhez a Story-hoz már létezik KB cikk. A gomb ismételt megnyomásával a rendszer FELÜLÍRJA a régit.";
    gs.addInfoMessage("Már létezik KB cikk. A felülíráshoz kattints a gombra MÉGEGYSZER!");
    
} else if (httpStatus === 200) {
    var result = JSON.parse(responseBody);
    if (result.success && result.kb_url) {
        // Sikeres létrehozás vagy frissítés. Reseteljük a flag-et!
        current.setValue('u_kb_force_update', 'false');
        current.work_notes = "KB article created/updated: " + result.kb_url + " (" + result.title + ")";
    }
} else {
    // Hiba esetén is reseteljük
    current.setValue('u_kb_force_update', 'false');
    current.work_notes = "KB article generation FAILED: HTTP " + httpStatus + " - " + responseBody.substring(0, 200);
    gs.addErrorMessage("Hiba a generálás során (HTTP " + httpStatus + ")");
}

action.setRedirectURL(current);
action.setReturnURL(current);
