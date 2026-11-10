"""
filtra_valencia.py -- Trau de MaCoCu-ca 1.0 les frases amb formes
valencianes: GD > 0,5 (més marcadors occidentals que orientals), per a
tindre valencià real del corpus (decisió de l'usuari, 09/11/2026). És el
filtre simètric de `../catala/filtra_macocu.py`.

Segons l'anàlisi del corpus sencer (`../analitza_macocu.py`, mostra del
2 %), ~5-6 % de les frases tenen GD > 0,5, però moltes només per falsos
marcadors del GD que també són català normal ("vegada", "permet",
"alcalde", "últim"...). Per això es guarden els marcadors de cada frase:
es podrà filtrar després (per exemple, amb `--min-marcadors 2`) sense
tornar a passar spaCy.

Dos passos (vore README.es.md d'esta carpeta):

1. `extreu` (sense spaCy, una passada pel XML):
   - els mateixos paràgrafs i frases que el filtre català (`comu.py`):
     `good`, `ca`, no títol, no sensible, `lm_score >= 0,7`; frases de 8 a
     40 paraules, completes, sense repetides. (El `lm_score` castiga una
     mica el valencià, 6,5 % per davall de 0,7 davant del 2 % del català,
     però les frases que lleva són brossa: castellà, wiki sense netejar,
     lletres que falten.) Els paràgrafs en castellà (`lang="es"`) queden
     fora: "este", "esta", "alcalde", "vos" hi són marcadors valencians;
   - **prefiltre segur**: spaCy només LLEVA marcadors al GD (formes
     verbals que no són verb, homògrafs), mai n'afig. Sense spaCy es
     calcula una cota superior dels occidentals (tots els possibles) i una
     cota inferior dels orientals (els que no depenen d'spaCy: lèxic simple
     que no és homògraf). Si la cota superior occidental no arriba al
     mínim de marcadors o no supera la inferior oriental, el GD exacte
     mai pot ser > 0,5: es descarta sense perdre res.
   Eixida: `dades/macocu/valencia/candidates.jsonl` + `estadistiques_extreu.json`.

2. `gd` (spaCy, en paral·lel i reprenible): `calcula_gd(text)`; es
   queden les de GD > `--min-gd` (0,5) amb almenys `--min-marcadors` (1).
   Eixida: `dades/macocu/valencia/valencia.jsonl` + `estadistiques_gd.json`,
   amb `gd`, `occ`, `ori`, `marcadors_occidentals`, `marcadors_orientals`
   i `total_paraules`. Des del 10/11/2026 no crida `calcula_gd` frase a
   frase sinó `_gd_lot` (mateix resultat, ~3 vegades més ràpid).

Ús (des de l'arrel del repositori):
    python pipeline/08_traduccio_corpus/macocu/valencia/filtra_valencia.py extreu
    python pipeline/08_traduccio_corpus/macocu/valencia/filtra_valencia.py extreu --limit-mb 200   # prova
    python pipeline/08_traduccio_corpus/macocu/valencia/filtra_valencia.py extreu --processos 4
    python pipeline/08_traduccio_corpus/macocu/valencia/filtra_valencia.py gd --processos 6
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comu import DIR, XML, _PARAULA, _SEPARA, clau_repetida, frase_valida, paragraf_bo, paragrafs  # noqa: E402

DIR_VAL = DIR / "valencia"
CANDIDATES = DIR_VAL / "candidates.jsonl"
VALENCIA = DIR_VAL / "valencia.jsonl"
PROGRES_GD = DIR_VAL / "progres_gd.json"


# --------------------------------------------------------------------------
# Prefiltre de GD sense spaCy
# --------------------------------------------------------------------------

class Prefiltre:
    """Descarta frases que el GD exacte mai donaria > `min_gd`.

    >>> p = Prefiltre()
    >>> p.passa("Esta vesprada els xiquets han eixit a jugar al carrer.")
    True
    >>> p.passa("Aquesta tarda els nens han sortit a jugar al carrer.")
    False
    """

    def __init__(self, min_marcadors: int = 1, min_gd: float = 0.5) -> None:
        from avlizador.grau_dialectal import gd

        self.gd = gd
        f = gd.carrega_formes_dialectals()
        # Occidental possible: tot (spaCy només en pot llevar).
        self.occidentals = f.occ_simple | f.occ_verbal
        # Oriental segur: lèxic simple que no és homògraf.
        self.or_segur = f.or_simple - set(f.homografs)
        self.min_marcadors = min_marcadors
        self.min_gd = min_gd

    def possibles_occidentals(self, text: str) -> int:
        """Cota superior dels marcadors occidentals per paraules soltes
        (si porta guionet, també cada part)."""
        n = 0
        for p in _PARAULA.findall(text.lower()):
            if p in self.occidentals:
                n += 1
            if "-" in p:
                n += sum(1 for q in p.split("-") if q in self.occidentals)
        return n

    def passa(self, text: str) -> bool:
        if self.possibles_occidentals(text) < self.min_marcadors:
            return False
        gd = self.gd
        tokens = gd.tokenize(text)
        gd.marca_noms_propis(tokens)
        occ = ori = 0
        for tok in tokens:
            if tok.surface.isspace() or tok.is_proper_noun:
                continue
            paraula = gd._paraula_per_lookup(tok.surface)
            if paraula is None:
                continue
            baix = paraula.lower()
            if baix in self.occidentals:
                occ += 1
            elif baix in self.or_segur:
                ori += 1
        # GD exacte = occ' / (occ' + ori') amb occ' <= occ i ori' >= ori.
        return occ >= self.min_marcadors and occ > 0 and occ / (occ + ori) > self.min_gd


# --------------------------------------------------------------------------
# Pas 1: extreu
# --------------------------------------------------------------------------

_PRE: Prefiltre | None = None


def _inicia_extreu(min_marcadors: int, min_gd: float) -> None:
    global _PRE
    _PRE = Prefiltre(min_marcadors, min_gd)


def _extreu_lot(lot: list[tuple[dict, dict, str]]) -> list[tuple[dict, dict, int, list]]:
    """La part cara d'`extreu` (frases vàlides + prefiltre) per a un lot de
    paràgrafs, en un procés treballador. Torna, per paràgraf, quantes
    frases té i, per a cada frase vàlida, (número, text, clau, passa el
    tall de paraules, passa el prefiltre). Les repetides les decidix el
    procés principal, en ordre: l'eixida és la mateixa que en un procés."""
    eixida = []
    for doc, par, text in lot:
        trossos = _SEPARA.split(text)
        valides = []
        for i, frase in enumerate(trossos, 1):
            frase = frase.strip()
            if not frase or not frase_valida(frase):
                continue
            tall = _PRE.possibles_occidentals(frase) >= _PRE.min_marcadors
            valides.append((i, frase, clau_repetida(frase), tall, tall and _PRE.passa(frase)))
        eixida.append((doc, par, len(trossos), valides))
    return eixida


def extreu(args: argparse.Namespace) -> None:
    est: Counter = Counter()
    vistes: set[bytes] = set()
    dominis: Counter = Counter()
    limit = args.limit_mb * 1_000_000 if args.limit_mb else None
    t0 = time.time()

    def escriu(resultats, out) -> None:
        for doc, par, n_frases, valides in resultats:
            est["frases"] += n_frases
            for i, frase, clau, tall, passa in valides:
                est["frases_valides"] += 1
                if clau in vistes:
                    est["repetides"] += 1
                    continue
                if not tall:
                    continue
                est["passen_tall_paraules"] += 1
                if not passa:
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

    # El procés principal llig el XML (~5 % del temps) i escriu en ordre;
    # els treballadors fan el prefiltre (~95 %).
    with mp.Pool(args.processos, initializer=_inicia_extreu, initargs=(args.min_marcadors, args.min_gd)) as pool, \
            open(CANDIDATES, "w", encoding="utf-8") as out:
        lot: list = []
        pendents: list = []
        for doc, par, text in paragrafs(XML, limit):
            est["paragrafs"] += 1
            if paragraf_bo(par, args.lm_min):
                est["paragrafs_bons"] += 1
                lot.append(({k: doc[k] for k in ("id", "domain", "url") if k in doc},
                            {k: par[k] for k in ("id", "lm_score") if k in par}, text))
                if len(lot) >= 2000:
                    pendents.append(pool.apply_async(_extreu_lot, (lot,)))
                    lot = []
                    while len(pendents) > args.processos * 3:
                        escriu(pendents.pop(0).get(), out)
            if est["paragrafs"] % 500_000 == 0:
                print(f"  {est['paragrafs']:,} paràgrafs, {est['candidates']:,} candidates, "
                      f"{time.time() - t0:,.0f} s", flush=True)
        if lot:
            pendents.append(pool.apply_async(_extreu_lot, (lot,)))
        for r in pendents:
            escriu(r.get(), out)
    est["segons"] = round(time.time() - t0)
    resum = {"lm_min": args.lm_min, "min_gd": args.min_gd, "min_marcadors": args.min_marcadors,
             "limit_mb": args.limit_mb, **est, "dominis_amb_mes_candidates": dominis.most_common(30)}
    (DIR_VAL / "estadistiques_extreu.json").write_text(json.dumps(resum, ensure_ascii=False, indent=2),
                                                       encoding="utf-8")
    print(json.dumps({k: v for k, v in resum.items() if k != "dominis_amb_mes_candidates"},
                     ensure_ascii=False, indent=2))


# --------------------------------------------------------------------------
# Pas 2: gd
# --------------------------------------------------------------------------

_MIN_GD = 0.5
_MIN_MARCADORS = 1
_FORMES = None
_NECESSITA_SPACY: frozenset[str] = frozenset()


def _inicia_treballador(min_gd: float, min_marcadors: int) -> None:
    global _MIN_GD, _MIN_MARCADORS, _FORMES, _NECESSITA_SPACY
    from avlizador.grau_dialectal import gd
    from avlizador.traductor_cat_val.rules import pos_tagger

    _MIN_GD, _MIN_MARCADORS = min_gd, min_marcadors
    _FORMES = gd.carrega_formes_dialectals()
    # spaCy només canvia el resultat de `_classifica_token` en les formes
    # verbals i els homògrafs; la resta de paraules no el miren.
    _NECESSITA_SPACY = frozenset(_FORMES.occ_verbal | _FORMES.or_verbal | set(_FORMES.homografs))
    pos_tagger._carrega_spacy()


class _DocsPrecalculats:
    """Fa de `nlp` per a `pos_tagger.etiqueta`: torna el Doc ja calculat
    per `nlp.pipe` (si no hi és, el calcula com sempre)."""

    def __init__(self, nlp, docs: dict) -> None:
        self.nlp, self.docs = nlp, docs

    def __call__(self, text: str):
        doc = self.docs.get(text)
        return doc if doc is not None else self.nlp(text)


def _gd_lot(linies: list[str]) -> list[str | None]:
    """El mateix que `calcula_gd(text)` per a cada línia (mateixos
    marcadors i GD; comprovat en 10.000 candidates, 10/11/2026), però
    ~3 vegades més ràpid: (1) spaCy només per a les frases amb alguna
    paraula que el necessita (~80 %) i (2) per lots amb `nlp.pipe` en
    compte d'una crida per frase."""
    from avlizador.grau_dialectal import gd
    from avlizador.traductor_cat_val.rules import marca_noms_propis, pos_tagger, tokenize

    regs, toks_l, pendents = [], [], []
    for linia in linies:
        r = json.loads(linia)
        toks = tokenize(r["text"])
        marca_noms_propis(toks)
        cal = False
        for tok in toks:
            if tok.surface.isspace() or tok.is_proper_noun:
                continue
            p = gd._paraula_per_lookup(tok.surface)
            if p is not None and p.lower() in _NECESSITA_SPACY:
                cal = True
                break
        regs.append(r)
        toks_l.append((toks, cal))
        if cal:  # el mateix text que construïx `pos_tagger.etiqueta`
            pendents.append("".join(t.surface for t in toks).replace("ʼ", "’"))

    nlp = pos_tagger._carrega_spacy()
    if nlp is not None and pendents:
        pos_tagger._NLP = _DocsPrecalculats(nlp, dict(zip(pendents, nlp.pipe(pendents, batch_size=256))))
    try:
        eixida = []
        for r, (toks, cal) in zip(regs, toks_l):
            if cal:
                pos_tagger.etiqueta(toks)
            occ, ori, total = [], [], 0
            for tok in toks:  # el bucle de `calcula_gd`
                if tok.surface.isspace():
                    continue
                p = gd._paraula_per_lookup(tok.surface)
                if p is None:
                    continue
                total += 1
                classe = gd._classifica_token(tok, _FORMES)
                if classe == "occ":
                    occ.append(p.lower())
                elif classe == "or":
                    ori.append(p.lower())
            g = gd._gd(len(occ), len(ori))
            if g is None or g <= _MIN_GD or len(occ) + len(ori) < _MIN_MARCADORS:
                eixida.append(None)
                continue
            r.update(gd=g, occ=len(occ), ori=len(ori), marcadors_occidentals=occ,
                     marcadors_orientals=ori, total_paraules=total)
            eixida.append(json.dumps(r, ensure_ascii=False))
        return eixida
    finally:
        pos_tagger._NLP = nlp


def gd(args: argparse.Namespace) -> None:
    progres = json.loads(PROGRES_GD.read_text()) if PROGRES_GD.exists() and not args.reinicia else {}
    if progres and (progres.get("min_gd"), progres.get("min_marcadors")) != (args.min_gd, args.min_marcadors):
        sys.exit("El progrés guardat és amb uns altres --min-gd/--min-marcadors; usa els mateixos o --reinicia.")
    fetes = progres.get("linies", 0)
    if fetes and VALENCIA.exists():
        os.truncate(VALENCIA, progres["mida"])
    else:
        fetes = 0
        VALENCIA.write_text("", encoding="utf-8")
    seleccionades = progres.get("valencianes", 0) if fetes else 0
    t0 = time.time()
    with mp.Pool(args.processos, initializer=_inicia_treballador, initargs=(args.min_gd, args.min_marcadors)) as pool, \
            open(CANDIDATES, encoding="utf-8") as f, open(VALENCIA, "a", encoding="utf-8") as out:
        for _ in range(fetes):
            next(f)
        linies = fetes
        while True:
            lot = [l for _, l in zip(range(args.lot), f)]
            if not lot:
                break
            trossos = [lot[i:i + 500] for i in range(0, len(lot), 500)]
            for resultats in pool.imap(_gd_lot, trossos):
                for res in resultats:
                    if res is not None:
                        out.write(res + "\n")
                        seleccionades += 1
            out.flush()
            linies += len(lot)
            PROGRES_GD.write_text(json.dumps({"linies": linies, "mida": out.tell(), "valencianes": seleccionades,
                                              "min_gd": args.min_gd, "min_marcadors": args.min_marcadors}))
            print(f"  {linies:,} candidates, {seleccionades:,} valencianes, {time.time() - t0:,.0f} s", flush=True)
    resum = {"min_gd": args.min_gd, "min_marcadors": args.min_marcadors, "candidates_llegides": linies,
             "valencianes": seleccionades, "segons_esta_execucio": round(time.time() - t0)}
    (DIR_VAL / "estadistiques_gd.json").write_text(json.dumps(resum, indent=2), encoding="utf-8")
    print(json.dumps(resum, indent=2))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="pas", required=True)
    for nom, ajuda in (("extreu", "pas 1: paràgrafs bons -> frases -> prefiltre de GD (sense spaCy)"),
                       ("gd", "pas 2: GD exacte amb spaCy, es queden les de GD > --min-gd")):
        s = sub.add_parser(nom, help=ajuda)
        s.add_argument("--min-gd", type=float, default=0.5, help="GD estrictament major que (0,5)")
        s.add_argument("--min-marcadors", type=int, default=1, help="marcadors mínims per frase (1)")
        if nom == "extreu":
            s.add_argument("--lm-min", type=float, default=0.7, help="fluïdesa mínima del paràgraf (0,7)")
            s.add_argument("--limit-mb", type=int, default=0, help="llegir només els primers N MB (proves)")
            s.add_argument("--processos", type=int, default=max(1, mp.cpu_count() - 2),
                           help="processos per al prefiltre (el principal llig el XML)")
        else:
            s.add_argument("--processos", type=int, default=max(1, mp.cpu_count() - 2))
            s.add_argument("--lot", type=int, default=20_000, help="candidates per lot (es guarda el progrés)")
            s.add_argument("--reinicia", action="store_true", help="començar de zero")
    args = p.parse_args(argv)
    DIR_VAL.mkdir(parents=True, exist_ok=True)
    extreu(args) if args.pas == "extreu" else gd(args)


if __name__ == "__main__":
    main()
