"""
tradueix_macocu.py -- Traduïx a valencià amb AVLizador les frases en
català pur de MaCoCu-ca (`catala_pur.jsonl`, eixida de `filtra_macocu.py`)
i fa el corpus paral·lel català/valencià (decisió de l'usuari, 09/11/2026).
Primer ús previst: entrenar un KenLM o fastText que faça el que fa hui FLOR
sense el biaix cap al català.

Decisions (vore README.es.md, secció "Calidad de los datos"):
- Es tradueix TOT, sense mostreig ni límits per document o domini.
- Fora 4 dominis amb text roín (`DOMINIS_EXCLOSOS`): PDF mal extret i
  traducció automàtica de l'anglés.
- Les frases amb paraules ambigües (les que passen per spaCy/FLOR) NO es
  lleven: van etiquetades amb qui ha decidit cada paraula, per a revisar-les.

Dos passos, els dos en paral·lel i reprenibles:

1. `motor` (spaCy, sense FLOR): motor de regles + detecció de paraules
   ambigües (`tradueix_cat_val_ml(text)` sense model). Les frases SENSE
   paraules ambigües ja són la traducció final (el sistema complet dona
   exactament el mateix: sense punts, `aplica_tries` torna el text del
   motor) i van a `paralel_motor.jsonl`. Les que en tenen van a
   `pendents_flor.jsonl`.
2. `flor`: el sistema complet (motor + spaCy + FLOR-760M, criteri per
   defecte: catalana per defecte i marge 2, el mateix que
   `translate_cat_val`) per a les pendents -> `paralel_flor.jsonl`. Cada
   procés carrega FLOR una vegada (~1,5 GB) i fa servir `--fils` fils.

Cada línia d'eixida:
    {"id", "doc", "domini", "url", "catala", "valencia",
     "canvis": [["aquest", "este"], ...],     # diferències per paraules
     "gd_val", "gdv_val", "marcadors_orientals_val",   # GD de l'eixida
     "punts": [{"paraula", "tipus", "candidats", "motor", "tria",
                "decidit", "pos", "puntuacions"}],      # només en el pas 2
     "revisar": bool}   # alguna paraula ambigua NO l'ha decidida spaCy
                        # (FLOR, la catalana per defecte o el motor)

GD de l'eixida amb `dialecte="val"` (sense marcadors = 1,0); GDV = 1 -
orientals / paraules (com `gdv.calcula_gdv`, sense tornar a passar spaCy).

Ús (des de l'arrel del repositori):
    python pipeline/08_traduccio_corpus/macocu/catala/tradueix_macocu.py motor --processos 6
    python pipeline/08_traduccio_corpus/macocu/catala/tradueix_macocu.py motor --processos 6 --maxim 10000   # prova
    python pipeline/08_traduccio_corpus/macocu/catala/tradueix_macocu.py flor --processos 2 --fils 3
"""

from __future__ import annotations

import argparse
import difflib
import json
import multiprocessing as mp
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Iterator

ARREL = Path(__file__).resolve().parents[4]
DIR = ARREL / "dades" / "macocu"
CATALA_PUR = DIR / "catala_pur.jsonl"
PARALEL_MOTOR = DIR / "paralel_motor.jsonl"
PENDENTS_FLOR = DIR / "pendents_flor.jsonl"
PARALEL_FLOR = DIR / "paralel_flor.jsonl"

# Decisió de l'usuari (09/11/2026): PDF mal extret (falten lletres) i
# traducció automàtica de l'anglés. 66.388 frases (1,5 %).
DOMINIS_EXCLOSOS = frozenset({"pdfslide.tips", "dokumen.tips", "ca.eferrit.com", "ca.whattalking.com"})


def canvis(catala: str, valencia: str) -> list[list[str]]:
    """Diferències per paraules (separades per espais) entre l'entrada i
    l'eixida.

    >>> canvis("Aquest any la seva feina.", "Este any la seua faena.")
    [['Aquest', 'Este'], ['seva feina.', 'seua faena.']]
    >>> canvis("Igual.", "Igual.")
    []
    """
    a, b = catala.split(" "), valencia.split(" ")
    return [[" ".join(a[i1:i2]), " ".join(b[j1:j2])]
            for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes()
            if op != "equal"]


def gd_eixida(valencia: str) -> dict:
    """GD (dialecte "val") i GDV de la traducció amb una sola passada.

    >>> r = gd_eixida("Este xiquet vol vindre hui.")
    >>> r["gd_val"], r["gdv_val"], r["marcadors_orientals_val"]
    (1.0, 1.0, [])
    """
    from avlizador.grau_dialectal.gd import calcula_gd

    r = calcula_gd(valencia, dialecte="val")
    total = r["total_paraules"]
    return {
        "gd_val": r["gd"],
        "gdv_val": round(1 - r["total_orientals"] / total, 4) if total else 1.0,
        "marcadors_orientals_val": r["marcadors_orientals"],
    }


def _punt_a_dict(p) -> dict:
    return {
        "paraula": p.paraula,
        "tipus": p.tipus,
        "candidats": list(p.candidats),
        "motor": p.motor,
        "tria": p.tria,
        "decidit": p.decidit,
        "pos": p.pos,
        "puntuacions": {c: {"lp": round(d["lp"], 3), "prior": round(d["prior"], 3), "n": d["n"]}
                        for c, d in (p.puntuacions or {}).items()},
    }


def registre(r: dict, valencia: str, punts: list | None = None) -> str:
    punts = [_punt_a_dict(p) for p in (punts or [])]
    eix = {
        "id": r["id"], "doc": r["doc"], "domini": r["domini"], "url": r["url"],
        "catala": r["text"], "valencia": valencia,
        "canvis": canvis(r["text"], valencia),
        **gd_eixida(valencia),
        "punts": punts,
        "revisar": any(p["decidit"] != "spacy" for p in punts),
    }
    return json.dumps(eix, ensure_ascii=False)


# --------------------------------------------------------------------------
# Treballadors
# --------------------------------------------------------------------------

def _inicia_motor() -> None:
    from avlizador.traductor_cat_val.model_llengua import tradueix_cat_val_ml

    tradueix_cat_val_ml("Aquest cop és nou.")  # carrega el motor, els punts i spaCy
    gd_eixida("Este xiquet vol vindre hui.")    # i l'índex del GD


def _tradueix_motor(linia: str) -> tuple[str, str]:
    """("motor", registre final) o ("flor", línia d'entrada sense tocar)."""
    from avlizador.traductor_cat_val.model_llengua import tradueix_cat_val_ml

    r = json.loads(linia)
    valencia, punts = tradueix_cat_val_ml(r["text"])
    if punts:
        return "flor", linia.rstrip("\n")
    return "motor", registre(r, valencia)


_MODEL = None


def _inicia_flor(fils: int) -> None:
    global _MODEL
    from avlizador.traductor_cat_val.model_llengua.puntuador import ModelLlengua

    _MODEL = ModelLlengua(fils=fils)
    _inicia_motor()


def _tradueix_flor(linia: str) -> str:
    from avlizador.traductor_cat_val.model_llengua import Criteri, tradueix_cat_val_ml

    r = json.loads(linia)
    valencia, punts = tradueix_cat_val_ml(r["text"], _MODEL, Criteri())
    if len(_MODEL._cache) > 200_000:  # la memòria cau de log-probabilitats no ha de créixer sense límit
        _MODEL._cache.clear()
    return registre(r, valencia, punts)


# --------------------------------------------------------------------------
# Bucle comú: lots, progrés i reprendre
# --------------------------------------------------------------------------

def _executa(pas: str, entrada: Path, eixides: dict[str, Path], funcio, pool, args, filtre=None) -> dict:
    progres_path = DIR / f"progres_{pas}.json"
    progres = json.loads(progres_path.read_text()) if progres_path.exists() and not args.reinicia else {}
    fetes = progres.get("linies", 0)
    comptes = Counter(progres.get("comptes", {}))
    mode = "a" if fetes else "w"
    if fetes:
        # Si el job es va tallar a mitjan lot, les eixides tenen línies
        # posteriors al progrés guardat: es retallen per a no duplicar-les.
        for k, p in eixides.items():
            if p.exists():
                os.truncate(p, progres.get("mides", {}).get(k, 0))
    fitxers = {k: open(p, mode, encoding="utf-8") for k, p in eixides.items()}

    def pendents() -> Iterator[str]:
        with open(entrada, encoding="utf-8") as f:
            for n, linia in enumerate(f):
                if n >= fetes:
                    yield linia

    def guarda(linies: int) -> None:
        for f in fitxers.values():
            f.flush()
        mides = {k: os.path.getsize(p) for k, p in eixides.items()}
        progres_path.write_text(json.dumps({"linies": linies, "comptes": comptes, "mides": mides}))

    t0 = time.time()
    linies = fetes
    lot: list[str] = []

    def processa(lot: list[str]) -> None:
        bones = []
        for l in lot:
            if filtre is not None and not filtre(l):
                comptes["exclosa_domini"] += 1
            else:
                bones.append(l)
        for res in pool.imap(funcio, bones, chunksize=args.chunk):
            clau, text = res if isinstance(res, tuple) else (next(iter(fitxers)), res)
            fitxers[clau].write(text + "\n")
            comptes[clau] += 1
            if clau != "flor" and '"revisar": true' in text:
                comptes["revisar"] += 1

    try:
        for linia in pendents():
            lot.append(linia)
            if len(lot) == args.lot:
                processa(lot)
                linies += len(lot)
                lot = []
                guarda(linies)
                print(f"  {linies:,} línies, {dict(comptes)}, {time.time() - t0:,.0f} s", flush=True)
                if args.maxim and linies - fetes >= args.maxim:
                    break
        else:
            if lot:
                processa(lot)
                linies += len(lot)
        guarda(linies)
    finally:
        for f in fitxers.values():
            f.close()
    resum = {"pas": pas, "linies_llegides": linies, **comptes, "segons_esta_execucio": round(time.time() - t0)}
    (DIR / f"estadistiques_{pas}.json").write_text(json.dumps(resum, indent=2), encoding="utf-8")
    print(json.dumps(resum, indent=2))
    return resum


def _no_exclosa(linia: str) -> bool:
    """
    >>> _no_exclosa('{"domini": "ca.eferrit.com"}'), _no_exclosa('{"domini": "ara.cat"}')
    (False, True)
    """
    return json.loads(linia)["domini"] not in DOMINIS_EXCLOSOS


def pas_motor(args: argparse.Namespace) -> None:
    with mp.Pool(args.processos, initializer=_inicia_motor) as pool:
        _executa("motor", CATALA_PUR, {"motor": PARALEL_MOTOR, "flor": PENDENTS_FLOR},
                 _tradueix_motor, pool, args, filtre=_no_exclosa)


def pas_flor(args: argparse.Namespace) -> None:
    if not PENDENTS_FLOR.exists():
        sys.exit(f"Falta {PENDENTS_FLOR}: primer el pas `motor`.")
    with mp.Pool(args.processos, initializer=_inicia_flor, initargs=(args.fils,)) as pool:
        _executa("flor", PENDENTS_FLOR, {"paralel_flor": PARALEL_FLOR}, _tradueix_flor, pool, args)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="pas", required=True)
    m = sub.add_parser("motor", help="pas 1: motor + spaCy; separa les frases amb paraules ambigües")
    m.add_argument("--processos", type=int, default=max(1, mp.cpu_count() - 1))
    m.add_argument("--lot", type=int, default=20_000)
    m.add_argument("--chunk", type=int, default=64)
    f = sub.add_parser("flor", help="pas 2: sistema complet (FLOR) per a les frases amb paraules ambigües")
    f.add_argument("--processos", type=int, default=2)
    f.add_argument("--fils", type=int, default=4, help="fils de torch per procés")
    f.add_argument("--lot", type=int, default=2_000)
    f.add_argument("--chunk", type=int, default=4)
    for s in (m, f):
        s.add_argument("--maxim", type=int, default=0, help="parar després de llegir unes N línies més (proves)")
        s.add_argument("--reinicia", action="store_true", help="ignorar el progrés guardat i començar de zero")
    args = p.parse_args(argv)
    DIR.mkdir(parents=True, exist_ok=True)
    pas_motor(args) if args.pas == "motor" else pas_flor(args)


if __name__ == "__main__":
    main()
