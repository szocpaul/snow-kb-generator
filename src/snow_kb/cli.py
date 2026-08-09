"""cli.py — command line interface for the snow_kb pipeline.

A thin wrapper on top of pipeline.generate_kb_article(). All the logic lives in
pipeline.py and servicenow_client.py — this module only translates the command
line arguments into calls.

Usage:
    python -m snow_kb STRY0012345                     # production: fetch + generate + push
    python -m snow_kb STRY0012345 --dry-run           # mock Story, generate only
    python -m snow_kb STRY0012345 --no-push           # fetch + generate, no KB write
    python -m snow_kb STRY0012345 --output article.html  # write the result to a file
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
    """Builds the argparse argument parser."""
    parser = argparse.ArgumentParser(
        prog="snow_kb",
        description=(
            "Generates a Knowledge Base article from a ServiceNow Story "
            "with the help of a DSPy AI pipeline."
        ),
    )
    parser.add_argument(
        "story_id",
        help="The Story number (e.g. STRY0012345) or its sys_id.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mock Story from a local file, skipping the LM and the KB push.",
    )
    parser.add_argument(
        "--no-push",
        "--generate-only",
        dest="no_push",
        action="store_true",
        help="Generate without pushing (article to stdout / a file).",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="The path of config.yaml (default: ./config.yaml).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override for settings.models.main (e.g. openai/gpt-4o-mini).",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Where to save the generated article (HTML). Default: stdout.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="The article in JSON format (title, html, category, sys_id).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="More detailed logging.",
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
    """Writes the generated article to stdout or to a file."""
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
        print(f"Article saved: {output}", file=sys.stderr)
    else:
        print(content)


def main(argv: list[str] | None = None) -> int:
    """The CLI entry point.

    Args:
        argv: argumentumok (None = sys.argv[1:]).

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.verbose)
    logger = logging.getLogger("snow_kb.cli")

    # --- Load the settings ---
    try:
        settings = load_settings(args.config, dry_run=args.dry_run)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    # --- Modell override ---
    if args.model:
        settings.models.main = args.model

    # --- Run the pipeline ---
    try:
        client = ServiceNowClient(settings)
        article = generate_kb_article(
            story_identifier=args.story_id,
            client=client,
            settings=settings,
            push=not args.no_push,
            # Load the GEPA-optimized program if it exists (server pattern):
            # server.py OPTIMIZED_PROGRAM_PATH). Fallback a base programra,
            # if the file is missing or broken — see pipeline._load_program.
            program_path="artifacts/program.json",
        )
    except ServiceNowError as exc:
        print(f"ServiceNow error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        logger.debug("Traceback:", exc_info=True)
        return 1

    # --- Write the result ---
    _print_article(article, as_json=args.json, output=args.output)

    # --- Summary to stderr ---
    push_status = "pushed" if (not args.no_push and not args.dry_run) else "generated only"
    sys_id = getattr(article, "sys_id", "—")
    logger.info(
        "Article %s: %s (sys_id: %s)", push_status, article.title, sys_id
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
