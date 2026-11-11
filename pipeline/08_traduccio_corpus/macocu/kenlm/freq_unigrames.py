"""
freq_unigrames.py -- Freqüència de les paraules candidates (les dels punts
de `model_llengua`) en el text d'entrenament d'un KenLM (11/11/2026).

Per al prior de `compara_models.py`: puntuació = log P(frase) − λ · log
P(candidat), i log P(candidat) ha de ser la freqüència de la paraula. La
probabilitat d'unigrama que guarda KenLM no ho és (amb el suavitzat de
Kneser-Ney, l'unigrama compta en quants contextos distints apareix una
paraula, no quantes vegades: "colp" −10,66 i "vegada" −9,89 en
valencia_net_dogv, quan "vegada" és 35 voltes més freqüent).

Eixida: JSON `{"text", "linies", "tokens", "freq": {paraula: n}}`, amb
`tokens` = paraules + un </s> per línia (com compta KenLM). Per defecte,
al costat del model: `<nom>_freq.json`.

Ús (des de l'arrel del repositori):
    python pipeline/08_traduccio_corpus/macocu/kenlm/freq_unigrames.py dades/macocu/kenlm/valencia_net_dogv.txt
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def candidats() -> set[str]:
    from avlizador.traductor_cat_val.model_llengua.punts import carrega_punts

    return {c.lower() for p, d in carrega_punts().items() for c in [p, *d["candidats"]]}


def compta(text: Path, formes: set[str]) -> dict:
    """
    >>> import tempfile
    >>> t = Path(tempfile.mkdtemp()) / "t.txt"
    >>> _ = t.write_text("una vegada , un colp\\nuna altra vegada\\n", encoding="utf-8")
    >>> r = compta(t, {"colp", "vegada", "gandula"})
    >>> r["linies"], r["tokens"], r["freq"]
    (2, 10, {'colp': 1, 'gandula': 0, 'vegada': 2})
    """
    freq: Counter = Counter()
    linies = tokens = 0
    with text.open(encoding="utf-8") as fh:
        for linia in fh:
            paraules = linia.split()
            if not paraules:
                continue
            linies += 1
            tokens += len(paraules) + 1
            for w in paraules:
                if w in formes:
                    freq[w] += 1
    return {"text": text.name, "linies": linies, "tokens": tokens,
            "freq": {f: freq[f] for f in sorted(formes)}}


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("text", type=Path, help="text d'entrenament (normalitzat, una frase per línia)")
    p.add_argument("--eixida", type=Path, help="per defecte <text sense .txt>_freq.json")
    a = p.parse_args(argv)
    r = compta(a.text, candidats())
    eixida = a.eixida or a.text.with_name(a.text.stem + "_freq.json")
    eixida.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{r['linies']} línies, {r['tokens']} tokens -> {eixida}")
    for f, n in sorted(r["freq"].items(), key=lambda x: -x[1]):
        print(f"  {f:12s} {n}")


if __name__ == "__main__":
    main()
