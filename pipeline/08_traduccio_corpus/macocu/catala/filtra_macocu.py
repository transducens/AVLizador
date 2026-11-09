"""
filtra_macocu.py -- Trau de MaCoCu-ca 1.0 les frases en català "pur"
(GD = 0 amb almenys 2 marcadors orientals), per a traduir-les després a
valencià amb AVLizador i fer un corpus paral·lel (decisió de l'usuari,
06/11/2026). De moment NO es traduïx res.

Corpus: MaCoCu-ca 1.0 (CLARIN.SI, hdl 11356/1837, CC0), web de 2022,
5,9 M documents. Format "prevert": `<doc ...>` amb metadades, `<p ...>`
amb qualitat jusText, idioma, fluïdesa (lm_score) i si és títol o dada
sensible; el text del paràgraf va en les línies de dins.

Dos passos (vore README.es.md d'esta carpeta):

1. `extreu` (sense spaCy, una passada pel XML de 15 GB):
   - paràgrafs `quality="good"`, `lang="ca"`, no títol, no sensible,
     `lm_score >= --lm-min` (0,7 per defecte: deixa fora el ~10 % pitjor);
   - frases de 8 a 40 paraules, completes, sense llistes ni majúscules
     senceres, amb pocs números (mateix criteri que
     `pipeline/03_seleccio_de_model/benchmark_manual/construeix_pool.py`);
   - sense repetides (text normalitzat);
   - **prefiltre de GD segur**: spaCy només LLEVA marcadors al GD (formes
     verbals que no són verb, homògrafs amb una altra categoria), mai
     n'afig. Així que si una frase, sense spaCy, no arriba a 2 possibles
     marcadors orientals, o té un marcador occidental que no depén
     d'spaCy, el GD exacte mai la donarà com a catalana pura: es pot
     descartar abans sense perdre res. Primer un tall per paraules
     soltes (cota superior, ràpid) i després amb el tokenitzador del
     motor (el mateix que fa servir `calcula_gd`).
   Eixida: `dades/macocu/candidates.jsonl` + `estadistiques_extreu.json`.

2. `gd` (spaCy, en paral·lel i reprenible): `calcula_gd(text,
   dialecte="cat")` de cada candidata; es queden les que tenen GD 0 i
   almenys 2 marcadors. `--fraccio` fa una mostra uniforme i
   determinista (per hash de l'id) i `--maxim` para en arribar a N
   frases.
   Eixida: `dades/macocu/catala_pur.jsonl` + `estadistiques_gd.json`.

Ús (des de l'arrel del repositori):
    python pipeline/08_traduccio_corpus/macocu/catala/filtra_macocu.py extreu
    python pipeline/08_traduccio_corpus/macocu/catala/filtra_macocu.py extreu --limit-mb 200   # prova
    python pipeline/08_traduccio_corpus/macocu/catala/filtra_macocu.py gd --processos 6
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comu import (  # noqa: E402
    DIR,
    XML,
    _PARAULA,
    _SEPARA,
    clau_repetida,
    frase_valida,
    paragraf_bo,
    paragrafs,
)

CANDIDATES = DIR / "candidates.jsonl"
CATALA_PUR = DIR / "catala_pur.jsonl"
PROGRES_GD = DIR / "progres_gd.json"
MIN_MARCADORS = 2


# --------------------------------------------------------------------------
# Prefiltre de GD sense spaCy
# --------------------------------------------------------------------------

class Prefiltre:
    """Descarta frases que el GD exacte mai donaria com a catalanes pures.

    Les dos comprovacions són cotes segures (vore el docstring del mòdul):
    `possibles_orientals` compta per excés i `te_occidental_segur` només
    mira marcadors que no depenen d'spaCy.
    """

    def __init__(self) -> None:
        from avlizador.grau_dialectal import gd

        self.gd = gd
        f = gd.carrega_formes_dialectals()
        self.formes = f
        self.orientals = f.or_simple | f.or_verbal
        # Occidental segur: lèxic simple que no és homògraf (els verbals
        # només compten si spaCy diu VERB; els homògrafs, segons spaCy).
        self.occ_segur = f.occ_simple - set(f.homografs)

    def possibles_orientals(self, text: str) -> int:
        """Cota superior dels marcadors orientals: compta cada paraula i,
        si porta guionet, també cada part."""
        n = 0
        for p in _PARAULA.findall(text.lower()):
            if p in self.orientals:
                n += 1
            if "-" in p:
                n += sum(1 for q in p.split("-") if q in self.orientals)
        return n

    def passa(self, text: str) -> bool:
        if self.possibles_orientals(text) < MIN_MARCADORS:
            return False
        gd = self.gd
        tokens = gd.tokenize(text)
        gd.marca_noms_propis(tokens)
        orientals = 0
        for tok in tokens:
            if tok.surface.isspace() or tok.is_proper_noun:
                continue
            paraula = gd._paraula_per_lookup(tok.surface)
            if paraula is None:
                continue
            baix = paraula.lower()
            if baix in self.occ_segur:
                return False
            if baix in self.orientals:
                orientals += 1
        return orientals >= MIN_MARCADORS


# --------------------------------------------------------------------------
# Pas 1: extreu
# --------------------------------------------------------------------------

def extreu(args: argparse.Namespace) -> None:
    pre = Prefiltre()
    est: Counter = Counter()
    vistes: set[bytes] = set()
    dominis: Counter = Counter()
    limit = args.limit_mb * 1_000_000 if args.limit_mb else None
    t0 = time.time()
    with open(CANDIDATES, "w", encoding="utf-8") as out:
        for doc, par, text in paragrafs(XML, limit):
            est["paragrafs"] += 1
            if not paragraf_bo(par, args.lm_min):
                continue
            est["paragrafs_bons"] += 1
            for i, frase in enumerate(_SEPARA.split(text), 1):
                frase = frase.strip()
                est["frases"] += 1
                if not frase or not frase_valida(frase):
                    continue
                est["frases_valides"] += 1
                clau = clau_repetida(frase)
                if clau in vistes:
                    est["repetides"] += 1
                    continue
                if pre.possibles_orientals(frase) < MIN_MARCADORS:
                    continue
                est["passen_tall_paraules"] += 1
                if not pre.passa(frase):
                    continue
                vistes.add(clau)
                est["candidates"] += 1
                dominis[doc.get("domain", "")] += 1
                out.write(json.dumps({
                    "id": f"{par.get('id')}.s{i}",
                    "doc": doc.get("id"),
                    "domini": doc.get("domain"),
                    "url": doc.get("url"),
                    "lm_score": float(par.get("lm_score", 0)),
                    "text": frase,
                }, ensure_ascii=False) + "\n")
            if est["paragrafs"] % 500_000 == 0:
                print(f"  {est['paragrafs']:,} paràgrafs, {est['candidates']:,} candidates, "
                      f"{time.time() - t0:,.0f} s", flush=True)
    est["segons"] = round(time.time() - t0)
    resum = {"lm_min": args.lm_min, "limit_mb": args.limit_mb, **est,
             "dominis_amb_mes_candidates": dominis.most_common(30)}
    (DIR / "estadistiques_extreu.json").write_text(json.dumps(resum, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in resum.items() if k != "dominis_amb_mes_candidates"}, ensure_ascii=False, indent=2))


# --------------------------------------------------------------------------
# Pas 2: gd
# --------------------------------------------------------------------------

def _en_mostra(id_: str, fraccio: float) -> bool:
    """Mostra uniforme i determinista: la mateixa frase sempre hi és o no.

    >>> _en_mostra("x", 1.0)
    True
    """
    if fraccio >= 1.0:
        return True
    h = int.from_bytes(hashlib.blake2b(id_.encode(), digest_size=8).digest(), "big")
    return h / 2**64 < fraccio


def _gd_de(linia: str) -> str | None:
    from avlizador.grau_dialectal.gd import calcula_gd

    r = json.loads(linia)
    res = calcula_gd(r["text"], dialecte="cat")
    if res["gd"] == 0.0 and res["total_orientals"] >= MIN_MARCADORS:
        r["gd"] = 0.0
        r["marcadors_orientals"] = res["marcadors_orientals"]
        r["total_paraules"] = res["total_paraules"]
        return json.dumps(r, ensure_ascii=False)
    return None


def _inicia_treballador() -> None:
    from avlizador.grau_dialectal.gd import calcula_gd

    calcula_gd("Aquest servei és nou.")  # carrega l'índex i spaCy una vegada


def gd(args: argparse.Namespace) -> None:
    progres = json.loads(PROGRES_GD.read_text()) if PROGRES_GD.exists() and not args.reinicia else {}
    if progres and (progres.get("fraccio") != args.fraccio):
        sys.exit(f"El progrés guardat és amb --fraccio {progres.get('fraccio')}; usa la mateixa o --reinicia.")
    fetes = progres.get("linies", 0)
    pures = progres.get("pures", 0)
    avaluades = progres.get("avaluades", 0)
    mode = "a" if fetes else "w"

    def pendents() -> Iterator[str]:
        with open(CANDIDATES, encoding="utf-8") as f:
            for n, linia in enumerate(f):
                if n < fetes:
                    continue
                yield linia

    t0 = time.time()
    with mp.Pool(args.processos, initializer=_inicia_treballador) as pool, \
            open(CATALA_PUR, mode, encoding="utf-8") as out:
        linies = fetes
        lot: list[str] = []

        def processa(lot: list[str]) -> None:
            nonlocal pures, avaluades
            triades = [l for l in lot if _en_mostra(json.loads(l)["id"], args.fraccio)]
            avaluades += len(triades)
            for res in pool.imap(_gd_de, triades, chunksize=64):
                if res is not None:
                    out.write(res + "\n")
                    pures += 1
            out.flush()

        for linia in pendents():
            lot.append(linia)
            if len(lot) == args.lot:
                processa(lot)
                linies += len(lot)
                lot = []
                PROGRES_GD.write_text(json.dumps({"linies": linies, "pures": pures, "avaluades": avaluades,
                                                  "fraccio": args.fraccio}))
                print(f"  {linies:,} candidates llegides, {avaluades:,} avaluades, {pures:,} pures, "
                      f"{time.time() - t0:,.0f} s", flush=True)
                if args.maxim and pures >= args.maxim:
                    break
        else:
            if lot:
                processa(lot)
                linies += len(lot)
        PROGRES_GD.write_text(json.dumps({"linies": linies, "pures": pures, "avaluades": avaluades,
                                          "fraccio": args.fraccio}))
    resum = {"fraccio": args.fraccio, "candidates_llegides": linies, "avaluades": avaluades,
             "catala_pur": pures, "segons_esta_execucio": round(time.time() - t0)}
    (DIR / "estadistiques_gd.json").write_text(json.dumps(resum, indent=2), encoding="utf-8")
    print(json.dumps(resum, indent=2))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="pas", required=True)
    e = sub.add_parser("extreu", help="pas 1: paràgrafs bons -> frases -> prefiltre de GD (sense spaCy)")
    e.add_argument("--lm-min", type=float, default=0.7, help="fluïdesa mínima del paràgraf (0,7)")
    e.add_argument("--limit-mb", type=int, default=0, help="llegir només els primers N MB (proves)")
    g = sub.add_parser("gd", help="pas 2: GD exacte amb spaCy, es queden les catalanes pures")
    g.add_argument("--processos", type=int, default=max(1, mp.cpu_count() - 2))
    g.add_argument("--fraccio", type=float, default=1.0, help="mostra uniforme de les candidates (0-1)")
    g.add_argument("--maxim", type=int, default=0, help="parar en arribar a N frases pures (0 = totes)")
    g.add_argument("--lot", type=int, default=20_000, help="candidates per lot (cada lot es guarda el progrés)")
    g.add_argument("--reinicia", action="store_true", help="ignorar el progrés guardat i començar de zero")
    args = p.parse_args(argv)
    DIR.mkdir(parents=True, exist_ok=True)
    extreu(args) if args.pas == "extreu" else gd(args)


if __name__ == "__main__":
    main()
