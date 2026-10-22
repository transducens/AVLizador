#!/usr/bin/env python3
"""
construeix_boe_dialectal.py -- Construïx els benchmarks del BOE per al
traductor a partir del BOE alineat català/valencià (21/10/2026): la mostra
general de 2.000 línies i els dos benchmarks "dialectals". Tot es guarda a
`dades/boe/benchmarks/` (fora de git), on hi ha un README amb l'ús.

PER QUÈ: la versió valenciana del BOE és una traducció independent que
reformula molt ("Pel que fa a" -> "Quant a", present -> futur, frases
reordenades). Mesurat sobre una mostra de 2.000 parells: el 56,5% són
reformulacions, i ahí el motor encerta l'1% de frases -- no perquè falle
en dialecte, sinó perquè no és un problema dialectal. Estos benchmarks
separen el soroll d'estil del que volem mesurar.

Tres eixides (a `dades/boe/benchmarks/`):

0. `benchmark_boe_mostra_2000.json` -- 2.000 línies a l'atzar (llavor 21)
   de 40 a 300 caràcters i ràtio de longitud de 0,85 a 1,15, sense cap
   altre filtre. És la mostra usada des del 21/10/2026 (abans es generava
   amb un script solt; ací es reprodueix idèntica).

1. `benchmark_boe_dialectal_ampli.json` -- parells IDÈNTICS o amb NOMÉS
   SUBSTITUCIONS paraula per paraula (alineació 1:1, sense insercions,
   eliminacions ni reordre; s'admet la "a" de "per a" + infinitiu). No
   jutja cada substitució: hi ha soroll d'estil, pero és on apareixen els
   buits que encara no coneixem. Criteri purament estructural, sense
   diccionari.

2. `benchmark_boe_dialectal_estricte.json` -- parells amb almenys una
   diferència on TOTES les diferències són dialectals segures:
     (a) el parell català/valencià és als diccionaris del traductor
         (`lexic_general.json`, que inclou possessius, demostratius i
         numerals, i `conjugacions_dialectals.json`). Fins al 22/10/2026
         també es carregava `demostratius_avl.json` (retirat), que
         admetia els creuaments "aquest"/"eixe" i "aqueix"/"este": els
         benchmarks del 21/10/2026 es van construir amb ell, i
         regenerar-los ara deixaria fora els parells que només
         s'explicaven per eixos creuaments;
     (b) spaCy dona el MATEIX LEMA i els MATEIXOS TRETS (temps, mode,
         persona, nombre, forma verbal; el gènere no, per "dues"/"dos") als
         dos costats i la forma canvia ("serveix"/"servix", que el proveïdor
         no llista). Sense els trets, "pot"/"podrà" (estil) passava com a
         dialectal. El prefix elidit i l'enclític han de ser iguals
         ("acords"/"d'acords" queda fora);
     (e) incoatius: la mateixa transformació de `cat_val/incoatius.py`
         ("adquireix"/"adquirix", on spaCy dona lemes diferents);
     (c) només canvia l'accent obert/tancat ("entès"/"entés", com a
         `accentuacio.py`);
     (d) la "a" de "per a" + infinitiu (BOE oficial: 97%).
   Qualsevol altra diferència (majúscules, temps verbal, paraula sense
   classificar) deixa el parell fora. ATENCIÓ: (a) usa el diccionari, així
   que este benchmark mesura el que el motor HAURIA de saber (regressions),
   no servix per a trobar buits nous -- per a això, l'ampli.

De cada conjunt es guarda el sencer i una mostra aleatòria de 2.000 (llavor
fixa) per a execucions ràpides. Ús, des de l'arrel del repo:

    python pipeline/05_corpus_boe/construeix_boe_dialectal.py
"""

from __future__ import annotations

import collections
import json
import random
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

ARREL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ARREL))

from traductor.rules import separa_prefix_elidit, separa_sufix_elidit  # noqa: E402
from traductor.rules.cat_val.incoatius import carrega_infinitius_ir, converteix_incoatiu  # noqa: E402

BOE = ARREL / "dades" / "boe"
CAT = BOE / "catala" / "corpus_entrenamiento.catala.txt"
VAL = BOE / "valencia" / "corpus_entrenamiento.valencia.txt"
DADES = BOE / "benchmarks"
DATA = ARREL / "traductor" / "data"
TOK = re.compile(r"[\wàèéíòóúïüç·'-]+|[^\w\s]", re.UNICODE)
MOSTRA = 2000
LLAVOR = 21


def normalitza(text: str) -> str:
    return text.replace("’", "'").replace("‘", "'").strip()


def tokens(text: str) -> list[str]:
    return TOK.findall(normalitza(text))


def parts(paraula: str) -> tuple[str, str, str]:
    """(prefix elidit, nucli, enclític), en minúscules."""
    p, pre, suf = paraula.lower(), "", ""
    sr = separa_sufix_elidit(p)
    if sr:
        p, suf = sr
    pr = separa_prefix_elidit(p)
    if pr:
        pre, p = pr
    return pre, p, suf


def nucli(paraula: str) -> str:
    """La paraula sense prefix elidit ni pronom enclític, en minúscules."""
    return parts(paraula)[1]


def mateixos_clitics(x: str, y: str) -> bool:
    """Els dos costats porten el mateix prefix elidit i el mateix enclític:
    "acords"/"d'acords" o "s'ha"/"ha" són canvis d'estructura, no de
    dialecte."""
    px, _, sx = parts(x)
    py, _, sy = parts(y)
    return px == py and sx == sy


TRETS = ("Tense", "Mood", "Person", "Number", "VerbForm")


def nomes_accent(x: str, y: str) -> bool:
    """Mateixa paraula llevat d'un accent obert/tancat (è/é, ò/ó)."""
    x, y = x.lower(), y.lower()
    return x != y and len(x) == len(y) and all(
        a == b or {a, b} in ({"è", "é"}, {"ò", "ó"}) for a, b in zip(x, y))


def carrega_parells_diccionari() -> set[tuple[str, str]]:
    parells: set[tuple[str, str]] = set()
    for e in json.loads((DATA / "lexic_general.json").read_text(encoding="utf-8")):
        c, v = (e.get("catalan") or "").strip().lower(), (e.get("valenciano") or "").strip().lower()
        if c and v and " " not in c and " " not in v:
            parells.add((c, v))
    for e in json.loads((DATA / "conjugacions_dialectals.json").read_text(encoding="utf-8"))["entradas"]:
        c, v = (e.get("catalan") or "").strip().lower(), (e.get("valenciano") or "").strip().lower()
        if c and v and " " not in c and " " not in v:
            parells.add((c, v))
    return parells


def ops_diferents(a: list[str], b: list[str]):
    al = [t.lower() for t in a]
    bl = [t.lower() for t in b]
    return [o for o in SequenceMatcher(None, al, bl, autojunk=False).get_opcodes() if o[0] != "equal"]


def es_estructural(a: list[str], b: list[str]) -> bool:
    """Només substitucions 1:1 (blocs de com a molt 2 paraules) o la "a"
    de "per a" inserida darrere de "per"."""
    for op, i1, i2, j1, j2 in ops_diferents(a, b):
        if op == "replace" and (i2 - i1) == (j2 - j1) <= 2:
            continue
        if op == "insert" and [t.lower() for t in b[j1:j2]] == ["a"] and i1 > 0 and a[i1 - 1].lower() == "per":
            continue
        return False
    return True


def main() -> None:
    catala = CAT.read_text(encoding="utf-8").split("\n")
    valencia = VAL.read_text(encoding="utf-8").split("\n")
    n = min(len(catala), len(valencia))
    parells_dic = carrega_parells_diccionari()
    DADES.mkdir(parents=True, exist_ok=True)

    # 0. Mostra general (mateix criteri i llavor que la del 21/10/2026)
    idx = [i for i in range(n) if 40 <= len(catala[i]) <= 300
           and 0.85 <= len(valencia[i]) / max(len(catala[i]), 1) <= 1.15]
    mostra_general = [{"id": f"boe_{i}", "oriental": catala[i], "occidental": valencia[i]}
                      for i in random.Random(LLAVOR).sample(idx, MOSTRA)]
    (DADES / "benchmark_boe_mostra_2000.json").write_text(
        json.dumps(mostra_general, ensure_ascii=False, indent=1), encoding="utf-8")

    ampli = []
    pendents_spacy = []  # (index, [(cat, val), ...]) diferències que el diccionari no explica
    estricte_idx: set[int] = set()
    estad = collections.Counter()
    for i in range(n):
        c, v = normalitza(catala[i]), normalitza(valencia[i])
        if not (30 <= len(c) <= 300) or not (0.85 <= len(v) / max(len(c), 1) <= 1.15):
            estad["descartat per longitud"] += 1
            continue
        a, b = tokens(c), tokens(v)
        if not es_estructural(a, b):
            estad["reformulat"] += 1
            continue
        ops = ops_diferents(a, b)
        reg = {"id": f"boe_{i}", "oriental": c, "occidental": v}
        ampli.append(reg)
        if not ops:
            estad["idèntic"] += 1
            continue
        if any(x != y and x.lower() == y.lower() for x, y in zip(a, b)) and len(a) == len(b):
            estad["substitucions, amb diferència de majúscules"] += 1
            continue
        sense_explicar = []
        for op, i1, i2, j1, j2 in ops:
            if op == "insert":
                continue  # la "a" de "per a" (ja validada a es_estructural)
            for x, y in zip(a[i1:i2], b[j1:j2]):
                if ((x.lower(), y.lower()) in parells_dic or (nucli(x), nucli(y)) in parells_dic
                        or nomes_accent(x, y)):
                    continue
                sense_explicar.append((x, y))
        if not sense_explicar:
            estricte_idx.add(i)
            estad["substitucions, totes al diccionari"] += 1
        else:
            pendents_spacy.append((i, sense_explicar))

    # (b) mateix lema segons spaCy, només per a les diferències que el diccionari no explica
    import spacy

    nlp = spacy.load("ca_core_news_sm", exclude=["parser", "ner"])

    def lema(doc, paraula: str):
        """(lema, trets) del primer token que és la paraula o el seu nucli."""
        buscada = nucli(paraula)
        for t in doc:
            if t.text.lower() in (paraula.lower(), buscada):
                return t.lemma_.lower(), tuple(tuple(t.morph.get(k)) for k in TRETS)
        return None

    infinitius_ir = carrega_infinitius_ir(DATA / "conjugacions_dialectals.json")

    def incoatiu(dc, x: str, y: str) -> bool:
        """(e) la mateixa transformació que aplica `cat_val/incoatius.py`:
        lema català validat contra els infinitius en "-ir" dels JSON."""
        for t in dc:
            if t.text.lower() == nucli(x) and t.lemma_.lower() in infinitius_ir:
                return converteix_incoatiu(nucli(x), t.lemma_.lower()) == nucli(y)
        return False

    idxs = [i for i, _ in pendents_spacy]
    docs_c = nlp.pipe((normalitza(catala[i]) for i in idxs), batch_size=256)
    docs_v = nlp.pipe((normalitza(valencia[i]) for i in idxs), batch_size=256)
    exemples = collections.defaultdict(list)
    for (i, difs), dc, dv in zip(pendents_spacy, docs_c, docs_v):
        tot_lema = True
        for x, y in difs:
            if not mateixos_clitics(x, y):
                ok = False
            elif incoatiu(dc, x, y):
                ok = True
            else:
                lc, lv = lema(dc, x), lema(dv, y)
                ok = bool(lc and lv and lc == lv)  # mateix lema i mateixos trets
            if not ok:
                tot_lema = False
                if len(exemples["fora: diferència sense classificar"]) < 15:
                    exemples["fora: diferència sense classificar"].append(f"{x} -> {y}")
                break
        if tot_lema:
            estricte_idx.add(i)
            estad["substitucions, explicades amb el mateix lema i trets (spaCy)"] += 1
            if len(exemples["dins: mateix lema"]) < 15:
                exemples["dins: mateix lema"].append(", ".join(f"{x} -> {y}" for x, y in difs))
        else:
            estad["substitucions, alguna sense classificar (fora de l'estricte)"] += 1

    estricte = [r for r in ampli if int(r["id"].split("_")[1]) in estricte_idx]
    rnd = random.Random(LLAVOR)
    for nom, conjunt in (("ampli", ampli), ("estricte", estricte)):
        (DADES / f"benchmark_boe_dialectal_{nom}_complet.json").write_text(
            json.dumps(conjunt, ensure_ascii=False, indent=1), encoding="utf-8")
        mostra = rnd.sample(conjunt, min(MOSTRA, len(conjunt)))
        (DADES / f"benchmark_boe_dialectal_{nom}.json").write_text(
            json.dumps(mostra, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"Parells del BOE: {n}")
    for k, val in estad.most_common():
        print(f"  {k:62} {val:7}")
    print(f"\nBOE dialectal AMPLI: {len(ampli)} parells (mostra de {min(MOSTRA, len(ampli))})")
    print(f"BOE dialectal ESTRICTE: {len(estricte)} parells (mostra de {min(MOSTRA, len(estricte))})")
    for k, ex in exemples.items():
        print(f"\n{k}:")
        for e in ex:
            print(f"   {e}")


if __name__ == "__main__":
    main()
