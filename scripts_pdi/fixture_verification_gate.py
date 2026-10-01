#!/usr/bin/env python3
"""fixture_verification_gate.py — spec 015 T001/T002: PDI-natív fixture a
verification-gate kalibrációhoz.

A fixture: egy Story (rm_story) + egy Update Set a PDI-n, amely MÁR MEGLEVŐ
komponenseket capture-öl (capture, NEM létrehozás — a spec tilalma szerint
új Script Include / Business Rule / Property / mező NEM jön létre; csak a
fixture-tartályok: a Story és az Update Set).

A logika FORDÍTOTT (plan KD2): a script előbb lekéri a valós, létező
komponensneveket a metaadat-táblákból, és a Story-szöveg EZEKRE íródik meg
(a capture SIKERE után, a ténylegesen capture-ölt nevekre).

A capture mechanizmusa (a sys_update_xml közvetlen insertje ACL-tiltott): a
script az user aktuális update set-jét a fixture Update Set-re állítja
(sys_update_set user preference), majd minden kiválasztott rekordon egy
benignis mezőt módosít ÉS AZONNAL visszaállít (touch+revert) — a platform
így capture-öli a rekordot az update set-be, a rekord-tartalom pedig nem
változik. ACL-védett (read-only) rendszerrekord esetén a script a következő
jelöltre lép (fallback), a végén a preference visszaáll az eredeti értékre.

A script resume-képes: a Story + Update Set létrehozása után állapotfájlba ír
(artifacts/verification_fixture_state.json), újrafuttatáskor onnan folytat.

Al-parancsok:
  create   — komponens-kiválasztás + capture + Story + Update Set + dump
             (idempotens: ha a dump-artifact létezik, --force nélkül megtagadja)
  verify   — SC-001 fixture-integritás gate: az update set MINDEN neve
             spot-checkkel "létezik" a PDI-n (exit 0 = zöld, exit 1 = piros)

Futtatás:  ../.venv/bin/python scripts_pdi/fixture_verification_gate.py create|verify
Előfeltétel: .env SNOW_INSTANCE + SNOW_USERNAME + SNOW_PASSWORD (admin jogú user).
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
# Kiválasztási szabályok (plan KD2: aktív, globális scope, "rendes" név,
# típus-diverzitás, sys_updated_on preferencia)
# ---------------------------------------------------------------------------

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_ .\-]{1,79}$")
_SENSITIVE_RE = re.compile(r"password|secret|token|apikey|api_key|private", re.I)
# Volatilis/futasideju property-k: ilyen nevu rekord nem stabil fixture-alap
# (pl. *_last_run naponta valtozik) — a T003 review terhe csokkentese.
_VOLATILE_RE = re.compile(r"_last_run$|_last_execution|_timestamp$", re.I)
# Vedett rendszerrekord-heurisztika: a base-system rekordok sys_id-je gyakran
# "ffff..."-sufixos es ACL-vedett (nem touch-elheto) — kizarjuk oket.
_PROTECTED_SYSID_RE = re.compile(r"f{8,}$")

# Mező-komponenseknél csak jól olvasható, gyakori táblák (a fixture szövegében
# is értelmezhető "tabla.mezo" alakok legyenek).
_DICT_TABLES = ("incident", "task", "kb_knowledge", "change_request",
                "sys_user", "rm_story", "problem", "sc_request")
_DICT_TYPES = ("string", "reference", "choice", "integer", "boolean")

# típus → (metaadat-tábla, lekérdezés, mezők, kvóta, update-xml type label)
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
# a rekord tartalma NEM valtozik, csak a platform capture-mechanizmusa fut).
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
    """Egy metaadat-sor → fixture-név, vagy None, ha nem alkalmas jelölt."""
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
    """Tipusonkenti jelöltlista (kvóta feletti bufferrel — a capture ACL-fallbackhez)."""
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
    """A Story-szöveg a TÉNYLEGESEN capture-ölt valós nevekre íródik."""
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

    A sys_dictionary (mezo) sorok target_name-je display-label ("Story.Type"),
    nem az azonosito-név — ezert ott a payload table/element attributumaibol
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
    """Egy MEGLEVO rekord capture-elese: benignis mezo modositas + visszaallitas.

    A platform csak akkor ir sys_update_xml sort, ha a rekord tenylegesen
    valtozik — ezert a touch ket lepes (modosit + azonnal visszaallit).
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
                "emberi ellenorzes kell!")


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
                           "(meglevo komponensek capture-elese, uj komponens NINCS)",
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
                    log.warning("    capture NEM jelent meg az update set-ben: %s — fallback",
                                comp["name"])
                    continue
                log.info("    capture: [%s] %s", comp["xml_type"], comp["name"])
                captured.append(comp)
                picked += 1
            if picked < quota:
                log.warning("    KEVESEBB %s komponens capture-olodott (%d/%d)",
                            kind, picked, quota)
    finally:
        _restore_update_set_pref(uset_id, original_pref)

    if not (10 <= len(captured) <= 15):
        raise RuntimeError(
            f"A capture-olt komponensszam {len(captured)} — a spec 10-15-ot ir elo. "
            "ALLJ MEG: az allapotfajl megvan (resume lehetseges), jelentsd az embernek.")

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
        "note": "A komponensek a PDI-n MAR MEGLEVO rekordok (capture, NEM letrehozas): "
                "a capture a platform standard mechanizmusa (aktualis update set + "
                "benignis mezo touch + azonnali visszaallitas; a rekord-tartalom nem "
                "valtozott). T003 MANUALIS KAPU: az ember review-ja utan epulhet a "
                "minta (T005).",
    }
    DUMP_PATH.write_text(json.dumps(dump, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    STATE_PATH.unlink()
    log.info("KESZ. Story=%s, Update Set=%s, komponens=%d — a dump review-ja a T003 MANUALIS KAPU.",
             story_number, story_number, len(captured))


# ---------------------------------------------------------------------------
# SC-001 fixture-integritás gate (T002)
# ---------------------------------------------------------------------------

def verify_fixture() -> int:
    """Az update set MINDEN komponensneve spot-checkkel letezik a PDI-n.

    A spot-check a komponens SAJAT metaadat-tablaja ellen tortenik nev (+sys_id)
    alapjan (a verification.py SpotChecker nevesitett-probeja nem fedi le pl. a
    sys_properties-t, ezert itt tipus-tudatosan kerdezunk — az ellenorzes
    szemantikaja azonos: instance-metaadat-lekerdezes nev szerint).
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
        print("  csak update set-ben:", sorted(set(us_names) - set(dump_names)))
        print("  csak dumpban:", sorted(set(dump_names) - set(us_names)))
        return 1

    # 3. Spot-check: minden nev letezik a SAJAT tablajaban (nev + sys_id egyezes)
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
            print(f"  HIBA {comp['kind']:16s} {comp['name']} — nincs meg a {comp['table']} tablaban")
            failures.append(comp["name"])

    if failures:
        print(f"SC-001 PIROS: {len(failures)}/{len(dump_names)} nev NEM letezik: {failures}")
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
