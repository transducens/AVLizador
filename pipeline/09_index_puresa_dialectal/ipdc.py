#!/usr/bin/env python3
"""
ipdc.py -- Índex de Puresa Dialectal Catalana (IPDC): quina part de les
paraules dialectalment marcades d'un text són formes CATALANES
(orientals). 1.0 = català pur, 0.0 = cap forma catalana.

    IPDC = total_orientals / (total_occidentals + total_orientals)

Germà simètric d'`ipdv.py` (Índex de Puresa Dialectal Valenciana): les
dos mesures van de 0 (gens pur) a 1 (pur), així que un text català pur
té IPDC = 1 i un text valencià pur té IPDV = 1. Amb marcadors,
IPDC = 1 - IPDV.

TEXT SENSE CAP PARAULA MARCADA (decisió de l'usuari, 26/10/2026): no hi
ha res que el desmentisca, així que és fidel als dos dialectes i compta
com a PUR en tots dos: IPDC = 1.0 (i IPDV = 1.0). `total_marcades == 0`
diu que el valor no ve de cap marcador.

No reimplementa res: els marcadors els detecta `ipd.py::calcula_ipd`
(mateix índex de parells del traductor, mateix filtre de POS i
d'homògrafs). `ipd.py` es queda tal qual (IPD únic, 1 = valencià i
0 = català, amb el paràmetre `dialecte`).

CORPUS: dona dos xifres, perquè les frases sense marcadors només
compten en una d'elles:
  - `ipdc_global`: suma de marcadors de tot el corpus (com l'IPD global
    d'`ipd.py`); les frases sense marcadors no hi pesen.
  - `ipdc_mitjana`: mitjana de l'IPDC de cada frase; les frases sense
    marcadors hi compten com a 1.0.

ÚS com a script:

    python ipdc.py --text "Aquest nen vol venir avui."
    python ipdc.py --fitxer un_document.txt
    python ipdc.py --corpus ../03_seleccio_de_model/benchmark_corpus.json \
        --camp oriental --sortida ipdc.json

ÚS com a mòdul:

    from ipdc import calcula_ipdc
    calcula_ipdc("Aquest nen vol venir avui.")["ipdc"]  # -> 1.0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_DIR = str(Path(__file__).resolve().parent)
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from ipd import Formes, _llig_jsonl, calcula_ipd, carrega_formes_dialectals  # noqa: E402


def calcula_ipdc(text: str, formes: Formes | None = None) -> dict:
    """Calcula l'IPDC d'un text solt (frase, paràgraf o document).

    >>> calcula_ipdc("Aquest nen vol venir avui.")["ipdc"]
    1.0
    >>> calcula_ipdc("Este xiquet vol vindre hui.")["ipdc"]
    0.0
    >>> calcula_ipdc("El xiquet jugava amb el nen del veí.")["ipdc"]
    0.5

    Sense cap paraula marcada, compta com a pur:

    >>> r = calcula_ipdc("La casa és gran i té un jardí.")
    >>> r["total_marcades"], r["ipdc"]
    (0, 1.0)
    """
    r = calcula_ipd(text, formes)
    total = r["total_marcades"]
    return {
        "total_paraules": r["total_paraules"],
        "total_occidentals": r["total_occidentals"],
        "total_orientals": r["total_orientals"],
        "total_marcades": total,
        "ipdc": round(r["total_orientals"] / total, 4) if total else 1.0,
        "marcadors_occidentals": r["marcadors_occidentals"],
        "marcadors_orientals": r["marcadors_orientals"],
    }


def calcula_ipdc_corpus(
    path: Path, camp: str = "text", limit: int | None = None
) -> dict:
    """IPDC de cada document de `path` (JSONL o JSON amb un array) i les
    dos xifres globals (vore "CORPUS" al docstring del mòdul)."""
    formes = carrega_formes_dialectals()
    documents = []
    for i, doc in enumerate(_llig_jsonl(path)):
        if limit is not None and i >= limit:
            break
        text = doc.get(camp) or ""
        r = calcula_ipdc(text, formes)
        documents.append({"id": doc.get("id") or doc.get("corpus_id"), "text": text, **r})

    total_or = sum(d["total_orientals"] for d in documents)
    total_marcades = sum(d["total_marcades"] for d in documents)
    return {
        "camp": camp,
        "documents_totals": len(documents),
        "documents_sense_marcadors": sum(1 for d in documents if not d["total_marcades"]),
        "total_occidentals": total_marcades - total_or,
        "total_orientals": total_or,
        "ipdc_global": round(total_or / total_marcades, 4) if total_marcades else 1.0,
        "ipdc_mitjana": (
            round(sum(d["ipdc"] for d in documents) / len(documents), 4) if documents else 1.0
        ),
        "documents": documents,
    }


def _mostra_text(etiqueta: str, r: dict, mostra: int) -> None:
    nota = "" if r["total_marcades"] else " (cap paraula marcada: compta com a pur)"
    print(etiqueta)
    print(f"  IPDC: {r['ipdc']:.4f}{nota}")
    print(
        f"  occidentals={r['total_occidentals']}  orientals={r['total_orientals']}  "
        f"paraules totals={r['total_paraules']}"
    )
    if mostra > 0:
        if r["marcadors_occidentals"]:
            print(f"  marcadors occidentals: {r['marcadors_occidentals'][:mostra]}")
        if r["marcadors_orientals"]:
            print(f"  marcadors orientals:   {r['marcadors_orientals'][:mostra]}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calcula l'Índex de Puresa Dialectal Catalana (IPDC) "
                    "d'un text, fitxer o corpus (0 = gens català, 1 = català pur)."
    )
    grup = parser.add_mutually_exclusive_group(required=True)
    grup.add_argument("--text", help="Frase o text solt a analitzar.")
    grup.add_argument("--fitxer", type=Path, help="Fitxer de text pla a analitzar sencer.")
    grup.add_argument("--corpus", type=Path, help="Fitxer JSONL (o JSON amb un array) amb un document per linia.")
    parser.add_argument("--camp", default="text", help="Camp de text de cada document del --corpus (per defecte: 'text').")
    parser.add_argument("--limit", type=int, default=None, help="Amb --corpus: analitza només els primers N documents.")
    parser.add_argument("--sortida", type=Path, default=None, help="Amb --corpus: fitxer JSON on guardar el detall per document.")
    parser.add_argument("--mostra", type=int, default=10, help="Quants marcadors mostrar de cada dialecte (--text/--fitxer).")
    args = parser.parse_args()

    if args.text is not None:
        _mostra_text("(text solt)", calcula_ipdc(args.text), args.mostra)
        return
    if args.fitxer is not None:
        _mostra_text(str(args.fitxer), calcula_ipdc(args.fitxer.read_text(encoding="utf-8")), args.mostra)
        return

    res = calcula_ipdc_corpus(args.corpus, args.camp, args.limit)
    print(f"Corpus: {args.corpus}  ({res['documents_totals']} documents, camp '{args.camp}')")
    print(f"  IPDC global (suma de marcadors): {res['ipdc_global']}")
    print(f"  IPDC mitjana per document:       {res['ipdc_mitjana']}  "
          f"({res['documents_sense_marcadors']} sense marcadors, compten com a 1.0)")
    print(f"  occidentals={res['total_occidentals']}  orientals={res['total_orientals']}")
    if args.sortida is not None:
        args.sortida.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Guardat detall per document a {args.sortida}")


if __name__ == "__main__":
    main()
