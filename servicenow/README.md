# ServiceNow UI Action: "Create KB"

Ez a mappa tartalmazza a ServiceNow-oldali scripteket, amiket be kell másolnod
a ServiceNow instance-odra (UI Action record + script).
**Ezek nem futnak a szerverünkön** — a ServiceNow szerverén futnak.

## Telepítés

### 1. Gyűtsd össze az adatokat

Szükséged lesz a FastAPI szervered adataira:
- **API URL**: pl. `http://your-vps-ip:8000/generate-kb`
- **API Key**: a `SNOW_WEBHOOK_API_KEY`, amit a `.env`-be tettél

### 2. UI Action record létrehozása

Nyisd meg a ServiceNow-t, és hozz létre egy új UI Action recordot:

- **Name**: `Create KB Article`
- **Table**: `rm_story` (vagy `story`, attól függően, melyik van az instance-odon)
- **Client**: `true` (client-side script)
- **Onclick**: `createKbArticle()` (a Client Script neve, amit lentebb találsz)
- **Condition**: `current.state == '3' || current.state == 'Closed Complete'`
  (Csak lezárt Story-kon jelenjen meg a gomb)

### 3. Client Script (UI Action Script mezőbe)

Másold be a `create_kb_client_script.js` tartalmát az UI Action "Script" mezőjébe.
Ne felejtsd el átírni benne az `API_URL` és `API_KEY` értékeket!

## Hogyan működik?

1. A fejlesztő megnyit egy lezárt Story-t.
2. A Story form tetején megjelenik a "Create KB Article" gomb.
3. A gombra kattintva a ServiceNow kliens oldalon (böngészőben) egy `GlideAjax`
   hívást indít, ami a szerver oldalon egy Script Include-ot hív.
4. A Script Include (ServiceNow szerver oldalon) REST hívást intéz a FastAPI
   szerverednek (`POST /generate-kb`).
5. A FastAPI szerver lefuttatja a pipeline-t, létrehozza a KB cikket.
6. A Script Include visszakapja a KB cikk linkjét, és beírja a Story
   `work_notes` mezőjébe.

> **Megjegyzés:** A `create_kb_script_include.js` egy Script Include, amit külön
> létre kell hoznod a ServiceNow-ban, mert a kliens oldali script nem közvetlenül
> hívhat külső URL-t (CORS és biztonsági okokból). A Script Include fut a
> szerveren, és ott már lehet REST hívást indítani.
