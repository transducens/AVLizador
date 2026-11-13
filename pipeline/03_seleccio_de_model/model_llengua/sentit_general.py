"""
sentit_general.py -- Entrena el classificador de sentit GENERAL (13/11/2026,
decisió de l'usuari): un Naive Bayes per a cada paraula ambigua del lèxic,
no només per a "cop" (`sentit_cop.py`). El fa servir el sistema KenLM com a
desempat: si KenLM guanya per menys de 2 punts, decidix el classificador
de la paraula, si en té (`model_llengua.sentit.ClassificadorSentit`).

Sense cap llista de paraules: els punts ixen del lèxic (`carrega_punts`),
com en el sistema.
- Cada punt té dos candidats: classe "0" = el primer, "1" = el segon (una
  col·lisió: "colp" / "vegada"; un homògraf: la traducció i la paraula
  catalana, "faltes" / "manques").
- Grups: els punts amb els mateixos `lemas` en el lèxic (singular i plural:
  "gandula" i "gandules") compartixen classificador i dades; sense `lemas`
  ("cop", "cops"), un per punt.
- Dades: frases valencianes reals (MaCoCu net i DOGV, com `sentit_cop.py`;
  sense l'AVL, que no es pot redistribuir) on apareix un candidat. La
  paraula es canvia per un buit i l'etiqueta és la classe. Fora: les
  frases amb candidats de les dues classes i les semblants a un benchmark.
- Si una classe té menys de `--minim` frases, el grup no s'entrena (no hi
  ha prou dades: "panotxa" 4, "recuita" 0) i el sistema fa com abans.
- Mateixos trets que el de "cop": lemes d'spaCy al voltant, les paraules que
  concorden (amb gènere) només amb la categoria.
- Dev: el 10 % de les frases (per hash), apartades; encert per classe. Un
  grup només entra en el sistema si el seu encert equilibrat (la mitjana de
  les dues classes) és com a mínim `--min-dev` (0,7, decisió de l'usuari,
  13/11/2026): ha de demostrar que acerta amb frases reals que no ha vist.
  Els que no hi arriben ixen en `sentit_entrenament.json` ("descartats") i
  fan com abans (si KenLM dubta, la paraula catalana).

Ús (des de l'arrel del repositori):
    python pipeline/03_seleccio_de_model/model_llengua/sentit_general.py recompte
    python pipeline/03_seleccio_de_model/model_llengua/sentit_general.py entrena
Eixida: `dades/macocu/kenlm/sentit/sentit.json` (el classificador; per a
usar-lo, al costat del model KenLM, en `AVLIZADOR_KENLM_DIR`) i
`sentit_entrenament.json` (dades, dev i paraules més informatives).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from sentit_cop import FONTS, FONTS_PER_DEFECTE, es_dev, frases_font  # noqa: E402

ARREL = AQUI.parents[2]
EIXIDA = ARREL / "dades" / "macocu" / "kenlm" / "sentit"


def grups_de_punts() -> dict[str, dict]:
    """`{grup: {"punts": {forma: [c0, c1]}, "classe": {candidat: "0"|"1"}}}`
    a partir del lèxic.

    >>> g = grups_de_punts()
    >>> g["punt:cop"]["punts"], g["punt:cop"]["classe"]["vegada"]
    ({'cop': ['colp', 'vegada']}, '1')
    >>> sorted(next(x for x in g.values() if "gandula" in x["punts"])["punts"])
    ['gandula', 'gandules']
    """
    from avlizador.traductor_cat_val.model_llengua.punts import carrega_punts
    from avlizador.traductor_cat_val.rules import LEXIC_GENERAL_PATH

    lemas = {}
    for e in json.loads(Path(LEXIC_GENERAL_PATH).read_text(encoding="utf-8")):
        forma = (e.get("forma_problematica") or "").strip().lower()
        if forma and e.get("lemas") and forma == (e.get("catalan") or "").strip().lower():
            lemas[forma] = "lemas:" + "|".join(sorted(e["lemas"]))
    grups: dict[str, dict] = {}
    for forma, d in sorted(carrega_punts().items()):
        cands = [c.lower() for c in d["candidats"]]
        if len(cands) != 2:
            continue
        g = grups.setdefault(lemas.get(forma, f"punt:{forma}"), {"punts": {}, "classe": {}})
        g["punts"][forma] = cands
        for i, c in enumerate(cands):
            if g["classe"].get(c, str(i)) != str(i):
                raise ValueError(f"{c}: classe distinta en el grup de {forma}")
            g["classe"][c] = str(i)
    return grups


def recull(grups: dict, fonts=FONTS_PER_DEFECTE, maxim: int = 30000, llavor: int = 13):
    """Exemples `{grup: {classe: [(tokens, posicions)]}}` i recomptes."""
    sys.path.insert(0, str(ARREL / "pipeline" / "08_traduccio_corpus" / "macocu" / "kenlm"))
    from termes_ambigus import Avaluacio

    aval = Avaluacio()
    per_paraula: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for g, d in grups.items():
        for c, classe in d["classe"].items():
            per_paraula[c].append((g, classe))
    exemples: dict = {g: {"0": [], "1": []} for g in grups}
    comptes: Counter = Counter()
    for _font, toks in frases_font(fonts):
        trobades: dict = defaultdict(lambda: defaultdict(list))
        for i, t in enumerate(toks):
            for g, classe in per_paraula.get(t, ()):
                trobades[g][classe].append(i)
        if not trobades:
            continue
        if aval.semblant(" ".join(toks)):
            comptes["semblant_avaluacio"] += 1
            continue
        for g, classes in trobades.items():
            if len(classes) > 1:  # candidats de les dues classes en la mateixa frase
                comptes[f"{g}:les_dues"] += 1
                continue
            classe, pos = next(iter(classes.items()))
            exemples[g][classe].append((toks, pos))
    rnd = random.Random(llavor)
    total = {}
    for g in grups:
        total[g] = {c: len(v) for c, v in exemples[g].items()}
        for c, v in exemples[g].items():
            rnd.shuffle(v)
            del v[maxim:]
    return exemples, total, dict(comptes)


def recompte(args) -> None:
    grups = grups_de_punts()
    _exemples, total, comptes = recull(grups, args.fonts, maxim=0)
    for g, d in grups.items():
        t = total[g]
        estat = "SÍ" if min(t.values()) >= args.minim else "no (poques dades)"
        noms = {c: d["punts"][f][int(c)] for f in d["punts"] for c in ("0", "1")}
        print(f"{', '.join(d['punts']):24s} {noms['0']:>10s} {t['0']:7d} | {noms['1']:<10s} {t['1']:7d}  -> {estat}")
    print("altres:", comptes)


def entrena(args) -> None:
    from avlizador.traductor_cat_val.model_llengua.sentit import BUIT, Lematitzador, NaiveBayes, trets

    grups = grups_de_punts()
    exemples, total, comptes = recull(grups, args.fonts, args.maxim, args.llavor)
    lem = Lematitzador()
    eixida = {"versio": 2, "creat": datetime.now().isoformat(timespec="seconds"), "finestra": args.finestra,
              "minim": args.minim, "min_dev": args.min_dev, "fonts": list(args.fonts), "grups": {}}
    informe = {"args": vars(args), "comptes": comptes, "grups": {}, "descartats": {}, "sense_dades": {}}
    for g, d in grups.items():
        if min(total[g].values()) < args.minim:
            informe["sense_dades"][g] = {"punts": d["punts"], "frases": total[g]}
            print(f"{g}: sense classificador (frases {total[g]})", flush=True)
            continue
        nb = NaiveBayes(args.alpha, ("0", "1"))
        apartats = []  # (trets, classe) del dev: s'avaluen quan el model ja està entrenat
        llista = [(c, toks, pos) for c in ("0", "1") for toks, pos in exemples[g][c]]
        lemes = lem.lemes([[BUIT if i in pos else t for i, t in enumerate(toks)] for _c, toks, pos in llista])
        for (classe, toks, pos), l in zip(llista, lemes):
            for i in pos:
                l2 = list(l)
                l2[i] = BUIT
                f = trets(l2, i, args.finestra)
                if es_dev(toks):
                    apartats.append((f, classe))
                else:
                    nb.afig(f, classe)
        dev = {"0": [0, 0], "1": [0, 0]}  # [encerts, total]
        for f, classe in apartats:
            lo = nb.logodds(f)
            dev[classe][1] += 1
            dev[classe][0] += lo != 0 and (lo > 0) == (classe == "0")
        encert = {c: f"{dev[c][0]}/{dev[c][1]}" for c in ("0", "1")}
        bal = sum(dev[c][0] / max(1, dev[c][1]) for c in ("0", "1")) / 2
        fila = {"punts": d["punts"], "frases": total[g], "dev": encert, "balancejat": round(bal, 3),
                "informatius": nb.mes_informatius(15)}
        if bal < args.min_dev:  # no ha demostrat que acerte: no entra en el sistema
            informe["descartats"][g] = fila
            print(f"{g}: DESCARTAT, dev {encert} (balancejat {bal:.3f} < {args.min_dev})", flush=True)
            continue
        eixida["grups"][g] = {"punts": d["punts"], "nb": nb.a_dict(args.poda)}
        informe["grups"][g] = fila
        print(f"{g}: frases {total[g]}, dev {encert} (balancejat {bal:.3f})", flush=True)
    EIXIDA.mkdir(parents=True, exist_ok=True)
    (EIXIDA / f"{args.nom}.json").write_text(json.dumps(eixida, ensure_ascii=False), encoding="utf-8")
    (EIXIDA / f"{args.nom}_entrenament.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1),
                                                       encoding="utf-8")
    print(f"-> {EIXIDA / (args.nom + '.json')} ({len(eixida['grups'])} grups)")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="ordre", required=True)
    for nom in ("recompte", "entrena"):
        x = sub.add_parser(nom)
        x.add_argument("--fonts", nargs="+", choices=FONTS, default=list(FONTS_PER_DEFECTE))
        x.add_argument("--minim", type=int, default=20, help="frases mínimes de cada classe per a entrenar un grup")
    e = sub.choices["entrena"]
    e.add_argument("--maxim", type=int, default=30000, help="frases màximes per classe (mostra a l'atzar)")
    e.add_argument("--finestra", type=int, default=8)
    e.add_argument("--alpha", type=float, default=0.5)
    e.add_argument("--poda", type=int, default=2, help="trets amb menys aparicions es lleven del fitxer")
    e.add_argument("--min-dev", type=float, default=0.7,
                   help="encert equilibrat mínim en el dev (frases apartades) perquè el grup entre en el sistema")
    e.add_argument("--llavor", type=int, default=13)
    e.add_argument("--nom", default="sentit")
    args = p.parse_args(argv)
    (recompte if args.ordre == "recompte" else entrena)(args)


if __name__ == "__main__":
    main()
