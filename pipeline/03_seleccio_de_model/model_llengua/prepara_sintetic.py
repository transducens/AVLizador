"""
prepara_sintetic.py -- Text de KenLM a partir del corpus sintètic d'homògrafs
(25/11/2026, petició de l'usuari): prova a banda per a vore si unes frases
escrites per als sentits que casi no apareixen en el corpus real (fartada,
panolla, gandula "vaga", anou, bragues/calces, llavadora, reeixida "èxit",
manca verb/adjectiu, brollador, colp) milloren el KenLM. NO és el sistema.

Entrada: `dades/sintetic_homografs/*.jsonl` (camp `valencia`; vore
`INSTRUCCIONS_GENERACIO.md` en la mateixa carpeta). Eixida: una frase per
línia, normalitzada amb la MATEIXA funció que el text d'entrenament i la
puntuació (`model_llengua.kenlm.normalitza`), repetida `--repeticions`
vegades (la poda de KenLM lleva els n-grames d'ordre >= 2 que només hi són
una vegada: amb una sola còpia, casi tots els contextos sintètics es
perden).

Ús (des de l'arrel del repositori):
    python pipeline/03_seleccio_de_model/model_llengua/prepara_sintetic.py
    python pipeline/03_seleccio_de_model/model_llengua/prepara_sintetic.py --repeticions 3 \\
        --eixida dades/sintetic_homografs/sintetic_net_x3.txt

>>> from avlizador.traductor_cat_val.model_llengua.kenlm import normalitza
>>> normalitza("Va guardar l'anou més grossa.")
"va guardar l' anou més grossa ."
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from avlizador.traductor_cat_val.model_llengua.kenlm import normalitza

ARREL = Path(__file__).resolve().parents[3]
DIR = ARREL / "dades" / "sintetic_homografs"


def frases(directori: Path) -> list[str]:
    """Les frases valencianes normalitzades de tots els `*.jsonl`, sense repetides."""
    vistes: dict[str, None] = {}
    for f in sorted(directori.glob("*.jsonl")):
        for linia in f.read_text(encoding="utf-8").splitlines():
            if linia.strip():
                vistes.setdefault(normalitza(json.loads(linia)["valencia"]), None)
    return list(vistes)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--directori", type=Path, default=DIR)
    p.add_argument("--repeticions", type=int, default=1)
    p.add_argument("--eixida", type=Path, default=DIR / "sintetic_net.txt")
    args = p.parse_args(argv)
    fs = frases(args.directori)
    with args.eixida.open("w", encoding="utf-8", newline="\n") as f:
        for _ in range(args.repeticions):
            f.writelines(x + "\n" for x in fs)
    print(f"{len(fs)} frases x {args.repeticions} -> {args.eixida}")


if __name__ == "__main__":
    main()
