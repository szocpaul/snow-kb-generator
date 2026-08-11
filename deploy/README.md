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
