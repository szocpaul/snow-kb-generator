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
// A ServiceNow beépített JSON encoder-ét használjuk a stabilitás miatt
var payload = {};
payload.story_id = storyId + ''; // string-ként kényszerítés
payload.push = true;
payload.force_update = false; // Alapból nem írunk felül

// Duplikáció kezelése: először megnézzük, van-e már cikk
var restMessage = new sn_ws.RESTMessageV2();
restMessage.setEndpoint(apiUrl);
restMessage.setHttpMethod('POST');
restMessage.setRequestHeader('Content-Type', 'application/json');
restMessage.setRequestHeader('X-API-Key', apiKey);
restMessage.setRequestBody(new JSON().encode(payload));
restMessage.setRequestTimeout(120000); // 120 másodperc timeout a GLM generálás miatt

var response = restMessage.execute();
var httpStatus = response.getStatusCode();
var responseBody = response.getBody();

if (httpStatus === 409) {
    // US2/US3: Duplikáció észlelve. Megkérdezzük a felhasználót.
    var dupData = JSON.parse(responseBody).detail;
    var kbUrl = dupData.kb_url;
    
    // Felhasználó megerősítése (UI Action specifikus)
    // Mivel szerver oldalon futunk, a confirm() nem működik közvetlenül.
    // Ehelyett a work_notes-ba írjuk az információt, és egy újabb gombnyomásra 
    // (force_update=true) kerül sor.
    current.work_notes = "Figyelem: Ehhez a Story-hoz már létezik KB cikk: " + kbUrl + 
                         ". Ha újra generálni szeretnéd, kattints a gombra mégegyszer (a rendszer felül fogja írni).";
    current.update();
    gs.addInfoMessage("Már létezik KB cikk. Lásd a work_notes mezőt. Újrageneráláshoz kattints a gombra mégegyszer.");
    
} else if (httpStatus === 200) {
    var result = JSON.parse(responseBody);
    if (result.success && result.kb_url) {
        // 3. Sikeres generálás esetén a link berakása a Story work_notes mezőjébe
        // NEM hívjuk a current.update()-et! 
        current.work_notes = "KB article created: " + result.kb_url + " (" + result.title + ")";
    }
} else {
    // Ha a szerver 500-as vagy más hibakódot adott vissza
    current.work_notes = "KB article generation FAILED: HTTP " + httpStatus + " - " + responseBody.substring(0, 200);
    gs.addErrorMessage("Hiba a generálás során (HTTP " + httpStatus + ")");
}

// 4. Irányítás beállítása: maradjon nyitva a Story-n a frissítés után
action.setRedirectURL(current);
action.setReturnURL(current);
