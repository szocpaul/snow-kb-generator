// ============================================================================
// UI Action Client Script: Create KB Article
// ============================================================================
// Ezt a scriptet a UI Action "Script" mezőjébe kell másolni.
// A script a böngészőben fut, amikor a felhasználó a gombra kattint.
// ============================================================================

function createKbArticle() {
    // Megerősítés
    var answer = confirm("Biztosan generálni szeretnél egy KB cikket ehhez a Story-hoz?");
    if (!answer) {
        return;
    }

    // Lekérjük a Story számát és sys_id-ját
    var storyNumber = g_form.getValue('number');
    var storySysId = g_form.getUniqueValue();

    // Üzenet a felhasználónak
    g_form.addInfoMessage("KB cikk generálása folyamatban... ez eltarthat 15-20 másodpercig.");

    // A gomb letiltása, amíg fut
    var action = g_form.getControl('create_kb_article'); // UI Action sys_id vagy név
    if (action) {
        action.disabled = true;
    }

    // GlideAjax hívás a Script Include-hoz
    // (A kliens nem hívhat külső URL-t biztonsági okokból,
    // ezért a szerver oldali Script Include-ot hívjuk)
    var ga = new GlideAjax('SnowKbGenerator');
    ga.addParam('sysparm_name', 'generateKb');
    ga.addParam('sysparm_story_id', storyNumber);
    ga.addParam('sysparm_story_sys_id', storySysId);
    ga.getXML(callBack);

    function callBack(response) {
        // A gomb újra engedélyezése
        if (action) {
            action.disabled = false;
        }

        var result;
        try {
            // A ServiceNow GlideAjax válaszát biztonságosan olvassuk ki
            var answerText = response.responseXML.documentElement.getAttribute('answer');
            
            // Ha a ServiceNow duplán escape-elte a JSON-t (gyakori hiba)
            if (typeof answerText === 'string' && answerText.startsWith("{")) {
                result = JSON.parse(answerText);
            } else {
                // Ha valamiért mégis objektumként jön
                result = answerText;
            }
        } catch (e) {
            g_form.addErrorMessage("Hiba a szerver válaszának feldolgozásakor: " + e.message);
            return;
        }

        if (result && result.success) {
            // Sikeres generálás
            var kbUrl = result.kb_url || '';
            var title = result.title || 'KB cikk';

            // Link megjelenítése
            if (kbUrl) {
                g_form.addInfoMessage("KB cikk létrehozva: <a href='" + kbUrl + "' target='_blank'>" + title + "</a>");
            } else {
                g_form.addInfoMessage("KB cikk generálva (push nélkül): " + title);
            }

            // Oldal újratöltése, hogy frissüljön a work_notes mező (megtörtént a szerver oldalon)
            window.location.reload();
        } else {
            // Hiba
            var errorMsg = (result && result.message) ? result.message : 'Ismeretlen hiba történt a generálás során.';
            g_form.addErrorMessage("Hiba: " + errorMsg);
        }
    }
}
