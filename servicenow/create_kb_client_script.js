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

        var answer = response.responseXML.documentElement.getAttribute("answer");
        var result = JSON.parse(answer);

        if (result.success) {
            // Sikeres generálás
            var kbUrl = result.kb_url || '';
            var title = result.title || 'KB cikk';

            // Link megjelenítése
            if (kbUrl) {
                g_form.addInfoMessage("KB cikk létrehozva: <a href='" + kbUrl + "' target='_blank'>" + title + "</a>");
            } else {
                g_form.addInfoMessage("KB cikk generálva (push nélkül): " + title);
            }

            // Work notes frissítése
            // (A Script Include már frissíti, de itt is jelezzük)
            g_form.addInfoMessage("A Story work_notes mezője frissítve lett a KB linkkel.");
        } else {
            // Hiba
            var errorMsg = result.message || 'Ismeretlen hiba történt.';
            g_form.addErrorMessage("Hiba a KB cikk generálásakor: " + errorMsg);
        }
    }
}
