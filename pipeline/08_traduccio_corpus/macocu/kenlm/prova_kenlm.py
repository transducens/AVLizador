"""
prova_kenlm.py -- Prova ràpida d'un model KenLM: puntua frases
(normalitzades igual que el text d'entrenament) i, si se li passen grups
separats per " | ", diu quina variant prefereix i per quant.

Ús:
    python prova_kenlm.py dades/macocu/kenlm/macocu_tot_o5.binary \\
        "Una altra vegada hem guanyat. | Un altre colp hem guanyat. | Un altre cop hem guanyat."
    python prova_kenlm.py MODEL --fitxer frases.txt   # una línia per grup

La puntuació és log10 P(frase) (com més alta, més probable); la diferència
entre dues variants en log10: 1 = 10 vegades més probable.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from exporta_text import normalitza  # noqa: E402


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("model", type=Path)
    p.add_argument("grups", nargs="*", help='variants separades per " | "')
    p.add_argument("--fitxer", type=Path)
    args = p.parse_args(argv)

    import kenlm

    lm = kenlm.Model(str(args.model))
    print(f"Model: {args.model} (ordre {lm.order})")
    grups = list(args.grups)
    if args.fitxer:
        grups += [l.strip() for l in args.fitxer.read_text(encoding="utf-8").splitlines() if l.strip()]
    for g in grups:
        variants = [v.strip() for v in g.split("|") if v.strip()]
        punts = [(lm.score(normalitza(v), bos=True, eos=True), v) for v in variants]
        millor = max(punts)[0]
        print()
        for s, v in sorted(punts, reverse=True):
            oov = [w for w in normalitza(v).split() if w not in lm]
            print(f"  {s:9.3f}  {s - millor:+7.3f}  {v}" + (f"   [fora de vocabulari: {', '.join(oov)}]" if oov else ""))


if __name__ == "__main__":
    main()
