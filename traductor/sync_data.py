"""
sync_data.py -- Sincronitza les còpies de `traductor/data/` amb els
fitxers font reals de `02_regles_dialectals/lexic/font_mauricio/`
(equip AVLizador). Des del 30/09/2026 el traductor és pur lookup de
diccionari de Mauricio -- ja no hi ha fonts Apertium/Paula Guerrero.

Per què cal esta sincronització manual: `traductor/rules/*.py` mai llig
`02_regles_dialectals/` en temps d'execució -- llig NOMÉS còpies pròpies
dins de `traductor/data/` (decisió de disseny: el paquet `traductor/` ha
de poder funcionar de manera autònoma, sense dependre de la resta del
repositori). Si algú edita un fitxer font directament (com el 30/09/2026,
quan es va editar `acentuacion_limpio.json` a mà: es va llevar una entrada
i afegir-ne una altra), eixe canvi NO arriba al motor fins que algú torna
a copiar el fitxer -- este script ho fa d'una tacada per a totes les
fonts, i diu exactament què ha canviat (entrades afegides/llevades) en
compte de sobreescriure en silenci.

Ús:
    python -m traductor.sync_data            # sincronitza i mostra el resum
    python -m traductor.sync_data --check    # només comprova (exit 1 si cal sincronitzar), no escriu res

Nota: la sincronització és una còpia/embolcall MECÀNIC -- els filtres de
negoci (descartar `_PENDENT`, topònims, resoldre `canonica`, excloure
"després" de l'accentuació, etc.) NO viuen ací, viuen als loaders de cada
regla (`lexic.py`, `numerals.py`...) i s'apliquen soles la pròxima vegada
que s'instancie `RuleEngine` -- este script només s'assegura que la
matèria primera (les còpies de `traductor/data/`) estiga al dia.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ARREL = Path(__file__).resolve().parent.parent
LEXICO = ARREL / "02_regles_dialectals" / "lexic"
MAURICIO = LEXICO / "font_mauricio"
DATA = Path(__file__).resolve().parent / "data"

_CONJUGACIONS_DESCRIPCIO = (
    "Formes verbals valencia/catala que difereixen entre dialectes, extretes de "
    "l'apertium bilingue catala-castella per Mauricio (equip AVLizador, 29/09/2026). "
    "Cobrix 111 verbs on almenys una conjugacio difereix. El camp 'problematica' "
    "marca formes on el valencia usa la mateixa paraula per al present d'indicatiu "
    "i el de subjuntiu (p.ex. abalance = jo abalanco / que jo abalanci), cosa que fa "
    "la conversio ambigua sense analisi gramatical (pos-tagging); conjugacions_dict.py "
    "exclou estes entrades del lookup automatic i les deixa documentades aci per si en "
    "el futur es pot afegir un mecanisme de desambiguacio."
)


@dataclass(frozen=True)
class FontSpec:
    dest: str
    font: Path | tuple[Path, ...]
    # Extrau la llista d'entrades "crues" a partir de l'estructura tal com
    # ve a CADA fitxer font (independentment de si el dest l'embolica o
    # no). Si `font` és una tupla, s'aplica a cada un i es concatenen en
    # eixe orde -- el PRIMER fitxer de la tupla guanya en cas de conflicte
    # (vore `carrega_conjugacions`, que fa `setdefault`).
    entrades: Callable[[object], list[dict]]
    # Si no és None, el dest NO és una còpia literal del font -- s'embolica
    # amb metadades (vore conjugacions_dialectals.json). Rep la llista
    # d'entrades ja concatenada i torna l'estructura completa a escriure.
    embolica: Callable[[list[dict]], object] | None = None
    # Camps a mostrar en el resum humanament llegible (primer que exista).
    camps: tuple[str, str] = ("valenciano", "catalan")

    @property
    def fonts(self) -> tuple[Path, ...]:
        return self.font if isinstance(self.font, tuple) else (self.font,)


FONTS: list[FontSpec] = [
    FontSpec(
        dest="lexic_mauricio.json",
        font=MAURICIO / "lexico_general_limpio.json",
        entrades=lambda d: d,
    ),
    FontSpec(
        dest="numerals_mauricio.json",
        font=MAURICIO / "numerales_limpio.json",
        entrades=lambda d: d,
    ),
    FontSpec(
        dest="lexic_acentuacio_mauricio.json",
        font=MAURICIO / "acentuacion_limpio.json",
        entrades=lambda d: d,
    ),
    FontSpec(
        dest="possessius_mauricio.json",
        font=MAURICIO / "posesivos_cat_val.json",
        entrades=lambda d: d,
    ),
    FontSpec(
        # "verbos_no_ambiguos.json" (afegit 30/09/2026, 261 formes de 45
        # verbs FORA dels 111 originals, totes marcades "ambigu": false)
        # va PRIMER a propòsit: 16 formes de "eixir" (isca/isquen/isc...)
        # apareixen a totes dos fonts amb traduccions diferents (
        # "ixi"/"ixin"/"ixo" a conjugaciones_limpio.json vs "surti"/
        # "surtin"/"surto" ací) -- guanya "surti" per coherència amb la
        # decisió ja presa a lexic.py (`eixir->sortir`, vore lexic_mauricio.json).
        # `carrega_conjugacions` fa `setdefault`, així que el primer fitxer
        # de la tupla és el que guanya; totes dos fitxers es conserven
        # sencers dins de "entradas" per transparència (no es descarta cap
        # entrada en sincronitzar, només en carregar -- vore docstring del
        # mòdul).
        dest="conjugacions_dialectals.json",
        font=(MAURICIO / "verbos_no_ambiguos.json", MAURICIO / "conjugaciones_limpio.json"),
        entrades=lambda d: d,
        embolica=lambda entrades: {
            "total_entradas": len(entrades),
            "descripcio": _CONJUGACIONS_DESCRIPCIO,
            "entradas": entrades,
        },
        camps=("valenciano", "catalan"),
    ),
]


def _signatura(entrada: dict) -> str:
    return json.dumps(entrada, sort_keys=True, ensure_ascii=False)


def _resum_entrada(entrada: dict, camps: tuple[str, str]) -> str:
    a, b = camps
    if a in entrada:
        return f"{entrada[a]!r} -> {entrada.get(b)!r}"
    return repr(entrada)


def _entrades_actuals_dest(spec: FontSpec, dest_dades: object) -> list[dict]:
    if spec.embolica is None:
        return spec.entrades(dest_dades)
    return dest_dades.get("entradas", []) if isinstance(dest_dades, dict) else []


def sync(check_only: bool = False) -> bool:
    """Torna `True` si calia sincronitzar alguna cosa (encara que
    `check_only=True` i per tant no s'haja escrit res de veres)."""
    calen_canvis = False
    for spec in FONTS:
        entrades_noves: list[dict] = []
        for font_path in spec.fonts:
            font_dades = json.loads(font_path.read_text(encoding="utf-8"))
            entrades_noves.extend(spec.entrades(font_dades))
        dest_path = DATA / spec.dest

        entrades_velles: list[dict] = []
        if dest_path.exists():
            dest_dades = json.loads(dest_path.read_text(encoding="utf-8"))
            entrades_velles = _entrades_actuals_dest(spec, dest_dades)

        sig_noves = {_signatura(e): e for e in entrades_noves}
        sig_velles = {_signatura(e): e for e in entrades_velles}
        afegides = sig_noves.keys() - sig_velles.keys()
        llevades = sig_velles.keys() - sig_noves.keys()

        if not afegides and not llevades and dest_path.exists():
            print(f"= {spec.dest}: sense canvis ({len(entrades_noves)} entrades)")
            continue

        calen_canvis = True
        etiqueta = "NOU FITXER" if not dest_path.exists() else f"+{len(afegides)} / -{len(llevades)}"
        print(f"~ {spec.dest}: {etiqueta} (total {len(entrades_noves)})")
        for sig in sorted(llevades):
            print(f"   - {_resum_entrada(sig_velles[sig], spec.camps)}")
        for sig in sorted(afegides):
            print(f"   + {_resum_entrada(sig_noves[sig], spec.camps)}")

        if not check_only:
            if spec.embolica is not None:
                nova_dest = spec.embolica(entrades_noves)
            else:
                # Còpia literal: només té sentit amb UN sol fitxer font
                # (sense embolcall no hi ha manera de fusionar dos
                # estructures completes en una), es reaprofita tal qual.
                (font_path,) = spec.fonts
                nova_dest = json.loads(font_path.read_text(encoding="utf-8"))
            dest_path.write_text(
                json.dumps(nova_dest, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    return calen_canvis


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Només comprova si cal sincronitzar (exit 1 si sí); no escriu res.",
    )
    args = parser.parse_args(argv)

    calen_canvis = sync(check_only=args.check)

    if args.check:
        if calen_canvis:
            print("\nCalen canvis -- executa `python -m traductor.sync_data` sense --check.")
            return 1
        print("\nTot sincronitzat.")
        return 0

    if calen_canvis:
        print(
            "\nSincronitzat. Recorda: si has canviat lexic_mauricio.json o "
            "lexic_acentuacio_mauricio.json, torna a córrer el benchmark per "
            "confirmar que no s'ha introduït cap regressió (vore traductor/README.md)."
        )
    else:
        print("\nJa estava tot sincronitzat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
