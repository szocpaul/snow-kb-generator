"""dataset.py — Gold dataset loader a GEPA optimalizációhoz.

Betölti a gold_dataset.md fájlt, és dspy.Example objektumokat hoz létre
trainset (3) / valset (2) szeparált felosztásban.
"""

from __future__ import annotations

import re
from pathlib import Path

import dspy


_TEMPLATE_CACHE: str | None = None


def _load_template_context() -> str:
    """Az Integration Team HTML sablon betöltése (cache-elve).

    Ha a fájl hiányzik, üres string — ilyenkor a program ValueError-t dob
    (spec 009), ami a helyes viselkedés: sablon nélkül nincs generálás.
    """
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is None:
        template_path = Path("data/examples/integration_team_template.html")
        _TEMPLATE_CACHE = (
            template_path.read_text(encoding="utf-8") if template_path.exists() else ""
        )
    return _TEMPLATE_CACHE


def load_gold_dataset(path: str | Path) -> tuple[list[dspy.Example], list[dspy.Example]]:
    """Betölti a gold_dataset.md fájlt és szeparált trainset/valset felosztást ad vissza.

    Args:
        path: A gold_dataset.md fájl útvonala.

    Returns:
        (trainset, valset) tuple — 3 trainset és 2 valset dspy.Example objektum.
        Minden example tartalmazza a story_text (input) és html (expected output) mezőket.

    Raises:
        FileNotFoundError: ha a fájl nem létezik.
        ValueError: ha a fájl formátuma érvénytelen (kevesebb mint 5 példa, vagy hiányzó mezők).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Gold dataset nem található: {path}")

    content = path.read_text(encoding="utf-8")

    # A fájl szerkezete: "## Példa N: ..." szekciókra bontva
    # A speciális Unicode karakterek (á, é, stb.) miatt a split nem működik,
    # ezért egyszerűen a "## " (kettős hash + szóköz) kezdetű sorokra bontjuk,
    # de csak azokra, amik után "Példa" szerepel (a fejléceket nem bontjuk).
    examples_raw = re.split(r"^## P", content, flags=re.MULTILINE)
    examples_raw = [e.strip() for e in examples_raw if e.strip() and e.startswith("élda ")]

    examples = []

    for idx, raw in enumerate(examples_raw):
        # Story kinyerése (json blokk)
        # A "### Story" után új sor, majd ```json, majd a tartalom, majd ```
        story_match = re.search(r"### Story\s*```json\s*(.+?)```", raw, re.DOTALL)
        if not story_match:
            raise ValueError(f"A {idx+1}. példában hiányzik a '### Story' blokk.")

        story_text = story_match.group(1).strip()

        # KB cikk kinyerése (html blokk)
        # A "(Gold Article)" suffix opcionális — a gold_dataset.md tartalmazza,
        # de a teszt-fixture-ök és a korábbi formátum csak "### Várt KB Cikk"-et használ
        html_match = re.search(r"### Várt KB Cikk(?: \(Gold Article\))?\s*```html\s*(.+?)```", raw, re.DOTALL)
        if not html_match:
            raise ValueError(f"A {idx+1}. példában hiányzik a '### Várt KB Cikk (Gold Article)' blokk.")

        html = html_match.group(1).strip()

        # Validáció: a story_text és html nem lehet üres
        if len(story_text) < 50:
            raise ValueError(f"A {idx+1}. példa story_text mezője túl rövid ({len(story_text)} karakter).")
        if "<h2>" not in html:
            raise ValueError(f"A {idx+1}. példa html mezője nem tartalmaz <h2> fejléceket.")

        # dspy.Example létrehozása: story_text + template_context (inputok),
        # html (expected output). Spec 009: a template_context kötelező input —
        # a gold példákhoz az Integration Team sablont használjuk (ugyanaz,
        # mint amit a pipeline a ServiceNow-ból tölt le).
        ex = dspy.Example(
            story_text=story_text,
            template_context=_load_template_context(),
            html=html,
        ).with_inputs("story_text", "template_context")
        examples.append(ex)

    # Szeparált felosztás: első 3 trainset, utolsó 2 valset
    if len(examples) < 5:
        raise ValueError(
            f"A gold dataset kevesebb mint 5 példát tartalmaz ({len(examples)}). "
            "Legalább 5 példa kell a GEPA optimalizációhoz."
        )

    trainset = examples[:3]
    valset = examples[3:5]

    return trainset, valset
