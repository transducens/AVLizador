#!/usr/bin/env python3
"""traça_verbs_fallats.py -- Per a cada verb d'una llista donada, mostra
UNA traça completa: quina de les 9 capes del motor el toca primer (i amb
quina entrada exacta de `conjugacions_dialectals.json`), i que diu spaCy
d'ell (POS + Mood) en la frase real del benchmark.

Pensat per a respondre "com el classifica el meu sistema / quina regla
del motor de regles utilitza" sobre els 24 casos de col·lisio de mode
verbal en 3a plural trobats el 08/10/2026 (vore CLAUDE.md).

Us:
    python traça_verbs_fallats.py
    python traça_verbs_fallats.py --id RC006
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ARREL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ARREL))

from avlizador.traductor_cat_val.rules import Token, detokenize, marca_noms_propis, tokenize  # noqa: E402
from avlizador.traductor_cat_val.rules import pos_tagger  # noqa: E402
from avlizador.traductor_cat_val.rules.val_cat.accentuacio import AccentuacioRule  # noqa: E402
from avlizador.traductor_cat_val.rules.val_cat.concordanca_dos_dues import ConcordancaDosDuesRule  # noqa: E402
from avlizador.traductor_cat_val.rules.val_cat.conjugacions_dict import DEFAULT_CONJUGACIONS_PATH, ConjugacionsDictRule  # noqa: E402
from avlizador.traductor_cat_val.rules.val_cat.demostratius import DemostratiusRule  # noqa: E402
from avlizador.traductor_cat_val.rules.val_cat.incoatius import IncoatiusRule  # noqa: E402
from avlizador.traductor_cat_val.rules.val_cat.lexic import LexicRule  # noqa: E402
from avlizador.traductor_cat_val.rules.val_cat.numerals import NumeralsRule  # noqa: E402
from avlizador.traductor_cat_val.rules.val_cat.possessius import PossessiusRule  # noqa: E402
from avlizador.traductor_cat_val.rules.val_cat.relatiu_on import RelatiuOnRule  # noqa: E402

REGLES = [
    LexicRule(), ConjugacionsDictRule(), PossessiusRule(), NumeralsRule(),
    ConcordancaDosDuesRule(), RelatiuOnRule(), DemostratiusRule(),
    AccentuacioRule(), IncoatiusRule(),
]

# Els 24 casos reals trobats el 08/10/2026 (RC_id -> paraula valenciana).
CASOS = {
    "RC001": "limiten", "RC006": "creuen", "RC009": "predominen", "RC016": "reben",
    "RC017": "poden", "RC026": "aspiren", "RC040": "quedaren", "RC049": "poden",
    "RC051": "transformaren", "RC057": "designen", "RC062": "poden", "RC069": "procuren",
    "RC070": "passaren", "RC071": "conformen", "RC078": "avalen", "RC079": "estimularen",
    "RC090": "deriven", "RC093": "opten", "RC101": "presenten", "RC107": "originen",
    "RC119": "gustaren", "RC142": "consideren", "RC144": "porten", "RC148": "poden",
}


def traça_frase(text: str, paraula: str) -> dict:
    tokens = tokenize(text)
    marca_noms_propis(tokens)
    pos_tagger.etiqueta(tokens)

    tok_objectiu = next((t for t in tokens if t.surface.lower() == paraula.lower()), None)
    pos_spacy = tok_objectiu.pos if tok_objectiu else None

    regla_que_el_toca = None
    for regla in REGLES:
        abans = tok_objectiu.is_translated if tok_objectiu else None
        tokens = regla.apply(tokens)
        if tok_objectiu and not abans and tok_objectiu.is_translated:
            regla_que_el_toca = regla.__class__.__name__
            break

    return {
        "pos_spacy": pos_spacy,
        "regla": regla_que_el_toca,
        "forma_final": tok_objectiu.translated if tok_objectiu else None,
        "hipotesi_completa": detokenize(tokens),
    }


def busca_entrada(paraula: str) -> dict | None:
    dades = json.loads(DEFAULT_CONJUGACIONS_PATH.read_text(encoding="utf-8"))
    hits = [e for e in dades["entradas"] if e.get("valenciano", "").strip().lower() == paraula.lower()]
    return hits[0] if hits else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--id", default=None, help="Nomes esta frase (p.ex. RC006)")
    args = parser.parse_args()

    bench = json.loads((ARREL / "03_seleccio_de_model" / "benchmark_corpus.json").read_text(encoding="utf-8"))
    bench_per_id = {r["id"]: r for r in bench}

    casos = {args.id: CASOS[args.id]} if args.id else CASOS

    for rid, paraula in casos.items():
        r = bench_per_id[rid]
        entrada = busca_entrada(paraula)
        traça = traça_frase(r["occidental"], paraula)

        print("=" * 100)
        print(f"{rid}: {paraula!r}")
        print(f"  Frase: {r['occidental']}")
        print(f"  Referencia esperava: ...{paraula}... (sense canviar)")
        print(f"  spaCy diu POS={traça['pos_spacy']!r}  -> es deixa passar el filtre (es VERB/AUX)")
        print(f"  Entrada trobada en conjugacions_dialectals.json: {entrada}")
        print(f"  Regla del motor que l'ha tocat: {traça['regla']}")
        print(f"  Resultat: {paraula!r} -> {traça['forma_final']!r}")
        print()


if __name__ == "__main__":
    main()
