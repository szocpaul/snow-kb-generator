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

## ServiceNow permissions for the verification gate (spec 014)

The component-name verification (if `verification_gate.enabled: true`) queries the
instance metadata on the existing SNOW_USERNAME/SNOW_PASSWORD Table API session —
no new environment variable is needed. The spot check reads the following
metadata tables:

| Table | What it contains |
|---|---|
| `sys_db_object` | table names |
| `sys_dictionary` | field names (per table) |
| `sys_script` | Business Rule names |
| `sys_script_include` | Script Include names |
| `sys_ws_operation` / `sys_processor` etc. | other script objects (according to the whitelist extension) |

The API user needs **read access** to these (on a PDI the default itil/admin
profile has it; on an instance with a narrower ACL, check the
`personalize_dictionary` permission or its equivalent). If the query returns 403,
the gate skips the spot-check layer in fail-open mode with a warning (FR-002) —
the pipeline does not stop, but the protection is weaker.

## Raising the gate into the client (spec 015, US3) — deployment note

Since spec 015 the verification gate runs INSIDE the write path of
`servicenow_client` (`_create_kb_article_live`), not in the pipeline layer. The
behaviour is unchanged (flag/strip/block + fail-open), but from now on EVERY
call path — pipeline, CLI, future endpoint — goes through the same gate; the
pipeline-level call is gone (no double decision / double recording).

**In-flight requests at the moment of the restart**: requests running during the
restart complete via the old (pipeline-level) path — this is expected, not a
bug. The actual restart is a MANUAL STEP (the runner does not deploy):

```
sudo systemctl restart snow-kb.service
```

Check after the restart: the JSONL recording of a pipeline run
(`verification_gate.recording_path`) still writes EXACTLY 1 decision row per
article write.
