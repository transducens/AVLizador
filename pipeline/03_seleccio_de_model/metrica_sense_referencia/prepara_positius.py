"""Pas 1: parells positius (src català, mt valencià) i candidats d'homògrafs.

Fonts paral·leles (les úniques amb el català d'origen):
- BOE alineat (`dades/boe/corpus_entrenamiento.jsonl`), document a document;
- corpus sintètic de l'AVL (`dades/sintetic/parallel.{cat,val}`): el
  valencià és text real de l'AVL; el català, d'un LLM.

Cap salida d'AVLizador entra ací. Es descarten:
- les frases dels benchmarks d'avaluació (exactes i quasi iguals) i les
  línies del BOE d'on ix el benchmark manual (`comu.Exclusions`; amb
  `--exclou-documents`, els documents sencers);
- parells repetits, idèntics, mal alineats (similitud < 0,5) i frases
  fora de 8-60 paraules.

POSITIU = el valencià té GD = 1 amb almenys `--min-marcadors` marcadors
(cap forma catalana del lèxic) i el català, cap marcador valencià i almenys
un de català. El GD és el del paquet (spaCy per als verbs i els homògrafs).

CANDIDAT D'HOMÒGRAF = el català porta una forma ambigua del lèxico ("nou",
"deu", "cop"...) i el valencià no té cap marcador català; es fan servir per
als negatius de tipus 3.

Eixides en `dades/metrica_sense_referencia/`: `positius.jsonl`,
`homografs_corpus.jsonl`, `estadistiques_positius.json`.

    python prepara_positius.py [--processos 4] [--maxim N] [--min-marcadors 2]
"""
from __future__ import annotations

import argparse
import collections
import difflib
import json
import multiprocessing as mp
import time

import comu

BOE = comu.DADES / "boe" / "corpus_entrenamiento.jsonl"
SINTETIC_CAT = comu.DADES / "sintetic" / "parallel.cat"
SINTETIC_VAL = comu.DADES / "sintetic" / "parallel.val"
MIN_PARAULES, MAX_PARAULES = 8, 60
MIN_SIMILITUD = 0.5


def llig_fonts(maxim: int | None):
    with open(BOE, encoding="utf-8") as f:
        for i, linia in enumerate(f):
            if maxim and i >= maxim:
                break
            x = json.loads(linia)
            yield {"id": x["id"], "font": "boe", "doc": x["documento_id"],
                   "src": x["texto_catalan"], "mt": x["texto_valenciano"]}
    for i, (c, v) in enumerate(realinea_sintetic()):
        if maxim and i >= maxim:
            break
        yield {"id": f"SIN-{i:05d}", "font": "avl_sintetic", "doc": f"SIN-{i:05d}", "src": c, "mt": v}


def realinea_sintetic(finestra: int = 40, minim: float = 0.6) -> list[tuple[str, str]]:
    """Parells (català, valencià) del corpus sintètic. Des de la línia
    17.172 el català porta restes del LLM ("/no_think", "</think>", línies
    buides) i les dos columnes es desplacen: cada línia valenciana
    s'empareja amb la catalana més pareguda dins d'una finestra cap avant
    (monòton). Les que no en tenen cap amb similitud >= `minim` es perden."""
    with open(SINTETIC_CAT, encoding="utf-8") as f:
        cat = [l.strip() for l in f]
    with open(SINTETIC_VAL, encoding="utf-8") as f:
        val = [l.strip() for l in f]
    parells, j = [], 0
    for v in val:
        nv = comu.norm(v)
        millor, jm = 0.0, None
        for k in range(j, min(j + finestra, len(cat))):
            sm = difflib.SequenceMatcher(None, comu.norm(cat[k]), nv, autojunk=False)
            if sm.real_quick_ratio() < minim or sm.quick_ratio() < minim:
                continue
            r = sm.ratio()
            if r > millor:
                millor, jm = r, k
                if r > 0.95:
                    break
        if jm is not None and millor >= minim:
            parells.append((cat[jm], v))
            j = jm + 1
    return parells


# --- Treballadors (spaCy) -------------------------------------------------

_F = None


def _init() -> None:
    global _F
    _F = comu.gd.carrega_formes_dialectals()


def _classifica(text: str):
    toks = comu.gd._tokenitza_amb_pos(text)
    occ, orr = [], []
    for i, t in enumerate(toks):
        c = comu.gd._classifica_token(t, _F, toks, i)
        if c == "occ":
            occ.append([i, comu.paraula_del_token(t.surface)])
        elif c == "or":
            orr.append([i, comu.paraula_del_token(t.surface)])
    return occ, orr


def _processa(args):
    x, min_marcadors = args
    occ_mt, or_mt = _classifica(x["mt"])
    res = {}
    if x["cand_positiu"] and len(occ_mt) >= min_marcadors and not or_mt:
        occ_src, or_src = _classifica(x["src"])
        if not occ_src and or_src:
            res["positiu"] = {**x, "marcadors": occ_mt, "marcadors_src": or_src}
    if x["cand_homograf"] and not or_mt:
        res["homograf"] = {**x, "marcadors": occ_mt}
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--processos", type=int, default=4)
    ap.add_argument("--maxim", type=int, default=None, help="línies de cada font (per a provar)")
    ap.add_argument("--min-marcadors", type=int, default=2)
    ap.add_argument("--exclou-documents", action="store_true",
                    help="descarta també els documents del BOE d'on ix el manual (sencers)")
    args = ap.parse_args()

    t0 = time.time()
    E = comu.Exclusions()
    F = comu.gd.carrega_formes_dialectals()
    occ_formes = F.occ_simple | F.occ_verbal
    homo_cat = set(comu.homografs_cat_val())

    stats = collections.Counter()
    vistos = set()
    candidats = []
    for x in llig_fonts(args.maxim):
        stats[f"{x['font']}:llegits"] += 1
        n = len(x["mt"].split())
        if not (MIN_PARAULES <= n <= MAX_PARAULES):
            stats[f"{x['font']}:llargaria"] += 1
            continue
        ns, nm = comu.norm(x["src"]), comu.norm(x["mt"])
        if ns == nm:
            stats[f"{x['font']}:identics"] += 1
            continue
        if (ns, nm) in vistos:
            stats[f"{x['font']}:repetits"] += 1
            continue
        vistos.add((ns, nm))
        if difflib.SequenceMatcher(None, ns, nm, autojunk=False).ratio() < MIN_SIMILITUD:
            stats[f"{x['font']}:mal_alineats"] += 1
            continue
        motiu = E.motiu(x["src"], x["mt"], id=x["id"],
                        doc=x["doc"] if (x["font"] == "boe" and args.exclou_documents) else None)
        if motiu:
            stats[f"{x['font']}:exclos_{motiu}"] += 1
            continue
        # Prefiltre sense spaCy: almenys `min` paraules que podrien ser marcadors.
        ps_mt = [comu.paraula_del_token(t.surface) for t in comu.tokenize(x["mt"])]
        possibles = sum(1 for p in ps_mt if p in occ_formes)
        x["cand_positiu"] = possibles >= args.min_marcadors
        x["cand_homograf"] = any(p in homo_cat for p in comu.paraules(x["src"]))
        if x["cand_positiu"] or x["cand_homograf"]:
            candidats.append(x)
        else:
            stats[f"{x['font']}:sense_prou_marcadors"] += 1
    print(f"Candidats per a spaCy: {len(candidats)} ({time.time() - t0:.0f} s)", flush=True)

    positius, homografs = [], []
    with mp.Pool(args.processos, initializer=_init) as pool:
        for k, r in enumerate(pool.imap(_processa, ((x, args.min_marcadors) for x in candidats), chunksize=64)):
            if "positiu" in r:
                positius.append(r["positiu"])
            if "homograf" in r:
                homografs.append(r["homograf"])
            if (k + 1) % 10000 == 0:
                print(f"  {k + 1}/{len(candidats)}  positius {len(positius)}  ({time.time() - t0:.0f} s)", flush=True)

    for p in positius:
        stats[f"{p['font']}:positius"] += 1
    for h in homografs:
        stats[f"{h['font']}:homografs"] += 1
    comu.EIXIDA.mkdir(parents=True, exist_ok=True)
    for nom, files in (("positius.jsonl", positius), ("homografs_corpus.jsonl", homografs)):
        with open(comu.EIXIDA / nom, "w", encoding="utf-8") as f:
            for x in files:
                x.pop("cand_positiu", None)
                x.pop("cand_homograf", None)
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
    stats["segons"] = round(time.time() - t0)
    (comu.EIXIDA / "estadistiques_positius.json").write_text(
        json.dumps(dict(sorted(stats.items())), ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
