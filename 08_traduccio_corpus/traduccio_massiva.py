"""
traduccio_massiva.py -- Aplica el motor `traductor/` (RuleEngine, pur
basat en regles) a un corpus complet, document a document, en compte
d'una sola frase (CLI, `python -m traductor.cli`) o de les 150 frases
curades del benchmark (`evalua_models.py --model traductor`).

Per què cal això (vore `README.md` d'esta carpeta per al context
complet): cap de les dos vies existents prova el motor contra text REAL
sense seleccionar a mà -- és l'única manera de saber si les regles
actuals es poden donar per bones a escala, i no només sobre el
benchmark.

Ús:
    python traduccio_massiva.py
    python traduccio_massiva.py --input ../dades/avl/final/dialectal/corpus_occidental_net.jsonl --limit 50

Segmentació de frases (simplificació coneguda, vore README, secció
"Limitacions conegudes"): separa per punt/interrogació/exclamació seguit
d'espai -- no gestiona abreviatures ("Dr.", "núm.") ni punts suspensius
amb precisió. Acceptable per a esta primera passada.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))  # traductor/ viu a l'arrel, germana d'esta carpeta

from traductor.translate import translate  # noqa: E402

DEFAULT_INPUT = ROOT_DIR / "dades" / "avl" / "final" / "dialectal" / "corpus_occidental_net.jsonl"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "eixides" / "corpus_traduit_regles.jsonl"

_SEPARADOR_FRASES = re.compile(r"(?<=[.!?])\s+")


def segmenta_frases(text: str) -> list[str]:
    """Separa `text` en frases perquè cada crida a `translate()` tracte
    una sola frase -- necessari perquè `marca_noms_propis()` (vore
    `traductor/rules/__init__.py`) només eximix de sospita de nom propi
    la PRIMERA paraula de tot el que se li passa; si es traduïra el
    document sencer d'una tacada, la primera paraula de cada frase (2a,
    3a...) es marcaria com a possible nom propi i es saltaria."""
    return [f for f in _SEPARADOR_FRASES.split(text.strip()) if f]


def traduix_document(text: str) -> str:
    return " ".join(translate(frase) for frase in segmenta_frases(text))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Corpus .jsonl d'entrada (occidental)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Fitxer .jsonl d'eixida")
    parser.add_argument("--camp-text", default="text", help="Camp del JSON amb el text a traduir (per defecte 'text')")
    parser.add_argument("--limit", type=int, default=None, help="Només els N primers documents (per a proves)")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with args.input.open(encoding="utf-8") as entrada, args.output.open("w", encoding="utf-8") as eixida:
        for i, linia in enumerate(entrada):
            if args.limit is not None and i >= args.limit:
                break
            if not linia.strip():
                continue
            registre = json.loads(linia)
            text_original = registre.get(args.camp_text, "")
            registre_eixida = {
                "id": registre.get("id"),
                "text_occidental": text_original,
                "text_oriental_regles": traduix_document(text_original),
            }
            eixida.write(json.dumps(registre_eixida, ensure_ascii=False) + "\n")
            total += 1

    print(f"{total} documents traduïts -> {args.output}")


if __name__ == "__main__":
    main()
