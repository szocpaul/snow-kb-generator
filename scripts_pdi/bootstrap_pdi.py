#!/usr/bin/env python3
"""bootstrap_pdi.py — preparing a new ServiceNow PDI for the snow_kb_generator pipeline.

The steps (each can be run on its own: --step N):
  1. Connection check + fetching the KB sys_id (it writes it into config.yaml)
  2. The `u_source_story` field on the kb_knowledge table (spec 001, duplicate prevention)
  3. The `u_assignment_group` field on the kb_knowledge_base table (spec 002, template recognition)
  4. Template-KB + sablon-cikk a teszt-csoporthoz
  5. The "Create KB Article" UI Action on the rm_story table (servicenow/ui_action_script.js)
  6. Recreating the test Story from the runs/stry0010010_story_dump.json

Run:  ../.venv/bin/python scripts_pdi/bootstrap_pdi.py [--step N] [--dry-run]
Prerequisite: .env SNOW_INSTANCE + SNOW_USERNAME + SNOW_PASSWORD for the NEW instance.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
ENV = {}
for line in (ROOT / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        ENV[k.strip()] = v.split("#")[0].strip()

INSTANCE = ENV["SNOW_INSTANCE"]
AUTH = (ENV["SNOW_USERNAME"], ENV["SNOW_PASSWORD"])
BASE = f"https://{INSTANCE}/api/now/table"
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
WEBHOOK_KEY = ENV.get("SNOW_WEBHOOK_API_KEY", "")


def api(method, table, **kw):
    r = requests.request(method, f"{BASE}/{table}", auth=AUTH, headers=HEADERS, timeout=60, **kw)
    if r.status_code >= 400:
        raise RuntimeError(f"{method} {table} → HTTP {r.status_code}: {r.text[:400]}")
    return r.json().get("result", r.json())


def api_get1(table, query, fields="sys_id"):
    res = api("GET", table, params={"sysparm_query": query, "sysparm_limit": 1, "sysparm_fields": fields})
    return res[0] if res else None


def step1(dry: bool):
    print("[1] Kapcsolat + KB sys_id...")
    me = api("GET", "sys_user", params={"sysparm_query": f"user_name={AUTH[0]}", "sysparm_limit": 1})
    print("    auth OK:", me[0].get("user_name") if me else "?")
    kbs = api("GET", "kb_knowledge_base", params={"sysparm_limit": 10, "sysparm_fields": "sys_id,title"})
    for kb in kbs:
        print(f"    KB: {kb['title']}  ({kb['sys_id']})")
    # preferred: the first KB (on a PDI there is usually one)
    if not kbs:
        raise RuntimeError("There is no Knowledge Base on the instance!")
    # Preferred: the OOB "IT" Knowledge Base (the old config used this as well);
    # NOT the first API hit (that can be a demo KB, e.g. "KCS Knowledge Base").
    preferred = next((k for k in kbs if k.get("title") == "IT"), kbs[0])
    kb_id = preferred["sys_id"]
    print(f"    selected KB: {preferred['title']}")
    if dry:
        print(f"    [dry-run] config.yaml knowledge_base_id ← {kb_id}")
    else:
        cfg_path = ROOT / "config.yaml"
        # A targeted text replacement (a yaml round-trip would lose the comments!)
        import re as _re
        text = cfg_path.read_text()
        text, n = _re.subn(r'knowledge_base_id:.*', f'knowledge_base_id: "{kb_id}"', text, count=1)
        if n == 0:
            raise RuntimeError("the knowledge_base_id line is not found in the config.yaml!")
        cfg_path.write_text(text)
        print(f"    config.yaml updated: knowledge_base_id = {kb_id}")


def _ensure_field(table, column, label, internal_type, dry, reference=None, max_length=80):
    existing = api_get1("sys_dictionary", f"name={table}^element={column}")
    if existing:
        print(f"    {table}.{column} already exists ✅")
        return
    body = {
        "name": table, "element": column, "column_label": label,
        "internal_type": internal_type, "max_length": str(max_length), "active": "true",
    }
    if reference:
        body["reference"] = reference
    if dry:
        print(f"    [dry-run] I would create: {table}.{column} ({internal_type})")
    else:
        api("POST", "sys_dictionary", json=body)
        print(f"    {table}.{column} created ✅")


def step2(dry: bool):
    print("[2] u_source_story a kb_knowledge-n (spec 001)...")
    _ensure_field("kb_knowledge", "u_source_story", "Source Story", "string", dry, max_length=32)


def step3(dry: bool):
    print("[3] u_assignment_group a kb_knowledge_base-en (spec 002)...")
    _ensure_field("kb_knowledge_base", "u_assignment_group", "Assignment Group",
                  "reference", dry, reference="sys_user_group")


def step4(dry: bool):
    print("[4] Template-KB + sablon-cikk...")
    group = api_get1("sys_user_group", "name=Service Desk", "sys_id,name") or             api_get1("sys_user_group", "active=true", "sys_id,name")
    if not group:
        raise RuntimeError("There is no user group on the instance!")
    print(f"    csoport: {group['name']}")

    kb = api_get1("kb_knowledge_base", "u_assignment_group=" + group["sys_id"], "sys_id,title")
    if not kb:
        if dry:
            print("    [dry-run] I would create the template KB")
            return
        kb = api("POST", "kb_knowledge_base", json={
            "title": "KB Templates (snow_kb_generator)",
            "u_assignment_group": group["sys_id"], "active": "true",
        })
        print(f"    template KB created: {kb['sys_id']}")
    else:
        print(f"    template KB already exists: {kb['sys_id']}")

    tpl = api_get1("kb_knowledge", "kb_knowledge_base=" + kb["sys_id"] + "^short_descriptionLIKEStructure",
                   "sys_id,short_description")
    # a STRUCTURAL template is needed (NOT the style reference!) — the pipeline loads this as the template_context
    template_html = (ROOT / "data" / "examples" / "integration_team_template.html").read_text()         if (ROOT / "data" / "examples" / "integration_team_template.html").exists() else ""
    if not tpl and not dry:
        tpl = api("POST", "kb_knowledge", json={
            "short_description": "Integration KB — Structure Template (snow_kb_generator)",  # because of the pipeline's "CONTAINS Structure" (with a space) query it must NOT start with Structure!
            "kb_knowledge_base": kb["sys_id"], "text": template_html, "workflow_state": "published",
        })
        print(f"    template article created: {tpl['sys_id']}")
    elif tpl:
        print(f"    template article already exists: {tpl['sys_id']}")


def step5(dry: bool):
    print("[5] UI Action 'Create KB Article' az rm_story-n...")
    tbl = api_get1("sys_db_object", "name=rm_story", "sys_id")
    if not tbl:
        raise RuntimeError("the rm_story table is not found — is the Agile Development plugin installed?")
    script = (ROOT / "servicenow" / "ui_action_script.js").read_text()
    if WEBHOOK_KEY and WEBHOOK_KEY not in script:
            print("    ⚠️  WARNING: the apiKey in the script does not match the SNOW_WEBHOOK_API_KEY of the .env!")
    existing = api_get1("sys_ui_action", f"name=Create KB Article^table={tbl['sys_id']}", "sys_id")
    if existing:
        print("    UI Action already exists ✅")
        return
    if dry:
        print("    [dry-run] I would create the UI Action")
    else:
        ua = api("POST", "sys_ui_action", json={
            "name": "Create KB Article", "table": tbl["sys_id"],
            "client": "false", "form_button": "true",
            "condition": "current.state == '3'", "active": "true",
            "script": script,
        })
        print(f"    UI Action created: {ua['sys_id']}")


def step6(dry: bool):
    print("[6] Restoring the test Story from the dump...")
    dump_path = ROOT / "runs" / "stry0010010_story_dump.json"
    if not dump_path.exists():
        print("    no story dump, skipping")
        return
    story = json.loads(dump_path.read_text())
    existing = api_get1("rm_story", f"number={story['number']}", "sys_id,number")
    if existing:
        print(f"    {story['number']} already exists ✅")
        return
    body = {k: v for k, v in story.items()
            if k in ("number", "short_description", "description", "acceptance_criteria",
                     "u_technical_specification", "work_notes", "comments")}
    body["state"] = "3"  # Closed Complete — the button is only visible on a closed story
    # the assignment_group is mandatory for the pipeline (template recognition) — the old
    # sys_id of the dump is meaningless on the new instance, so we set the local Service Desk.
    grp = api_get1("sys_user_group", "name=Service Desk", "sys_id")
    if grp:
        body["assignment_group"] = grp["sys_id"]
    if dry:
        print(f"    [dry-run] I would create: {story['number']}")
    else:
        s = api("POST", "rm_story", json=body)
        print(f"    Story created: {s.get('number')} ({s.get('sys_id')})")


STEPS = [step1, step2, step3, step4, step5, step6]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--step", type=int, help="only the Nth step (1-6)")
    p.add_argument("--dry-run", action="store_true", help="it only prints what it would do")
    args = p.parse_args()
    steps = [STEPS[args.step - 1]] if args.step else STEPS
    for fn in steps:
        fn(args.dry_run)
    print("\nDONE ✅ — check: ../.venv/bin/python -m snow_kb <STRY> --no-push --json")


if __name__ == "__main__":
    main()
