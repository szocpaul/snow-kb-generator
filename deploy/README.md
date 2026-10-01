# Szerver telepítés systemd-vel (restart-tűrés)

A `deploy/snow-kb.service` unit fájl gondoskodik róla, hogy a FastAPI szerver
gép-újraindítás és crash után is automatikusan elinduljon (`Restart=always`).

## Telepítés

```bash
sudo cp deploy/snow-kb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now snow-kb.service
```

## Kezelés

```bash
systemctl status snow-kb.service   # állapot
sudo systemctl restart snow-kb.service  # újraindítás (pl. deploy után)
tail -f server.log                 # a log továbbra is a projekt server.log-jába ír
```

## Dev mód a szerveren (lokális LLM használata Kimi helyett)

```bash
sudo systemctl edit snow-kb.service
# illeszd be:
# [Service]
# Environment=SNOW_KB_DEV_MODE=1
sudo systemctl restart snow-kb.service
```

Kikapcsolás: a drop-in törlése (`sudo systemctl revert snow-kb.service`) + restart.

## Verification gate ServiceNow-jogosultságai (spec 014)

A komponensnév-hitelesítés (ha `verification_gate.enabled: true`) a meglévő
SNOW_USERNAME/SNOW_PASSWORD Table API-sessionjén kérdezi le az instance
metaadatait — új környezeti változó NEM kell. A spot-check a következő
metaadat-táblákat olvassa:

| Tábla | Mit tartalmaz |
|---|---|
| `sys_db_object` | táblanevek |
| `sys_dictionary` | mezőnevek (táblánként) |
| `sys_script` | Business Rule-nevek |
| `sys_script_include` | Script Include-nevek |
| `sys_ws_operation` / `sys_processor` stb. | egyéb szkript-objektumok (a whitelist-kiterjesztés szerint) |

Az API-usernek ezekre **olvasási jog** kell (a PDI-n az alap itil/admin
profil rendelkezik vele; szűkebb ACL-ű instance-en a `personalize_dictionary`
vagy ekvivalens jogot ellenőrizni kell). Ha a lekérdezés 403-at ad, a gate
fail-open módon warninggal kihagyja a spot-check réteget (FR-002) — a
pipeline nem áll le, de a védelem gyengül.

## Gate-emelés a kliensbe (spec 015, US3) — deploy-megjegyzés

A spec 015 óta a verification gate a `servicenow_client` írási útjának
BELSEJÉBEN fut (`_create_kb_article_live`), nem a pipeline-rétegben. A
viselkedés változatlan (flag/strip/block + fail-open), de mostantól MINDEN
hívási út — pipeline, CLI, jövőbeli endpoint — ugyanazon a kapun megy át;
a pipeline-rétegű hívás megszűnt (nincs dupla döntés / dupla recording).

**In-flight kérések a restart pillanatában**: a restartkor futó kérések a régi
(pipeline-rétegű) úton fejeződnek be — ez várható, nem hiba. A tényleges
restart EMBERI LÉPÉS (a runner nem deployol):

```
sudo systemctl restart snow-kb.service
```

A restart után ellenőrzés: egy pipeline-futás JSONL-recordingja
(`verification_gate.recording_path`) továbbra is PONTOSAN 1 döntéssort ír
cikk-írásonként.
