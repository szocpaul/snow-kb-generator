# ServiceNow UI Action: "Create KB" (Szerveroldali megoldás)

Ez a mappa tartalmazza a ServiceNow-oldali scriptet, amit be kell másolnod az UI Action recordba. 
**Ez a script a ServiceNow szerverén fut**, és közvetlenül onnan hívja meg a VPS-en lévő FastAPI szerverünket. (Sokkal stabilisebb, mint a böngészőből indított GlideAjax hívások).

## Telepítés lépései

### 1. UI Action record létrehozása
Nyisd meg a ServiceNow-t, és hozz létre egy új UI Action recordot (System UI > UI Actions > New).

Töltsd ki így:
- **Name:** `Create KB Article`
- **Table:** `rm_story`
- **Client:** `false` (NINCS pipa! Ez kritikus, szerver oldalon fog futni)
- **Form button:** `true` (Hogy látható legyen a gomb)
- **Condition:** `current.state == '3'` (Csak lezárt Story-kon jelenjen meg)

### 2. Script bemásolása
Másold be az `ui_action_script.js` fájl tartalmát az UI Action **"Script"** mezőjébe.

**Ellenőrizd a scriptben lévő beállításokat:**
- `apiUrl`: A te VPS szervered IP címe és portja (jelenleg: `http://91.99.175.157:8000/generate-kb`)
- `apiKey`: A szerver API kulcsa (jelenleg: `snow-kb-test-key-2024`)

### 3. Működés
Amikor egy fejlesztő megnyomja a gombot a lezárt Story-n:
1. A ServiceNow szerver összerakja a Story azonosítót.
2. Elküld egy REST POST kérést a VPS szerverednek.
3. A VPS szerver (FastAPI + DSPy + GLM) legenerálja a KB cikket.
4. A generált cikk azonnal feltöltődik a ServiceNow KB-be.
5. A szerver visszaadja a cikk URL-jét a ServiceNow-nak.
6. A script automatikusan beírja a KB cikk linkjét a Story `work_notes` mezőjébe.
7. A képernyőn megjelenik a sikeres üzenet.

## Problémák elhárítása
- **Connection refused:** Ellenőrizd, hogy a VPS tűzfalán (UFW / Hetzner Cloud) be van-e engedve a 8000-es port.
- **Timeout:** A GLM-5.2 modell generálása 10-20 másodpercet vesz igénybe. A scriptben a timeout 120 másodpercre (`120000` ms) van állítva, ami bőségesen elég.
