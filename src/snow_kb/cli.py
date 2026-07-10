# cli.py — command line interface (DESIGN, not implemented)
# ===========================================================================
#
# Responsibility: a user-friendly entry point to the pipeline.
# Run (planned):  python -m snow_kb STRY0012345 [options]
#
# Tervezett argumentumok (argparse vagy typer):
#
#   story_id (positional, mandatory)
#       The Story number (STRY...) or its sys_id.
#
#   --dry-run
#       Does not reach ServiceNow: the Story from a local mock file
#       reads (data/sample_stories/<story_id>.json), and the generated
#       does not write the article back to the KB. For development / testing.
#
#   --no-push   (alias: --generate-only)
#       Fetches the Story from SNOW, generates the article, but does NOT write it to the KB.
#       Writes the article to stdout and/or into the artifacts/ folder.
#
#   --config PATH
#       Custom config.yaml path (default ./config.yaml).
#
#   --model NAME
#       Overrides settings.models.main (for quick testing).
#
#   --output PATH
#       Where the generated article (HTML + JSON) is saved. Default: artifacts/.
#
#   --verbose / -v
#       More detailed logging (DSPy trace, step durations).
#
# Planned behavior:
#   1. args = parse_args()
#   2. article = pipeline.generate_kb_article(args.story_id, ...)
#   3. print/print_json or writing to a file
#
# Later options (if they turn out to be needed):
#   --batch <file>           processing multiple Stories from a list
#   --optimize / --baseline  starts eval/GEPA steps (can also be a separate entry point)
#   --version                version / program metadata
#
# Note: the cli is only a thin wrapper — all the logic is in pipeline.py.
