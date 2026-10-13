#!/usr/bin/env python3
"""
ipd.py -- Índex de Puresa Dialectal (IPD): quin percentatge de les
paraules dialectalment marcades d'un text son formes OCCIDENTALS
(valencianes) en compte d'ORIENTALS (catalanes).

    IPD = total_paraules_occidentals / (total_occidentals + total_orientals)

Un IPD d'1.0 vol dir "cap paraula catalana marcada en tot el text", 0.0
vol dir el contrari, i `None` vol dir que no s'ha trobat cap paraula
dialectalment marcada (el text no diu res sobre quin dialecte és -- no
es pot calcular un percentatge sobre zero).

ORIGEN (13/10/2026, vore `documentacio/hoja_de_ruta_ipd_y_proxima_fase.md`):
`01_extraccio_i_neteja/estudi_dialectal.py` ja calculava una mètrica molt
semblant (`ratio_occ`), pero contra dos llistes curades a mà d'una
vuitantena de paraules cadascuna (`OCCIDENTAL_MARKERS`/`ORIENTAL_MARKERS`
en eixe fitxer). Este mòdul fa el mateix càlcul pero contra l'índex de
parells dialectals que JA manté `traductor/` per a traduir de veres --
uns 53.000 parells (1.471 de lèxic general + ~52.000 formes verbals
conjugades + demostratius/possessius/numerals), no reinventant cap dada
nova. Avantages sobre l'enfocament antic:

  1. Molt mes vocabulari cobert (uns 500 cops mes paraules).
  2. Una sola font de veritat: si una paraula es dialectal segons el
     motor de traducció, també ho és segons l'IPD -- no hi ha dos
     llistes que es puguen desincronitzar.
  3. Funciona per a QUALSEVOL text (una frase solta, un fitxer, un
     corpus JSONL sencer), no només per als documents ja carregats a
     `dades/avl/final/unified.jsonl` com calia amb l'script antic.

LIMITACIÓ CONEGUDA, ACCEPTADA DE MOMENT: només compta paraules que
apareixen LITERALMENT a algun dels diccionaris de lookup exacte (lèxic,
conjugacions, demostratius, numerals, possessius). Els patrons
PRODUCTIUS de sufix del motor (p.ex. `-és`(occ)/`-ès`(or) a
`accentuacio.py`, o l'alternança incoativa d'`incoatius.py`) NO estan
inclosos encara -- cobrixen un patró obert (qualsevol paraula que
acabe aixina, no una llista tancada), i incorporar-los ací faria falta
el mateix tipus de regex que ya tenen eixos mòduls. Es deixa fora
expressament per no barrejar dos mecanismes distints en la primera
versió -- ampliar-ho és un pas pendent documentat, no un oblit.

AMBIGÜITAT: si una mateixa forma apareix com a VALENCIANA en un parell
i com a CATALANA en un atre (col·lisió entre entrades no relacionades,
p.ex. per homografia accidental), no es fiable com a marcador de cap
dels dos costats -- se'n descarta dels dos conjunts (preferix fals
negatiu, mateix criteri que la resta del projecte).

ÚS com a script:

    python ipd.py --text "Este xiquet vol vindre hui."
    python ipd.py --fitxer un_document.txt
    python ipd.py --corpus ../dades/avl/final/unified.jsonl --camp text

ÚS com a mòdul (des d'un atre script del projecte):

    from ipd import calcula_ipd
    calcula_ipd("Este xiquet vol vindre hui.")["ipd"]  # -> 1.0
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterator

# `ipd.py` viu a 09_index_puresa_dialectal/, germana de `traductor/` (no
# dins d'ella) -- mateix mecanisme que `03_seleccio_de_model/evalua_models.py`
# per a trobar el paquet quan l'script s'executa des de dins d'esta carpeta.
_ARREL_PROJECTE = str(Path(__file__).resolve().parent.parent)
if _ARREL_PROJECTE not in sys.path:
    sys.path.insert(0, _ARREL_PROJECTE)

from traductor.rules.cat_val.conjugacions_dict import carrega_conjugacions_invers
from traductor.rules.cat_val.demostratius import carrega_demostratius_invers
from traductor.rules.cat_val.lexic import carrega_lexic_invers
from traductor.rules.cat_val.numerals import carrega_numerals_invers
from traductor.rules.cat_val.possessius import carrega_possessius_invers
from traductor.rules.val_cat.conjugacions_dict import carrega_conjugacions
from traductor.rules.val_cat.demostratius import carrega_demostratius
from traductor.rules.val_cat.lexic import carrega_lexic
from traductor.rules.val_cat.numerals import carrega_numerals
from traductor.rules.val_cat.possessius import _carrega_possessius

# Mateix patró de tokenització que `01_extraccio_i_neteja/estudi_dialectal.py`
# (paraules Unicode, sense dígits) -- prou per a un recompte de presència
# de paraula, no fa falta el tokenitzador complet del motor (que distingix
# prefixos/sufixos elidits per a poder RECONSTRUIR el text traduït, cosa
# que l'IPD no necessita fer).
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

_CACHE: tuple[frozenset[str], frozenset[str]] | None = None


def carrega_formes_dialectals(forcar_recarrega: bool = False) -> tuple[frozenset[str], frozenset[str]]:
    """Fusiona tots els diccionaris diferencials que ja fa servir
    `traductor/` (les dos direccions, per a cobertura màxima -- cada
    direcció resol l'ambigüitat pel seu costat, aixina que una entrada
    descartada en un sentit pot seguir sent vàlida per l'altre) i torna
    `(formes_occidentals, formes_orientals)`, dos conjunts disjunts de
    paraules en minúscules.

    Es guarda en cache de mòdul (`forcar_recarrega=True` per ignorar-la)
    perque fusionar ~53.000 entrades a cada crida seria car si s'analitza
    un corpus sencer document a document.

    >>> occ, orr = carrega_formes_dialectals()
    >>> "xiquet" in occ
    True
    >>> "nen" in orr
    True
    >>> "xiquet" in orr
    False
    """
    global _CACHE
    if _CACHE is not None and not forcar_recarrega:
        return _CACHE

    occ: set[str] = set()
    orr: set[str] = set()

    def afig_val_a_cat(parells: dict[str, str]) -> None:
        for valenciano, catalan in parells.items():
            occ.add(valenciano.lower())
            orr.add(catalan.lower())

    def afig_cat_a_val(parells: dict[str, str]) -> None:
        for catalan, valenciano in parells.items():
            occ.add(valenciano.lower())
            orr.add(catalan.lower())

    afig_val_a_cat(carrega_lexic())
    afig_val_a_cat(carrega_conjugacions())
    afig_val_a_cat(carrega_demostratius())
    afig_val_a_cat(carrega_numerals())
    afig_val_a_cat(_carrega_possessius())

    afig_cat_a_val(carrega_lexic_invers())
    afig_cat_a_val(carrega_conjugacions_invers())
    afig_cat_a_val(carrega_demostratius_invers())
    afig_cat_a_val(carrega_numerals_invers())
    afig_cat_a_val(carrega_possessius_invers())

    # Col·lisions entre entrades no relacionades (vore docstring del
    # mòdul, "AMBIGÜITAT") -- es descarten dels dos conjunts.
    ambigues = occ & orr
    occ -= ambigues
    orr -= ambigues

    _CACHE = (frozenset(occ), frozenset(orr))
    return _CACHE


def calcula_ipd(
    text: str, formes: tuple[frozenset[str], frozenset[str]] | None = None
) -> dict:
    """Calcula l'IPD d'un text solt (una frase, un paràgraf, un
    document sencer). Si no es passa `formes`, carrega (o reutilitza)
    l'índex complet amb `carrega_formes_dialectals()`.

    >>> r = calcula_ipd("Este xiquet vol vindre hui.")
    >>> r["total_occidentals"], r["total_orientals"], r["ipd"]
    (3, 0, 1.0)

    >>> r = calcula_ipd("El xiquet jugava amb el nen del veí.")
    >>> r["total_occidentals"], r["total_orientals"], r["ipd"]
    (1, 1, 0.5)

    >>> r = calcula_ipd("La casa és gran i té un jardí.")
    >>> r["total_marcades"], r["ipd"]
    (0, None)
    """
    if formes is None:
        formes = carrega_formes_dialectals()
    occ_formes, or_formes = formes

    paraules = WORD_RE.findall(text.lower())
    marcadors_occ = [p for p in paraules if p in occ_formes]
    marcadors_or = [p for p in paraules if p in or_formes]

    total_occ = len(marcadors_occ)
    total_or = len(marcadors_or)
    total_marcades = total_occ + total_or

    return {
        "total_paraules": len(paraules),
        "total_occidentals": total_occ,
        "total_orientals": total_or,
        "total_marcades": total_marcades,
        "ipd": round(total_occ / total_marcades, 4) if total_marcades else None,
        "marcadors_occidentals": marcadors_occ,
        "marcadors_orientals": marcadors_or,
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _llig_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"AVÍS: línia {lineno} de {path} il·legible ({exc})", file=sys.stderr)


def _mostra_text(etiqueta: str, resultat: dict, mostra: int) -> None:
    ipd = resultat["ipd"]
    ipd_text = f"{ipd:.4f}" if ipd is not None else "-- (cap paraula marcada)"
    print(f"{etiqueta}")
    print(f"  IPD: {ipd_text}")
    print(
        f"  occidentals={resultat['total_occidentals']}  "
        f"orientals={resultat['total_orientals']}  "
        f"paraules totals={resultat['total_paraules']}"
    )
    if mostra > 0:
        if resultat["marcadors_occidentals"]:
            print(f"  marcadors occidentals: {resultat['marcadors_occidentals'][:mostra]}")
        if resultat["marcadors_orientals"]:
            print(f"  marcadors orientals:   {resultat['marcadors_orientals'][:mostra]}")


def _processa_corpus(path: Path, camp: str, mostra: int, sortida_json: Path | None) -> None:
    formes = carrega_formes_dialectals()
    resultats = []
    total_occ = total_or = 0
    for doc in _llig_jsonl(path):
        text = doc.get(camp) or ""
        r = calcula_ipd(text, formes)
        total_occ += r["total_occidentals"]
        total_or += r["total_orientals"]
        resultats.append({**{"id": doc.get("id") or doc.get("corpus_id")}, **r})

    denom = total_occ + total_or
    ipd_global = round(total_occ / denom, 4) if denom else None
    print(f"Corpus: {path}  ({len(resultats)} documents, camp '{camp}')")
    print(f"  IPD global: {ipd_global if ipd_global is not None else '-- (cap paraula marcada)'}")
    print(f"  occidentals={total_occ}  orientals={total_or}")

    if sortida_json is not None:
        sortida_json.write_text(
            json.dumps(
                {"ipd_global": ipd_global, "total_occidentals": total_occ,
                 "total_orientals": total_or, "documents": resultats},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        print(f"  Guardat detall per document a {sortida_json}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calcula l'Índex de Puresa Dialectal (IPD) d'un text, fitxer o corpus JSONL."
    )
    grup = parser.add_mutually_exclusive_group(required=True)
    grup.add_argument("--text", help="Frase o text solt a analitzar.")
    grup.add_argument("--fitxer", type=Path, help="Fitxer de text pla a analitzar sencer.")
    grup.add_argument("--corpus", type=Path, help="Fitxer JSONL amb un document per linia.")
    parser.add_argument(
        "--camp", default="text",
        help="Camp de text dins de cada linia del --corpus (per defecte: 'text').",
    )
    parser.add_argument(
        "--mostra", type=int, default=10,
        help="Quants marcadors trobats mostrar de cada dialecte (nomes per a --text/--fitxer).",
    )
    parser.add_argument(
        "--sortida", type=Path, default=None,
        help="Amb --corpus: fitxer JSON on guardar el detall per document.",
    )
    args = parser.parse_args()

    if args.text is not None:
        _mostra_text("(text solt)", calcula_ipd(args.text), args.mostra)
    elif args.fitxer is not None:
        text = args.fitxer.read_text(encoding="utf-8")
        _mostra_text(str(args.fitxer), calcula_ipd(text), args.mostra)
    else:
        _processa_corpus(args.corpus, args.camp, args.mostra, args.sortida)


if __name__ == "__main__":
    main()
