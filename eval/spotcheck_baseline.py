"""spotcheck_baseline.py — T004: a T003 jelöltek ellenőrzése az instance ellen.

A artifacts/component_inventory.json jelöltjeit ellenőrzi:
  1. Update Set-tartalom (ahol a gold példához van update_set_payloads) —
     elsődleges whitelist (plan KD3).
  2. Per-név spot-check az élő instance metaadataiban (sys_db_object,
     sys_dictionary, sys_script, sys_script_include) — a ServiceNowClient
     sessionjén.

Kimenet: artifacts/component_baseline_report.json + .md
  → hány "nem létezik" név van MA (a probléma nagysága számszerűen).

Futtatás:
    python -m eval.spotcheck_baseline
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

SPOTCHECK_TABLES = ["sys_db_object", "sys_script", "sys_script_include"]


def _spotcheck_name(session, base_url: str, name: str) -> tuple[str, str]:
    """Egy név spot-checkje az instance metaadataiban.

    Returns:
        (verdict, found_in) — verdict: "exists" | "not_found" | "error".
    """
    # dotted azonosítónál a teljes név ritkán táblanév — az utolsó szegmens
    # mező- vagy scriptnév lehet; mindkettőt próbáljuk.
    probes = [name]
    if "." in name:
        last = name.split(".")[-1]
        if last and last != name:
            probes.append(last)

    for probe in probes:
        for table in SPOTCHECK_TABLES + ["sys_dictionary"]:
            field = "element" if table == "sys_dictionary" else "name"
            try:
                resp = session.get(
                    f"{base_url}/{table}",
                    params={"sysparm_query": f"{field}={probe}", "sysparm_limit": "1",
                            "sysparm_fields": "sys_id"},
                    timeout=30,
                )
                if resp.status_code != 200:
                    return "error", f"{table} HTTP {resp.status_code}"
                if resp.json().get("result"):
                    return "exists", f"{table}.{field}={probe}"
            except Exception as exc:  # noqa: BLE001
                return "error", f"{type(exc).__name__}: {exc}"
    return "not_found", ""


def main(argv: list[str] | None = None) -> None:
    import argparse

    import requests

    parser = argparse.ArgumentParser(description="T004 baseline spot-check (spec 014).")
    parser.add_argument("--inventory", default="artifacts/component_inventory.json")
    parser.add_argument("--dataset", default="data/examples/gold_dataset.md")
    parser.add_argument("--output", default="artifacts/component_baseline_report.json")
    args = parser.parse_args(argv)

    load_dotenv()
    instance = os.environ["SNOW_INSTANCE"]
    session = requests.Session()
    session.auth = (os.environ["SNOW_USERNAME"], os.environ["SNOW_PASSWORD"])
    session.headers.update({"Accept": "application/json"})
    base_url = f"https://{instance}/api/now/table"

    inventory = json.loads(Path(args.inventory).read_text(encoding="utf-8"))

    # Update Set whitelist a gold példákhoz (a dataset beágyazott payloadjaiból)
    from eval.dataset import load_gold_dataset

    trainset, valset = load_gold_dataset(args.dataset)
    gold_payloads: dict[str, str] = {}
    for i, ex in enumerate(trainset + valset):
        gold_payloads[f"gold-{i+1}"] = getattr(ex, "update_set_payloads", "") or ""

    rows = []
    counts = {"exists": 0, "not_found": 0, "error": 0, "in_update_set": 0,
              "whitelisted_generic": 0}
    for ex in inventory["examples"]:
        us_text = gold_payloads.get(ex["id"], "")
        # generált minta a gold_ref update setjét örökli
        if not us_text and ex.get("gold_ref"):
            us_text = gold_payloads.get(ex["gold_ref"], "")
        for cand in ex["candidates"]:
            name = cand["name"]
            if cand.get("whitelisted_generic"):
                counts["whitelisted_generic"] += 1
                rows.append({"example": ex["id"], "name": name,
                             "verdict": "whitelisted_generic", "evidence": "011-whitelist"})
                continue
            # 1. Update Set whitelist (casefold substring — a payload XML-ben
            #    a név gyakran attribútumban szerepel)
            if name.casefold() in us_text.casefold():
                counts["in_update_set"] += 1
                rows.append({"example": ex["id"], "name": name,
                             "verdict": "in_update_set", "evidence": "update_set_payloads"})
                continue
            # 2. Instance spot-check
            verdict, evidence = _spotcheck_name(session, base_url, name)
            counts[verdict] += 1
            rows.append({"example": ex["id"], "name": name,
                         "verdict": verdict, "evidence": evidence})
            print(f"{ex['id']:>12}  {verdict:>9}  {name}  {evidence}")

    report = {
        "spec": "014-component-instance-verification",
        "task": "T004",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "instance": instance,
        "counts": counts,
        "rows": rows,
    }
    out = Path(args.output)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md = out.with_suffix(".md")
    lines = [
        "# T004 baseline-leltár: komponensnevek az instance ellen",
        "",
        f"Dátum: {report['generated_at']}  |  Instance: {instance}",
        "",
        "| Verdict | Darab |",
        "|---|---|",
    ]
    for k, v in counts.items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## Nem létező nevek (a probléma nagysága)", ""]
    nf = [r for r in rows if r["verdict"] == "not_found"]
    if nf:
        for r in nf:
            lines.append(f"- `{r['name']}` ({r['example']})")
    else:
        lines.append("_Nincs nem-létező név a leltárban._")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nÖsszesítés: {counts}")
    print(f"→ {out} + {md}")


if __name__ == "__main__":
    main()
