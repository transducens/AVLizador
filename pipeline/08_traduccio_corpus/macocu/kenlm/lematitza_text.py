"""
lematitza_text.py -- Passa a LEMES un text d'entrenament de KenLM (una frase
normalitzada per línia) per a entrenar un KenLM de lemes (12/11/2026,
experiment; vore `avlizador.traductor_cat_val.model_llengua.lemes`).

Es queden en la seua forma les paraules candidates dels punts ambigus, les
paraules amb gènere que concorden (DET, NUM, ADJ, PRON) i la puntuació. La
línia d'eixida ja és la que veurà KenLM (la mateixa funció lematitza les
frases que puntua `compara_models.py`). Una línia d'eixida per línia
d'entrada, en el mateix ordre.

L'eixida s'escriu en `<eixida>.part` i es reanomena en acabar (un text a
mitges no es pren mai per bo); al costat, `<eixida sense .txt>.json` amb
els recomptes.

Ús (des de l'arrel del repositori; en Abaco, `lematitza_text.sh`):
    python pipeline/08_traduccio_corpus/macocu/kenlm/lematitza_text.py \
        dades/macocu/kenlm/valencia_net_dogv.txt --eixida dades/macocu/kenlm/valencia_net_dogv_lemes.txt --processos 16
    python pipeline/08_traduccio_corpus/macocu/kenlm/lematitza_text.py ENTRADA --limit 2000   # prova
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import time
from multiprocessing import Pool
from pathlib import Path

_LEM = None


def _inicia() -> None:
    global _LEM
    from avlizador.traductor_cat_val.model_llengua.lemes import LematitzadorLM

    _LEM = LematitzadorLM()


def _lematitza(linies: list[str]) -> list[tuple[str, str]]:
    """(línia d'entrada, línia de lemes) de cada línia del bloc."""
    entrada = [l.rstrip("\n") for l in linies]
    return list(zip(entrada, _LEM.linies(entrada)))


def blocs(fh, mida: int, limit: int | None):
    linies = itertools.islice(fh, limit) if limit else fh
    while True:
        bloc = list(itertools.islice(linies, mida))
        if not bloc:
            return
        yield bloc


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("entrada", type=Path, help="text normalitzat, una frase per línia")
    p.add_argument("--eixida", type=Path, help="per defecte <entrada sense .txt>_lemes.txt")
    p.add_argument("--processos", type=int, default=os.cpu_count() or 1)
    p.add_argument("--bloc", type=int, default=2000, help="línies per tasca")
    p.add_argument("--limit", type=int, default=None, help="només les N primeres línies (proves)")
    a = p.parse_args(argv)
    eixida = a.eixida or a.entrada.with_name(a.entrada.stem + "_lemes.txt")
    part = eixida.with_name(eixida.name + ".part")
    t0, n, tokens, canviats = time.time(), 0, 0, 0
    print(f"{a.entrada} -> {eixida} ({a.processos} processos)", flush=True)
    with a.entrada.open(encoding="utf-8") as fe, part.open("w", encoding="utf-8", newline="\n") as fs, \
            Pool(a.processos, initializer=_inicia) as pool:
        for parells in pool.imap(_lematitza, blocs(fe, a.bloc, a.limit)):
            for e, s in parells:
                fs.write(s + "\n")
                te, ts = e.split(), s.split()
                tokens += len(ts)
                canviats += sum(x != y for x, y in zip(te, ts))
            n += len(parells)
            if n % 100_000 < a.bloc:
                print(f"  {n} línies, {time.time() - t0:.0f} s", flush=True)
    part.replace(eixida)
    resum = {"entrada": str(a.entrada), "eixida": str(eixida), "linies": n, "tokens": tokens,
             "tokens_canviats": canviats, "segons": round(time.time() - t0)}
    eixida.with_name(eixida.stem + ".json").write_text(json.dumps(resum, ensure_ascii=False, indent=1),
                                                       encoding="utf-8")
    print(json.dumps(resum, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
