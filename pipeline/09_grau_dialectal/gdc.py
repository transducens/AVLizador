#!/usr/bin/env python3
"""
gdc.py -- Grau Dialectal Català (GDC): quina part de les paraules d'un
text és vàlida en català. 1.0 = totes, 0.0 = cap.

    GDC = (total_orientals + neutres) / total_paraules
        = 1 - total_occidentals / total_paraules

Germà simètric d'`gdv.py` (Grau Dialectal Valencià).

NEUTRES (decisió de l'usuari, 27/10/2026): les paraules que no són
marcador de cap dialecte ("casa", "amb", "el"...) són vàlides en els
dos, així que compten a favor del GDC (i del GDV). Només resten les
formes valencianes (occidentals). Motiu: el GDC s'ha de poder fer servir
de recompensa per a entrenar models, i una frase sense marcadors també
seguix l'estàndard català. Diferència amb el GD (`gd.py`), que es queda
tal qual: el GD només mira els marcadors (occidentals / marcades) i
ignora les neutres. Per això ara GDV + GDC no suma 1 (amb neutres, els
dos s'acosten a 1).

Límit: "neutra" vol dir "no està al diccionari de parells", no "és
correcta" -- un castellanisme o una paraula dialectal que el diccionari
no recull també hi compten com a vàlides.

Text sense cap paraula: GDC = 1.0 (no hi ha res que el desmentisca).

No reimplementa res: els marcadors i el recompte de paraules els fa
`gd.py::calcula_gd` (mateix índex de parells del traductor, mateix
filtre de POS i d'homògrafs).

CORPUS: dona dos xifres:
  - `gdc_global`: 1 - occidentals / paraules de tot el corpus (cada
    paraula pesa igual, les frases llargues pesen més);
  - `gdc_mitjana`: mitjana del GDC de cada frase (cada frase pesa igual).

ÚS com a script:

    python gdc.py --text "Aquest nen vol venir avui."
    python gdc.py --fitxer un_document.txt
    python gdc.py --corpus ../03_seleccio_de_model/benchmark_corpus.json \
        --camp oriental --sortida gdc.json

ÚS com a mòdul:

    from gdc import calcula_gdc
    calcula_gdc("Aquest nen vol venir avui.")["gdc"]  # -> 1.0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_DIR = str(Path(__file__).resolve().parent)
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from gd import Formes, _llig_jsonl, calcula_gd, carrega_formes_dialectals  # noqa: E402


def calcula_gdc(text: str, formes: Formes | None = None) -> dict:
    """Calcula el GDC d'un text solt (frase, paràgraf o document).

    >>> calcula_gdc("Aquest nen vol venir avui.")["gdc"]
    1.0

    4 de 5 paraules valencianes ("este", "xiquet", "vindre", "hui");
    "vol" és neutra i compta com a catalana:

    >>> calcula_gdc("Este xiquet vol vindre hui.")["gdc"]
    0.2

    1 forma valenciana ("xiquet") de 8 paraules:

    >>> calcula_gdc("El xiquet jugava amb el nen del veí.")["gdc"]
    0.875

    Sense cap paraula marcada, totes són neutres:

    >>> r = calcula_gdc("La casa és gran i té un jardí.")
    >>> r["total_marcades"], r["total_neutres"], r["gdc"]
    (0, 8, 1.0)
    """
    r = calcula_gd(text, formes)
    total = r["total_paraules"]
    return {
        "total_paraules": total,
        "total_occidentals": r["total_occidentals"],
        "total_orientals": r["total_orientals"],
        "total_marcades": r["total_marcades"],
        "total_neutres": total - r["total_marcades"],
        "gdc": round(1 - r["total_occidentals"] / total, 4) if total else 1.0,
        "marcadors_occidentals": r["marcadors_occidentals"],
        "marcadors_orientals": r["marcadors_orientals"],
    }


def calcula_gdc_corpus(
    path: Path, camp: str = "text", limit: int | None = None
) -> dict:
    """GDC de cada document de `path` (JSONL o JSON amb un array) i les
    dos xifres globals (vore "CORPUS" al docstring del mòdul)."""
    formes = carrega_formes_dialectals()
    documents = []
    for i, doc in enumerate(_llig_jsonl(path)):
        if limit is not None and i >= limit:
            break
        text = doc.get(camp) or ""
        r = calcula_gdc(text, formes)
        documents.append({"id": doc.get("id") or doc.get("corpus_id"), "text": text, **r})

    total_occ = sum(d["total_occidentals"] for d in documents)
    total_or = sum(d["total_orientals"] for d in documents)
    total_paraules = sum(d["total_paraules"] for d in documents)
    return {
        "camp": camp,
        "documents_totals": len(documents),
        "documents_sense_marcadors": sum(1 for d in documents if not d["total_marcades"]),
        "total_paraules": total_paraules,
        "total_occidentals": total_occ,
        "total_orientals": total_or,
        "total_neutres": total_paraules - total_occ - total_or,
        "gdc_global": round(1 - total_occ / total_paraules, 4) if total_paraules else 1.0,
        "gdc_mitjana": (
            round(sum(d["gdc"] for d in documents) / len(documents), 4) if documents else 1.0
        ),
        "documents": documents,
    }


def _mostra_text(etiqueta: str, r: dict, mostra: int) -> None:
    print(etiqueta)
    print(f"  GDC: {r['gdc']:.4f}")
    print(
        f"  occidentals={r['total_occidentals']}  orientals={r['total_orientals']}  "
        f"neutres={r['total_neutres']}  paraules totals={r['total_paraules']}"
    )
    if mostra > 0:
        if r["marcadors_occidentals"]:
            print(f"  marcadors occidentals: {r['marcadors_occidentals'][:mostra]}")
        if r["marcadors_orientals"]:
            print(f"  marcadors orientals:   {r['marcadors_orientals'][:mostra]}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calcula el Grau Dialectal Català (GDC) d'un text, fitxer o corpus: "
                    "part de les paraules vàlides en català (marcadors catalans + neutres)."
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
        _mostra_text("(text solt)", calcula_gdc(args.text), args.mostra)
        return
    if args.fitxer is not None:
        _mostra_text(str(args.fitxer), calcula_gdc(args.fitxer.read_text(encoding="utf-8")), args.mostra)
        return

    res = calcula_gdc_corpus(args.corpus, args.camp, args.limit)
    print(f"Corpus: {args.corpus}  ({res['documents_totals']} documents, camp '{args.camp}')")
    print(f"  GDC global (per paraula):  {res['gdc_global']}")
    print(f"  GDC mitjana per document:  {res['gdc_mitjana']}  "
          f"({res['documents_sense_marcadors']} sense marcadors)")
    print(f"  occidentals={res['total_occidentals']}  orientals={res['total_orientals']}  "
          f"neutres={res['total_neutres']}  paraules totals={res['total_paraules']}")
    if args.sortida is not None:
        args.sortida.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Guardat detall per document a {args.sortida}")


if __name__ == "__main__":
    main()
