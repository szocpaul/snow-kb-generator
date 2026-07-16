// ============================================================================
// UI Action Script: Create KB Article (CLIENT-SIDE CONFIRM + SERVER-SIDE REST)
// ============================================================================
// ServiceNow beállítás:
// 1. Client: TRUE (pipa)
// 2. Onclick: confirmCreateKb()
// 3. Script: Másold be ezt a kódot.
// ============================================================================

// --- 1. RÉSZ: KLIENS OLDALI SCRIPT (Böngésző) ---
function confirmCreateKb() {
    // Felugró ablak a felhasználónak
    var answer = confirm("Biztosan generálni szeretnél egy KB cikket ehhez a Story-hoz?\n(Ha már létezik cikk, a rendszer FELÜLÍRJA a régit!)");
    if (!answer) {
        return; // Mégsem
    }
    
    // Átadjuk a szerveroldali scriptnek (az UI Action neve szükséges hozzá)
    // A gomb Action neve (sys_id vagy név) kell ide. Használjuk a 'create_kb_server_action' nevét.
    gsftSubmit(null, g_form.getFormElement(), 'create_kb_server_action');
}

// --- 2. RÉSZ: SZERVER OLDALI SCRIPT (ServiceNow szerver) ---
if (typeof current !== 'undefined' && current !== null) {
    var storyId = current.number;
    
    // --- BEÁLLÍTÁSOK ---
    var apiUrl = 'http://91.99.175.157:8000/generate-kb';
    var apiKey = 'snow-kb-test-key-2024';
    
    // Mivel a felhasználó már rányomott az OK gombra a confirm ablakban,
    // a szerver mindig force_update=true-t küld (így nincs felesleges 409-es kör).
    var payload = {};
    payload.story_id = storyId + '';
    payload.push = true;
    payload.force_update = true; 
    
    var restMessage = new sn_ws.RESTMessageV2();
    restMessage.setEndpoint(apiUrl);
    restMessage.setHttpMethod('POST');
    restMessage.setRequestHeader('Content-Type', 'application/json');
    restMessage.setRequestHeader('X-API-Key', apiKey);
    restMessage.setRequestBody(JSON.stringify(payload));
    restMessage.setRequestTimeout(120000);
    
    var response = restMessage.execute();
    var httpStatus = response.getStatusCode();
    var responseBody = response.getBody();
    
    if (httpStatus === 200) {
        var result = JSON.parse(responseBody);
        if (result.success && result.kb_url) {
            current.work_notes = "KB article created/updated: " + result.kb_url + " (" + result.title + ")";
        } else {
             current.work_notes = "KB generation response error.";
        }
    } else if (httpStatus === 422) {
        // US2 (Team Feature): Hiányzó Assignment Group
        var errData = JSON.parse(responseBody).detail;
        current.work_notes = "Generálás megszakítva: " + (errData.message || 'Hiányzó csapat adat.');
        gs.addErrorMessage("Hiba: A Story-n kötelező az Assignment Group mező!");
    } else {
        current.work_notes = "KB article generation FAILED: HTTP " + httpStatus + " - " + responseBody.substring(0, 200);
        gs.addErrorMessage("Hiba a generálás során (HTTP " + httpStatus + ")");
    }
    
    action.setRedirectURL(current);
}
