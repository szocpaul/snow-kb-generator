# cli.py — parancssori felület (TERV, nincs implementálva)
# ===========================================================================
#
# Felelősség: ember-barát bejárat a pipeline-hoz.
# Futtatás (tervezett):  python -m snow_kb STRY0012345 [opciók]
#
# Tervezett argumentumok (argparse vagy typer):
#
#   story_id (pozicionális, kötelező)
#       A Story száma (STRY...) vagy sys_id-ja.
#
#   --dry-run
#       Ne érjen el ServiceNow-t: a Story-t egy helyi mock fájlból
#       (data/sample_stories/<story_id>.json) olvassa, és a generált
#       cikket nem írja vissza a KB-be. Fejlesztéshez / teszteléshez.
#
#   --no-push   (alias: --generate-only)
#       Lekéri a Story-t SNOW-ból, generálja a cikket, de NEM írja a KB-be.
#       A cikket kiírja a stdout-ra és/vagy artifacts/ mappába.
#
#   --config PATH
#       Egyéni config.yaml útvonal (alapból ./config.yaml).
#
#   --model NAME
#       Override a settings.models.main fölött (gyors teszteléshez).
#
#   --output PATH
#       A generált cikk (HTML + JSON) mentése ide. Alap: artifacts/.
#
#   --verbose / -v
#       Részletesebb logolás (DSPy trace, lépések időtartama).
#
# Tervezett működés:
#   1. args = parse_args()
#   2. article = pipeline.generate_kb_article(args.story_id, ...)
#   3. print/print_json vagy fájlba írás
#
# Későbbi opciók (ha szükség lesz rá):
#   --batch <file>           több Story feldolgozása listából
#   --optimize / --baseline  eval/GEPA lépéseket indít (külön entry point is lehet)
#   --version                verzió / program metaadatok
#
# Megjegyzés: a cli csak vékony wrapper — minden logika a pipeline.py-ban van.
