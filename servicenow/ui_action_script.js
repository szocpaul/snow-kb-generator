// ============================================================================
// UI Action Script: Create KB Article (SERVER-SIDE)
// ============================================================================
// Ez a script a ServiceNow szerverén fut, és közvetlenül onnan hívja meg a 
// VPS-en lévő FastAPI szerverünket. Kezeli a 200, 409 (Duplicate), 
// 422 (Missing Group) és egyéb hibakódokat.
// ============================================================================

// 1. A 'current' változó automatikusan a megnyitott Story-t tartalmazza
var storyId = current.number;

// --- BEÁLLÍTÁSOK ---
var apiUrl = 'http://91.99.175.157:8000/generate-kb';
var apiKey = 'snow-kb-test-key-2024';

// 2. Payload összeállítása
var payload = {};
payload.story_id = storyId + ''; // string-ként kényszerítés
payload.push = true;
// A UI Action gombra kattintva a felhasználó már jóváhagyta a generálást,
// ezért a force_update=true-t küldjük, hogy felülírja a régit, ha van.
payload.force_update = true; 

// 3. REST hívás indítása a VPS szerverünknek
var restMessage = new sn_ws.RESTMessageV2();
restMessage.setEndpoint(apiUrl);
restMessage.setHttpMethod('POST');
restMessage.setRequestHeader('Content-Type', 'application/json');
restMessage.setRequestHeader('X-API-Key', apiKey);
restMessage.setRequestBody(JSON.stringify(payload));
restMessage.setRequestTimeout(120000); // 120 másodperc timeout a GLM generálás miatt

var response = restMessage.execute();
var httpStatus = response.getStatusCode();
var responseBody = response.getBody();

// 4. Válasz feldolgozása a HTTP státuszkód alapján
if (httpStatus === 200) {
    // Sikeres generálás vagy frissítés
    var result = JSON.parse(responseBody);
    if (result.success && result.kb_url) {
        current.work_notes = "KB article created/updated: " + result.kb_url + " (" + result.title + ")";
    } else {
        current.work_notes = "KB generation finished, but response was invalid.";
    }
} else if (httpStatus === 422) {
    // Unprocessable Entity (pl. hiányzik az Assignment Group)
    var errData = JSON.parse(responseBody).detail;
    current.work_notes = "Generálás megszakítva: " + (errData.message || 'Hiányzó kötelező adat (pl. Assignment Group).');
    gs.addErrorMessage("Hiba: A Story-n kötelező az Assignment Group mező!");
} else if (httpStatus === 409) {
    // Conflict (Már létezik KB cikk a Story-hoz)
    current.work_notes = "Figyelem: Már létezik KB cikk ehhez a Story-hoz. A gomb ismételt megnyomásával a rendszer felül fogja írni a régit.";
    gs.addInfoMessage("Már létezik KB cikk. Kattints a gombra mégegyszer a felülíráshoz!");
} else {
    // Egyéb hibák (pl. 500 Internal Server Error, vagy 0 Connection Refused)
    current.work_notes = "Hiba történt (HTTP " + httpStatus + "): " + responseBody.substring(0, 150);
    gs.addErrorMessage("Hiba a generálás során (HTTP " + httpStatus + ")");
}

// 5. Irányítás beállítása: maradjon nyitva a Story-n a frissítés után
action.setRedirectURL(current);
action.setReturnURL(current);
