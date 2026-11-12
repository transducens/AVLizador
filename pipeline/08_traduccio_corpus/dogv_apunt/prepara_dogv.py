"""
prepara_dogv.py -- Text del DOGV (`dades/dogv_apunt/dogv_documents.tsv`)
llest per a afegir-lo al KenLM valencià net (10/11/2026, decisió de
l'usuari: provar KenLM amb MaCoCu net + DOGV).

Per què només el DOGV (`analitza_dogv_apunt.py`): és valencià normatiu de
l'AVL (este 91.022 / aquest 29.096, servici 25.568 / servei 7.797, -ix
39.553 / -eix 25.220), però el 21 % dels documents té GD <= 0,5 (textos
amb "aquest", "servei"...). Les notícies de la UA seguixen l'estàndard de
la universitat (GD 0,46: aquest, avui, servei, -eix) i NO entren.

Passos:
1. Partix cada document en frases (salts de línia i `comu._SEPARA`) i
   lleva les repetides (`clau_repetida`; el DOGV en té moltes: fórmules).
2. GD de cada frase única, per lots i en paral·lel, amb el mateix codi
   del filtre valencià (`valencia/filtra_valencia._gd_lot`; idèntic a
   `calcula_gd`).
3. GD de cada document = suma dels marcadors de les seues frases.
4. Es queden les frases dels documents amb GD >= `--min-gd-doc` (0,8),
   menys les que per si soles tenen més marcadors catalans que valencians
   i les dels benchmarks; normalitzades com el text del KenLM
   (`kenlm/exporta_text.normalitza`), de >= 3 tokens.

Eixida: `dades/dogv_apunt/dogv_net.txt` (una frase normalitzada per línia)
i `dogv_net.json` (xifres). Es puja a Abaco i s'ajunta amb
`dades/macocu/kenlm/valencia_net.txt` (vore README.es.md).

Ús (des de l'arrel del repositori):
    python pipeline/08_traduccio_corpus/dogv_apunt/prepara_dogv.py --processos 6
"""

from __future__ import annotations

import argparse
import csv
import json
import multiprocessing as mp
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ARREL = Path(__file__).resolve().parents[3]
MACOCU = ARREL / "pipeline" / "08_traduccio_corpus" / "macocu"
sys.path.insert(0, str(MACOCU))
sys.path.insert(0, str(MACOCU / "kenlm"))
sys.path.insert(0, str(MACOCU / "valencia"))
sys.path.insert(0, str(MACOCU / "fasttext"))
from comu import _SEPARA, clau_repetida  # noqa: E402
from exporta_text import MIN_TOKENS, normalitza  # noqa: E402
from filtra_valencia import _gd_lot, _inicia_treballador  # noqa: E402
from prepara_dades import claus_benchmarks  # noqa: E402

DIR = ARREL / "dades" / "dogv_apunt"


def frases(text: str):
    for paragraf in text.replace("\\n", "\n").split("\n"):
        for frase in _SEPARA.split(paragraf.strip()):
            if frase.strip():
                yield frase.strip()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--entrada", type=Path, default=DIR / "dogv_documents.tsv")
    p.add_argument("--eixida", type=Path, default=DIR / "dogv_net.txt")
    p.add_argument("--min-gd-doc", type=float, default=0.8)
    p.add_argument("--processos", type=int, default=max(1, mp.cpu_count() - 1))
    args = p.parse_args(argv)

    t0 = time.time()
    est: Counter = Counter()
    csv.field_size_limit(10**9)
    docs_frases: dict[str, list[bytes]] = defaultdict(list)
    uniques: dict[bytes, str] = {}
    with open(args.entrada, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            doc = r.get("signatura") or f"_{est['documents']}"
            est["documents"] += 1
            for frase in frases(r.get("text") or ""):
                est["frases"] += 1
                clau = clau_repetida(frase)
                docs_frases[doc].append(clau)
                if clau not in uniques:
                    uniques[clau] = frase
    est["frases_uniques"] = len(uniques)
    print(f"{est['documents']:,} documents, {est['frases']:,} frases, {len(uniques):,} úniques "
          f"({time.time() - t0:,.0f} s)", flush=True)

    # GD de cada frase única (per lots, en paral·lel)
    claus = list(uniques)
    linies = [json.dumps({"text": uniques[c]}, ensure_ascii=False) for c in claus]
    trossos = [linies[i:i + 500] for i in range(0, len(linies), 500)]
    marcadors: dict[bytes, tuple[int, int]] = {}
    fetes = 0
    with mp.Pool(args.processos, initializer=_inicia_treballador, initargs=(-1.0, 0)) as pool:
        for i, resultats in enumerate(pool.imap(_gd_lot, trossos)):
            for j, res in enumerate(resultats):
                if res is not None:
                    r = json.loads(res)
                    marcadors[claus[i * 500 + j]] = (r["occ"], r["ori"])
            fetes += len(resultats)
            if (i + 1) % 40 == 0:
                print(f"  {fetes:,} frases amb GD ({time.time() - t0:,.0f} s)", flush=True)

    # GD de cada document i selecció
    excloses = claus_benchmarks()
    docs_bons = set()
    for doc, cl in docs_frases.items():
        occ = sum(marcadors.get(c, (0, 0))[0] for c in cl)
        ori = sum(marcadors.get(c, (0, 0))[1] for c in cl)
        if occ + ori and occ / (occ + ori) >= args.min_gd_doc:
            docs_bons.add(doc)
        elif not occ + ori:
            est["documents_sense_marcadors"] += 1
    est["documents_bons"] = len(docs_bons)

    vistes: set = set()
    with open(args.eixida, "w", encoding="utf-8") as out:
        for doc, cl in docs_frases.items():
            if doc not in docs_bons:
                continue
            for c in cl:
                if c in vistes:
                    continue
                vistes.add(c)
                occ, ori = marcadors.get(c, (0, 0))
                if ori > occ:
                    est["frases_mes_catalanes"] += 1
                    continue
                if c in excloses:
                    est["frases_benchmark"] += 1
                    continue
                n = normalitza(uniques[c])
                if n.count(" ") + 1 < MIN_TOKENS:
                    est["frases_curtes"] += 1
                    continue
                out.write(n + "\n")
                est["frases_eixida"] += 1
                est["tokens_eixida"] += n.count(" ") + 1
    est["min_gd_doc"] = args.min_gd_doc
    est["segons"] = round(time.time() - t0)
    args.eixida.with_suffix(".json").write_text(json.dumps(est, indent=2), encoding="utf-8")
    print(json.dumps(est, indent=2))


if __name__ == "__main__":
    main()
