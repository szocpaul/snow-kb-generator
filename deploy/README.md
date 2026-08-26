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
