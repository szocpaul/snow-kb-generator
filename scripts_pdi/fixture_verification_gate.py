#!/usr/bin/env python3
"""fixture_verification_gate.py — spec 015 T001/T002: a PDI-native fixture for the
verification gate calibration.

The fixture: a Story (rm_story) + an Update Set on the PDI, which captures ALREADY EXISTING
components (capture, NOT creation — according to the prohibition of the spec
no new Script Include / Business Rule / Property / field is created; only the
fixture containers: the Story and the Update Set).

The logic is REVERSED (plan KD2): the script first fetches the real, existing
component names from the metadata tables, and the Story text is written for THESE
(after a SUCCESSFUL capture, for the actually captured names).

The capture mechanism (the direct insert of sys_update_xml is ACL-forbidden): the
script sets the current update set of the user to the fixture Update Set
(sys_update_set user preference), then on every selected record it modifies a
benign field AND IMMEDIATELY restores it (touch+revert) — the platform
captures the record into the update set this way, while the content of the record does not
change. For an ACL-protected (read-only) system record the script falls back to the
next marker, at the end the preference is restored to the original value.

The script is resume-capable: after creating the Story + Update Set it writes a state file
(artifacts/verification_fixture_state.json), on a rerun it continues from there.

Al-parancsok:
  create   — the component selection + capture + Story + Update Set + dump
             (idempotent: if the dump artifact exists, it refuses without --force)
  verify   — the SC-001 fixture integrity gate: EVERY name of the update set
             exists on the PDI per the spot-check (exit 0 = green, exit 1 = red)

Run:  ../.venv/bin/python scripts_pdi/fixture_verification_gate.py create|verify
Prerequisite: .env SNOW_INSTANCE + SNOW_USERNAME + SNOW_PASSWORD (a user with admin rights).
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DUMP_PATH = ROOT / "artifacts" / "verification_fixture_components.json"
STATE_PATH = ROOT / "artifacts" / "verification_fixture_state.json"
LOG_PATH = ROOT / "artifacts" / "verification_fixture_log.txt"

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

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.StreamHandler(),
                              logging.FileHandler(LOG_PATH, encoding="utf-8")])
log = logging.getLogger("fixture015")

# ---------------------------------------------------------------------------
# The selection rules (plan KD2: active, global scope, a "proper" name,
# type diversity, the sys_updated_on preference)
# ---------------------------------------------------------------------------

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_ .\-]{1,79}$")
_SENSITIVE_RE = re.compile(r"password|secret|token|apikey|api_key|private", re.I)
# Volatile/runtime properties: a record with such a name is not a stable fixture base
# (pl. *_last_run naponta valtozik) — a T003 review terhe csokkentese.
_VOLATILE_RE = re.compile(r"_last_run$|_last_execution|_timestamp$", re.I)
# Vedett rendszerrekord-heurisztika: a base-system rekordok sys_id-je gyakran
# "ffff..."-suffixed and ACL-protected (not touchable) — we exclude them.
_PROTECTED_SYSID_RE = re.compile(r"f{8,}$")

# For the field components only the well readable, common tables (in the fixture text
# they should be meaningful "table.field" shapes).
_DICT_TABLES = ("incident", "task", "kb_knowledge", "change_request",
                "sys_user", "rm_story", "problem", "sc_request")
_DICT_TYPES = ("string", "reference", "choice", "integer", "boolean")

# type → (metadata table, query, fields, quota, update-xml type label)
QUOTAS = [
    ("script_include", "sys_script_include",
     "active=true^sys_scope.scope=global^ORDERBYDESCsys_updated_on",
     "name,sys_id,sys_updated_on,sys_policy", 4, "Script Include"),
    ("business_rule", "sys_script",
     "active=true^sys_scope.scope=global^ORDERBYDESCsys_updated_on",
     "name,sys_id,sys_updated_on,collection", 3, "Business Rule"),
    ("system_property", "sys_properties",
     "sys_scope.scope=global^ORDERBYDESCsys_updated_on",
     "name,sys_id,sys_updated_on,description", 3, "System Property"),
    ("field", "sys_dictionary",
     "active=true^sys_scope.scope=global^elementISNOTEMPTY^ORDERBYDESCsys_updated_on",
     "name,element,sys_id,sys_updated_on,internal_type", 3, "Dictionary"),
]

# Tipus -> a touch-hoz hasznalt benignis mezo (modositas + azonnali visszaallitas;
# the record content does NOT change, only the platform capture mechanism runs).
_TOUCH_FIELD = {
    "script_include": "description",
    "business_rule": "description",
    "system_property": "description",
    "field": "comments",
}


def api(method, table, **kw):
    r = requests.request(method, f"{BASE}/{table}", auth=AUTH, headers=HEADERS,
                         timeout=60, **kw)
    if r.status_code >= 400:
        raise RuntimeError(f"{method} {table} -> HTTP {r.status_code}: {r.text[:400]}")
    return r.json().get("result", r.json())


def _sane_name(name: str) -> bool:
    if not name or name != name.strip():
        return False
    if not _NAME_RE.match(name):
        return False
    if _SENSITIVE_RE.search(name):
        return False
    if _VOLATILE_RE.search(name):
        return False
    return True


def _candidate_name(kind: str, row: dict) -> str | None:
    """A metadata row → the fixture name, or None if it is not a suitable candidate."""
    if kind == "field":
        itype = row.get("internal_type")
        if isinstance(itype, dict):  # display_value nelkul link/value alak
            itype = itype.get("value", "")
        element = row.get("element", "")
        table_name = row.get("name", "")
        if table_name not in _DICT_TABLES or itype not in _DICT_TYPES:
            return None
        if not re.match(r"^[a-z][a-z0-9_]*$", element or ""):
            return None
        return f"{table_name}.{element}"
    name = row.get("name", "")
    return name if _sane_name(name) else None


def fetch_candidates() -> dict[str, list[dict]]:
    """The candidate list per type (with a buffer over the quota — for the ACL fallback of the capture)."""
    candidates: dict[str, list[dict]] = {}
    for kind, table, query, fields, quota, xml_type in QUOTAS:
        rows = api("GET", table, params={
            "sysparm_query": query, "sysparm_limit": 200,
            "sysparm_fields": fields,
        })
        buf: list[dict] = []
        seen = {c["name"].casefold() for cs in candidates.values() for c in cs}
        for row in rows:
            if len(buf) >= quota * 4:
                break
            name = _candidate_name(kind, row)
            if not name or name.casefold() in seen:
                continue
            if _PROTECTED_SYSID_RE.search(row["sys_id"]):
                continue
            if row.get("sys_policy") in ("protected", "read"):
                continue
            buf.append({
                "name": name, "kind": kind, "table": table, "xml_type": xml_type,
                "sys_id": row["sys_id"], "sys_updated_on": row.get("sys_updated_on", ""),
            })
            seen.add(name.casefold())
        candidates[kind] = buf
        log.info("Jeloltek %s: %d (kvota: %d)", kind, len(buf), quota)
    return candidates


# ---------------------------------------------------------------------------
# Story + Update Set + capture
# ---------------------------------------------------------------------------

def _build_story_text(components: list[dict]) -> tuple[str, str]:
    """The Story text is written for the REAL names that were actually captured."""
    si = [c["name"] for c in components if c["kind"] == "script_include"]
    br = [c["name"] for c in components if c["kind"] == "business_rule"]
    prop = [c["name"] for c in components if c["kind"] == "system_property"]
    fld = [c["name"] for c in components if c["kind"] == "field"]

    short = "ServiceNow oldali webhook-fogadas es KB-draft generalas bekotese (snow-kb-generator)"
    desc_lines = [
        "A snow-kb-generator integracios projekt ServiceNow oldali bekotese: a Story-re",
        "erkezo webhook-hivas KB-cikk-vazlatot general, es a vazlatot a KB-be irja.",
        "",
        "Erintett Script Include-ok: " + ", ".join(si) + ".",
        "",
        "A megoldas a kovetkezo Business Rule-okra tamaszkodik: "
        + "; ".join(f"'{n}'" for n in br) + ".",
        "",
        "Rendszer-tulajdonsagok, amelyeket a bekotes olvas: " + ", ".join(prop) + ".",
        "",
        "Erintett mezok: " + ", ".join(fld) + ".",
        "",
        "Acceptance criteria: a webhook-fogadas a fenti komponensekkel egyutt mokodik,",
        "a KB-draft a story update set-je alapjan epul fel.",
    ]
    return short, "\n".join(desc_lines)


def _set_current_update_set(uset_id: str) -> str:
    """Az user aktualis update set-jenek atallitasa (sys_update_set preference).

    Returns: az EREDETI preference-ertek (a vegen visszaallitando).
    """
    me = api("GET", "sys_user", params={
        "sysparm_query": f"user_name={AUTH[0]}", "sysparm_limit": 1,
        "sysparm_fields": "sys_id"})
    uid = me[0]["sys_id"]
    rows = api("GET", "sys_user_preference", params={
        "sysparm_query": f"name=sys_update_set^user={uid}",
        "sysparm_fields": "sys_id,value"})
    original = rows[0]["value"] if rows else ""
    if rows:
        api("PATCH", f"sys_user_preference/{rows[0]['sys_id']}", json={"value": uset_id})
    else:
        api("POST", "sys_user_preference", json={
            "name": "sys_update_set", "user": uid, "value": uset_id,
            "description": "Current update set", "type": "string"})
    log.info("    sys_update_set preference: %s -> %s", original or "(ures)", uset_id)
    return original


def _restore_update_set_pref(uset_id: str, original: str) -> None:
    rows = api("GET", "sys_user_preference", params={
        "sysparm_query": "name=sys_update_set", "sysparm_fields": "sys_id,value"})
    for row in rows:
        if row["value"] == uset_id:
            api("PATCH", f"sys_user_preference/{row['sys_id']}", json={"value": original})
    log.info("    sys_update_set preference visszaallitva: %s", original or "(ures)")


def _update_set_rows(uset_id: str) -> list[dict]:
    """Az update set sys_update_xml sorai (target_name + payload-mezokkel)."""
    return api("GET", "sys_update_xml", params={
        "sysparm_query": f"update_set={uset_id}", "sysparm_limit": 200,
        "sysparm_fields": "sys_id,name,target_name,type,action,payload"})


def _semantic_name(row: dict) -> str:
    """A capture-sor SZEMANTIKUS komponensneve.

    The target_name of the sys_dictionary (field) rows is a display label ("Story.Type"),
    not the identifier name — therefore there the payload table/element attribute comes from
    epitjuk a "tabla.mezo" alakot.
    """
    if row.get("type") == "Dictionary" or row.get("name", "").startswith("sys_dictionary_"):
        payload = row.get("payload", "")
        mt = re.search(r'table="([^"]+)"', payload)
        me = re.search(r'element="([^"]+)"', payload)
        if mt and me:
            return f"{mt.group(1)}.{me.group(1)}"
    return row.get("target_name", "")


def _captured_targets(uset_id: str) -> set[str]:
    return {_semantic_name(r).casefold() for r in _update_set_rows(uset_id)}


def _capture_component(comp: dict) -> None:
    """Capturing an EXISTING record: a benign field modification + restore.

    The platform only writes a sys_update_xml row if the record is actually
    changed — therefore the touch is two steps (modify + restore immediately).
    ACL-vedett rekordnal RuntimeError (a hivo a kovetkezo jeloltre lep).
    """
    table = comp["table"]
    sys_id = comp["sys_id"]
    field = _TOUCH_FIELD[comp["kind"]]
    cur = api("GET", f"{table}/{sys_id}", params={"sysparm_fields": f"sys_id,{field}"})
    orig = cur.get(field) or ""
    api("PATCH", f"{table}/{sys_id}", json={field: orig + " [spec015-capture]"})
    try:
        api("PATCH", f"{table}/{sys_id}", json={field: orig})
    finally:
        after = api("GET", f"{table}/{sys_id}", params={"sysparm_fields": f"sys_id,{field}"})
        if (after.get(field) or "") != orig:
            raise RuntimeError(
                f"Visszaallitas SIKERTELEN: {comp['name']} ({table}.{field}) — "
                "human verification is needed!")


def create_fixture(force: bool) -> None:
    if DUMP_PATH.exists():
        raise SystemExit(f"A dump-artifact mar letezik: {DUMP_PATH} — "
                         "ujrakepzeshez --force (ez a fixture-tartalyokat is ujra letrehozza!)")
    if force and STATE_PATH.exists():
        STATE_PATH.unlink()

    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        log.info("[resume] Meglevo allapot: Story=%s, Update Set=%s",
                 state["story"]["number"], state["update_set"]["sys_id"])
    else:
        log.info("[1/5] Komponens-jeloltek lekerdezese a metaadat-tablakbol...")
        candidates = fetch_candidates()
        log.info("[2/5] Story letrehozasa (rm_story, leiro szoveg a capture UTAN)...")
        short, _ = _build_story_text([])  # a short_description fuggetlen a nevektol
        story = api("POST", "rm_story", json={
            "short_description": short,
            "description": "(spec 015 fixture — a leiras a komponens-capture utan irul)",
        })
        story_number = story["number"]
        log.info("    Story: %s (sys_id: %s)", story_number, story["sys_id"])

        log.info("[3/5] Update Set letrehozasa (nev = story szam)...")
        uset = api("POST", "sys_update_set", json={
            "name": story_number,
            "description": f"spec 015 fixture: a {story_number} story update set-je "
                           "(capturing the existing components, there is NO new component)",
            "state": "in progress",
        })
        state = {
            "story": {"number": story_number, "sys_id": story["sys_id"],
                      "short_description": short},
            "update_set": {"name": story_number, "sys_id": uset["sys_id"]},
            "candidates": candidates,
        }
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
        log.info("    Update Set: %s (sys_id: %s) — allapot: %s",
                 story_number, uset["sys_id"], STATE_PATH)

    uset_id = state["update_set"]["sys_id"]
    candidates = state["candidates"]
    story_number = state["story"]["number"]

    log.info("[4/5] Capture: aktualis update set atallitasa + touch+revert jeloltenkent...")
    original_pref = _set_current_update_set(uset_id)
    captured: list[dict] = []
    try:
        done = _captured_targets(uset_id)
        for kind, table, query, fields, quota, xml_type in QUOTAS:
            picked = 0
            for comp in candidates.get(kind, []):
                if picked >= quota:
                    break
                if comp["name"].casefold() in done:
                    log.info("    capture mar megvan: %s — kihagyom", comp["name"])
                    captured.append(comp)
                    picked += 1
                    continue
                try:
                    _capture_component(comp)
                except RuntimeError as exc:
                    log.warning("    capture SIKERTELEN (fallback a kovetkezo jeloltre): "
                                "%s — %s", comp["name"], exc)
                    continue
                # Megerosites: a sor tenyleg megjelent az update set-ben?
                if comp["name"].casefold() not in _captured_targets(uset_id):
                    log.warning("    the capture does NOT appear in the update set: %s — fallback",
                                comp["name"])
                    continue
                log.info("    capture: [%s] %s", comp["xml_type"], comp["name"])
                captured.append(comp)
                picked += 1
            if picked < quota:
                log.warning("    FEWER %s components were captured (%d/%d)",
                            kind, picked, quota)
    finally:
        _restore_update_set_pref(uset_id, original_pref)

    if not (10 <= len(captured) <= 15):
        raise RuntimeError(
            f"A capture-olt komponensszam {len(captured)} — a spec 10-15-ot ir elo. "
            "STOP: the state file exists (a resume is possible), report it to the human.")

    log.info("[5/5] Story-leiras veglegesitese a capture-olt nevekkel + dump...")
    short, desc = _build_story_text(captured)
    api("PATCH", f"rm_story/{state['story']['sys_id']}",
       json={"description": desc, "short_description": short})
    state["story"]["short_description"] = short

    dump = {
        "spec": "015-asymmetric-verification-gate",
        "task": "T001/T002",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "instance": INSTANCE,
        "story": state["story"],
        "update_set": state["update_set"],
        "components": captured,
        "note": "The components are records that ALREADY EXIST on the PDI (capture, NOT creation): "
                "a capture a platform standard mechanizmusa (aktualis update set + "
                "a benign field touch + an immediate restore; the record content did not "
                "valtozott). T003 MANUALIS KAPU: az ember review-ja utan epulhet a "
                "sample (T005).",
    }
    DUMP_PATH.write_text(json.dumps(dump, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    STATE_PATH.unlink()
    log.info("DONE. Story=%s, Update Set=%s, component=%d — the dump review is the T003 MANUAL GATE.",
             story_number, story_number, len(captured))


# ---------------------------------------------------------------------------
# The SC-001 fixture integrity gate (T002)
# ---------------------------------------------------------------------------

def verify_fixture() -> int:
    """Every component name of the update set exists on the PDI, verified with a spot-check.

    The spot-check runs against the component's OWN metadata table by name (+sys_id)
    (the named probe of the verification.py SpotChecker does not cover e.g.
    sys_properties, so here we query in a type-aware way — the semantics of the
    check are the same: an instance metadata query by name).
    """
    if not DUMP_PATH.exists():
        print(f"Hianyzik a dump: {DUMP_PATH} — futtasd elobb a create-et.")
        return 2
    dump = json.loads(DUMP_PATH.read_text(encoding="utf-8"))
    uset_id = dump["update_set"]["sys_id"]

    # 1. Az update set sys_update_xml sorainak SZEMANTIKUS nevlistaja az instance-rol
    #    (a Dictionary-sorok display-labelt adnak target_name-ben — payload-mapping)
    rows = _update_set_rows(uset_id)
    us_names = sorted({_semantic_name(r) for r in rows})
    print(f"Az update set-ben {len(us_names)} capture-sor van.")

    # 2. Dump konzisztencia: a dumpolt komponens-nevhalmaz == update set nevhalmaz
    dump_names = sorted(c["name"] for c in dump["components"])
    if us_names != dump_names:
        print("PIROS: a dump es az update set nevhalmaza elter!")
        print("  only in the update set:", sorted(set(us_names) - set(dump_names)))
        print("  only in the dump:", sorted(set(dump_names) - set(us_names)))
        return 1

    # 3. Spot-check: every name exists in its OWN table (name + sys_id match)
    failures = []
    for comp in dump["components"]:
        if comp["kind"] == "field":
            table_name, element = comp["name"].split(".", 1)
            query = f"name={table_name}^element={element}"
        else:
            query = f"name={comp['name']}"
        res = api("GET", comp["table"], params={
            "sysparm_query": query, "sysparm_limit": 5, "sysparm_fields": "sys_id,name",
        })
        hit = any(r["sys_id"] == comp["sys_id"] for r in res)
        if hit:
            print(f"  OK   {comp['kind']:16s} {comp['name']}")
        else:
            print(f"  ERROR {comp['kind']:16s} {comp['name']} — it is not in the {comp['table']} table")
            failures.append(comp["name"])

    if failures:
        print(f"SC-001 RED: {len(failures)}/{len(dump_names)} names do NOT exist: {failures}")
        return 1
    print(f"SC-001 ZOLD: az update set mind a {len(dump_names)} neve spot-checkkel letezik (0 elteres).")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["create", "verify"])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.command == "create":
        if args.force and DUMP_PATH.exists():
            DUMP_PATH.unlink()
        create_fixture(force=args.force)
    else:
        sys.exit(verify_fixture())


if __name__ == "__main__":
    main()
