"""cli.py — parancssori felület a snow_kb pipeline-hoz.

Vékony wrapper a pipeline.generate_kb_article() felett. Minden logika a
pipeline.py-ban és a servicenow_client.py-ban van — ez a modul csak a
parancssori argumentumokat fordítja le hívásokká.

Használat:
    python -m snow_kb STRY0012345                     # éles: lekér + generál + push
    python -m snow_kb STRY0012345 --dry-run           # mock Story, csak generál
    python -m snow_kb STRY0012345 --no-push           # lekér + generál, nem ír KB-be
    python -m snow_kb STRY0012345 --output cikk.html  # eredmény fájlba
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from snow_kb.config import ConfigError, load_settings
from snow_kb.pipeline import generate_kb_article
from snow_kb.servicenow_client import ServiceNowClient, ServiceNowError


def build_parser() -> argparse.ArgumentParser:
    """Felépíti az argparse argumentum-elemzőt."""
    parser = argparse.ArgumentParser(
        prog="snow_kb",
        description=(
            "ServiceNow Story-ból Knowledge Base cikket generál "
            "egy DSPy AI pipeline segítségével."
        ),
    )
    parser.add_argument(
        "story_id",
        help="A Story száma (pl. STRY0012345) vagy sys_id-ja.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mock Story helyi fájlból, LM és KB push kihagyása.",
    )
    parser.add_argument(
        "--no-push",
        "--generate-only",
        dest="no_push",
        action="store_true",
        help="Generálás push nélkül (cikk stdout-ra / fájlba).",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="A config.yaml útvonala (alapértelmezett: ./config.yaml).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override a settings.models.main fölött (pl. openai/gpt-4o-mini).",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="A generált cikk mentése ide (HTML). Alapértelmezett: stdout.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="A cikk JSON formátumban (title, html, category, sys_id).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Részletesebb logolás.",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Dev mód: a LOKÁLIS LLM-et (llama.cpp) használja a Kimi K3 helyett.",
    )
    return parser


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _print_article(article, as_json: bool, output: str | None) -> None:
    """Kiírja a generált cikket stdout-ra vagy fájlba."""
    if as_json:
        data = {
            "title": article.title,
            "html": article.html,
            "category": article.category,
            "knowledge_base_id": article.knowledge_base_id,
        }
        if hasattr(article, "sys_id"):
            data["sys_id"] = article.sys_id
        content = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        content = article.html

    if output:
        Path(output).write_text(content, encoding="utf-8")
        print(f"Cikk elmentve: {output}", file=sys.stderr)
    else:
        print(content)


def main(argv: list[str] | None = None) -> int:
    """A CLI belépési pontja.

    Args:
        argv: argumentumok (None = sys.argv[1:]).

    Returns:
        Exit code (0 = sikeres, 1 = hiba).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.verbose)
    logger = logging.getLogger("snow_kb.cli")

    # --- Settings betöltése ---
    try:
        settings = load_settings(args.config, dry_run=args.dry_run)
    except ConfigError as exc:
        print(f"Konfigurációs hiba: {exc}", file=sys.stderr)
        return 1

    # --- Modell override ---
    if args.model:
        settings.models.main = args.model

    # --- Dev mód: a lokális LLM-re váltás ---
    if args.dev:
        settings.pipeline.task_model = "local"
        logger.info("Dev mód: lokális LLM (llama.cpp) használata.")

    # --- Pipeline futtatása ---
    try:
        client = ServiceNowClient(settings)
        article = generate_kb_article(
            story_identifier=args.story_id,
            client=client,
            settings=settings,
            push=not args.no_push,
            # A GEPA-optimalizált program betöltése, ha létezik (server-minta:
            # server.py OPTIMIZED_PROGRAM_PATH). Fallback a base programra,
            # ha a fájl hiányzik/hibás — ld. pipeline._load_program.
            program_path="artifacts/program.json",
        )
    except ServiceNowError as exc:
        print(f"ServiceNow hiba: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Váratlan hiba: {exc}", file=sys.stderr)
        logger.debug("Traceback:", exc_info=True)
        return 1

    # --- Eredmény kiírása ---
    _print_article(article, as_json=args.json, output=args.output)

    # --- Összefoglaló stderr-re ---
    push_status = "pusholva" if (not args.no_push and not args.dry_run) else "csak generálva"
    sys_id = getattr(article, "sys_id", "—")
    logger.info(
        "Cikk %s: %s (sys_id: %s)", push_status, article.title, sys_id
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
