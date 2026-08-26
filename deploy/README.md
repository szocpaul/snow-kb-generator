# Server deployment with systemd (restart tolerance)

The `deploy/snow-kb.service` unit file makes sure the FastAPI server starts
automatically after a machine reboot or a crash (`Restart=always`).

## Installation

```bash
sudo cp deploy/snow-kb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now snow-kb.service
```

## Management

```bash
systemctl status snow-kb.service   # status
sudo systemctl restart snow-kb.service  # restart (e.g. after a deploy)
tail -f server.log                 # the log still goes to the project's server.log
```

## Dev mode on the server (using the local LLM instead of Kimi)

```bash
sudo systemctl edit snow-kb.service
# insert:
# [Service]
# Environment=SNOW_KB_DEV_MODE=1
sudo systemctl restart snow-kb.service
```

To switch it off: delete the drop-in (`sudo systemctl revert snow-kb.service`) + restart.
