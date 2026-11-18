"""Pas 1: famílies del lèxic i reserva del 20 % per al test de circularitat.

Una FAMÍLIA agrupa les formes d'un mateix lexema perquè la reserva no
deixe passar informació ("aquest" reservat i "aquesta" a l'entrenament no
seria un test de res). S'unixen (union-find):

- les formes verbals d'un mateix infinitiu català (camp `verbo` de
  `conjugaciones_general.json`, `infinitiu_cat` de
  `verbos_diferentes_conjugados.json`);
- les entrades del lèxic amb la mateixa glossa castellana, sense plural ni
  gènere ("servicio"/"servicios", "este"/"esta"/"estos");
- les formes que comparteixen la valenciana o la catalana.

La reserva és ESTRATIFICADA per freqüència: el 20 % de les famílies de
cada estrat (sense aparicions + cinc quintils), perquè n'hi haja de
freqüents i de rares. La freqüència és la dels marcadors que el GD troba de
veres (amb spaCy) en els positius (`positius.jsonl`, que no depén de la
reserva: cal executar `prepara_positius.py` abans); sense eixe fitxer, la
del DOGV en brut, que infla els verbs homògrafs de noms ("projectes",
"mesures"). Els homògrafs (nou, deu, cop...) no es reserven: van als
negatius de tipus 3.

Eixida: `dades/metrica_sense_referencia/lexic_parells.json`.

    python prepara_lexic.py [--percentatge 0.2] [--llavor 20261118]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import random
import re
import unicodedata

import comu

DOGV_TSV = comu.DADES / "dogv_apunt" / "nova" / "dogv_documents.tsv"
FREQ_CACHE = comu.EIXIDA / "freq_dogv.json"
CONJ = comu.DADES / "lexic" / "conjugaciones_general.json"
VERBS_DIF = comu.DADES / "lexic" / "verbos_diferentes_conjugados.json"


def freq_dogv() -> collections.Counter:
    """Freqüència de cada paraula en el DOGV en brut (sense el filtre de GD,
    que faria circular la mesura). El TSV porta els salts de línia com
    `\\n` literal."""
    if FREQ_CACHE.exists():
        return collections.Counter(json.loads(FREQ_CACHE.read_text(encoding="utf-8")))
    csv.field_size_limit(10**9)
    paraula = re.compile(r"[a-zà-ÿ·]+")
    freq: collections.Counter = collections.Counter()
    with open(DOGV_TSV, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            freq.update(paraula.findall((row["text"] or "").replace("\\n", " ").lower()))
    comu.EIXIDA.mkdir(parents=True, exist_ok=True)
    FREQ_CACHE.write_text(json.dumps(freq, ensure_ascii=False), encoding="utf-8")
    return freq


def clau_glossa(espanol: str) -> str:
    """'Servicios' -> 'servici', 'esta' -> 'est', 'últimos' -> 'ultim'."""
    s = "".join(ch for ch in unicodedata.normalize("NFD", espanol.lower())
                if unicodedata.category(ch) != "Mn").strip()
    s = re.sub(r"s$", "", s)
    return re.sub(r"[aeo]$", "", s)


class UnionFind:
    def __init__(self) -> None:
        self.pare: dict[str, str] = {}

    def troba(self, x: str) -> str:
        self.pare.setdefault(x, x)
        while self.pare[x] != x:
            self.pare[x] = self.pare[self.pare[x]]
            x = self.pare[x]
        return x

    def unix(self, a: str, b: str) -> None:
        ra, rb = self.troba(a), self.troba(b)
        if ra != rb:
            self.pare[max(ra, rb)] = min(ra, rb)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--percentatge", type=float, default=0.2)
    ap.add_argument("--llavor", type=int, default=20261118)
    args = ap.parse_args()

    P = comu.parells_val_cat()
    H = comu.homografs_cat_val()
    homo_val = {f for h in H.values() for f in ([h["dialectal"]] if h["tipus"] == "homonimia" else h["candidates"])}
    homo_cat = set(H)

    uf = UnionFind()
    for v, (c, _) in P.items():
        uf.unix("val:" + v, "cat:" + c)

    for e in comu.entrades_lexic():
        v = e["valenciano"].lower()
        if v in P:
            # Sense glossa (els demostratius, E1619...): la forma valenciana
            # sense gènere ni nombre dins de la categoria ("este", "estos",
            # "estes" -> "est").
            clau = ("es:" + clau_glossa(e["espanol"]) if e.get("espanol")
                    else f"morf:{e.get('categoria')}:{clau_glossa(v)}")
            uf.unix("val:" + v, clau)
    with open(CONJ, encoding="utf-8") as f:
        for e in json.load(f):
            v = e["valenciano"].lower()
            if v in P and e.get("verbo"):
                uf.unix("val:" + v, "verb:" + e["verbo"].lower())
    with open(VERBS_DIF, encoding="utf-8") as f:
        for e in json.load(f):
            v = e["valenciano"].lower()
            # La clau és l'infinitiu CATALÀ, com el camp `verbo` de
            # `conjugaciones_general.json` ("tinga" -> "tenir"; "tindre" -> "tenir").
            if v in P and e.get("infinitiu_cat"):
                uf.unix("val:" + v, "verb:" + e["infinitiu_cat"].lower())

    freq_d = freq_dogv()
    positius = comu.EIXIDA / "positius.jsonl"
    if positius.exists():
        freq = collections.Counter()
        with open(positius, encoding="utf-8") as f:
            for linia in f:
                freq.update(forma for _, forma in json.loads(linia)["marcadors"])
        print(f"Freqüència: marcadors de {positius.name}")
    else:
        freq = freq_d
        print("Freqüència: DOGV en brut (no hi ha positius.jsonl)")
    families: dict[str, dict] = {}
    for v, (c, font) in P.items():
        arrel = uf.troba("val:" + v)
        fam = families.setdefault(arrel, {"formes_val": [], "formes_cat": [], "fonts": set(), "freq": 0,
                                           "homograf": False})
        fam["formes_val"].append(v)
        fam["formes_cat"].append(c)
        fam["fonts"].add(font)
        fam["freq"] += freq[v]
        if v in homo_val or c in homo_cat:
            fam["homograf"] = True

    # Estrats: sense dades en el DOGV + quintils de les que en tenen.
    candidates = [k for k, f in families.items() if not f["homograf"]]
    zero = sorted(k for k in candidates if families[k]["freq"] == 0)
    amb = sorted((k for k in candidates if families[k]["freq"] > 0), key=lambda k: (families[k]["freq"], k))
    estrats = {"0_sense_dades": zero}
    n = len(amb)
    for q in range(5):
        estrats[f"{q + 1}_quintil"] = amb[q * n // 5:(q + 1) * n // 5]
    rng = random.Random(args.llavor)
    reservades = set()
    for nom, ks in estrats.items():
        triades = rng.sample(ks, round(len(ks) * args.percentatge))
        reservades.update(triades)
        for k in ks:
            families[k]["estrat"] = nom
    for k, f in families.items():
        f["reservada"] = k in reservades
        f.setdefault("estrat", "homograf" if f["homograf"] else "?")
        f["fonts"] = sorted(f["fonts"])

    noms = {k: f"F{i:05d}" for i, k in enumerate(sorted(families, key=lambda k: -families[k]["freq"]))}
    parells = []
    for v, (c, font) in sorted(P.items()):
        k = uf.troba("val:" + v)
        parells.append({"val": v, "cat": c, "font": font, "familia": noms[k],
                        "reservada": families[k]["reservada"], "freq": freq[v], "freq_dogv": freq_d[v]})
    eixida = {
        "percentatge": args.percentatge,
        "llavor": args.llavor,
        "families": {noms[k]: {**f, "arrel": k} for k, f in families.items()},
        "parells": parells,
    }
    comu.EIXIDA.mkdir(parents=True, exist_ok=True)
    path = comu.EIXIDA / "lexic_parells.json"
    path.write_text(json.dumps(eixida, ensure_ascii=False, indent=1), encoding="utf-8")

    # Resum
    print(f"Parells: {len(P)}; famílies: {len(families)} "
          f"(homògrafs, fora de la reserva: {sum(f['homograf'] for f in families.values())})")
    mides = collections.Counter(len(f["formes_val"]) for f in families.values())
    print("Família més gran:", max(mides), "formes; famílies d'1 forma:", mides[1])
    tot_freq = sum(f["freq"] for f in families.values())
    res_freq = sum(f["freq"] for f in families.values() if f["reservada"])
    print(f"Reservades: {len(reservades)} famílies, {sum(len(families[k]['formes_val']) for k in reservades)} formes, "
          f"{res_freq / tot_freq:.1%} de les aparicions al DOGV")
    for nom, ks in estrats.items():
        r = [k for k in ks if k in reservades]
        print(f"  {nom}: {len(ks)} famílies, {len(r)} reservades")
    print("Reservades més freqüents:")
    for k in sorted(reservades, key=lambda k: -families[k]["freq"])[:25]:
        f = families[k]
        print(f"  {f['freq']:>7}  {', '.join(sorted(f['formes_val'])[:6])} -> {', '.join(sorted(set(f['formes_cat']))[:6])}")
    print("Famílies més grans:")
    for k in sorted(families, key=lambda k: -len(families[k]["formes_val"]))[:5]:
        f = families[k]
        print(f"  {len(f['formes_val'])} formes: {k} ({', '.join(sorted(f['formes_val'])[:8])}...)")
    print("Escrit", path)


if __name__ == "__main__":
    main()
