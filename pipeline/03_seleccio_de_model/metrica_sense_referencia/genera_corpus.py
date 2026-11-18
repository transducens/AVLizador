"""Pas 3: corpus sintètic (src, mt, score) per a entrenar la mètrica.

Entrades (en `dades/metrica_sense_referencia/`): `positius.jsonl`,
`homografs_corpus.jsonl` (de `prepara_positius.py`), `lexic_parells.json`
(de `prepara_lexic.py`) i `homografs_creats.json` (en esta carpeta).

Per cada positiu (src català, mt valencià amb GD = 1):

| tipus | mt | score |
|---|---|---|
| 0 positiu | el valencià | 0,9 |
| 1 sense traduir | el src tal qual | 0,1 |
| 2 dialecte parcial | es catalanitza el 10/30/60/100 % dels marcadors | 0,5 -> 0,2 segons la fracció real |
| 4 mescla | cada bloc diferent (difflib) del src o del mt, a l'atzar | 0,3 |

Tipus 3 (error de sentit, 0,1): homògrafs del lèxic amb la lectura
equivocada. Del corpus (el BOE/AVL diu quina lectura és: "nou" igual als dos
costats = compartida, "anou" = dialectal) i de les frases escrites a mà
(`homografs_creats.json`), que cobrixen totes les formes i lectures.

RESERVA (test de circularitat): les formes de les famílies reservades mai
apareixen com a error en el mt de l'entrenament: no es catalanitzen (tipus
2), els blocs que les porten es queden en valencià (tipus 4) i no es fa el
tipus 1 si el src en porta alguna. Sí que poden aparéixer en valencià en els
positius. Amb els positius de validació i test que en porten es fa
`test_circularitat.csv`: original, només les reservades en català i, de
control, el mateix nombre de marcadors no reservats en català.

Partició 80/10/10 per document (BOE) o per frase (AVL, frases creades).

Eixides: `train.csv`, `val.csv`, `test.csv` (columnes src, mt, score),
`test_circularitat.csv`, `*_meta.jsonl` (tipus, id i detalls de cada fila)
i `estadistiques_corpus.json`. Amb `--sense-reserva`, en `complet/`.

    python genera_corpus.py [--llavor 20261118] [--sense-reserva]
"""
from __future__ import annotations

import argparse
import collections
import csv
import difflib
import hashlib
import json
import random
import re
import sys

import comu

CREATS = comu.RAIZ / "pipeline" / "03_seleccio_de_model" / "metrica_sense_referencia" / "homografs_creats.json"
FRACCIONS = (0.1, 0.3, 0.6, 1.0)
MAX_HOMOGRAF_CORPUS = 300  # per (forma, lectura)


def particio(grup: str) -> str:
    h = int(hashlib.md5(grup.encode("utf-8")).hexdigest(), 16) % 100
    return "train" if h < 80 else "val" if h < 90 else "test"


def score_parcial(k: int, n: int) -> float:
    """0,5 amb el 10 % dels marcadors en català, 0,2 amb el 100 %."""
    f = k / n
    return round(min(0.5, max(0.2, 0.5 - 0.3 * (f - 0.1) / 0.9)), 3)


def paraules_tokens(tokens):
    """[(índex, paraula en minúscules)] dels tokens que són paraules."""
    return [(i, comu.forma_actual(t)) for i, t in enumerate(tokens) if comu.forma_actual(t)]


class Generador:
    def __init__(self, sense_reserva: bool, llavor: int) -> None:
        lex = json.loads((comu.EIXIDA / "lexic_parells.json").read_text(encoding="utf-8"))
        self.P = {p["val"]: (p["cat"], p["font"]) for p in lex["parells"]}
        reservats = [] if sense_reserva else [p for p in lex["parells"] if p["reservada"]]
        self.res_val = {p["val"] for p in reservats}
        self.res_cat = {p["cat"] for p in reservats}
        self.familia = {p["val"]: p["familia"] for p in lex["parells"]}
        self.G = comu.generes_cat()
        self.H = comu.homografs_cat_val()
        self.genere_val = {}
        for e in comu.entrades_lexic():
            if e.get("genero_val") in ("m", "f"):
                self.genere_val.setdefault(e["valenciano"].lower(), e["genero_val"])
        self.rng = random.Random(llavor)
        self.E = comu.Exclusions()
        self.files = collections.defaultdict(list)
        self.vistos = collections.defaultdict(set)
        self.stats = collections.Counter()

    # --- utilitats ---------------------------------------------------------

    def afig(self, particio_: str, tipus: str, src: str, mt: str, score: float, **meta) -> None:
        clau = (src, mt)
        # Una mescla o una substitució pot reproduir per casualitat una frase
        # d'avaluació (el BOE ampli té frases quasi iguals en moltes lleis).
        if comu.norm(mt) in self.E.frases:
            self.stats[f"{particio_}:{tipus}:igual_avaluacio"] += 1
            return
        if clau in self.vistos[particio_]:
            self.stats[f"{particio_}:{tipus}:repetida"] += 1
            return
        self.vistos[particio_].add(clau)
        self.files[particio_].append({"tipus": tipus, "src": src, "mt": mt, "score": score, **meta})
        self.stats[f"{particio_}:{tipus}"] += 1

    def reservats_src(self, x: dict) -> set[int]:
        """Índexs (de `tokenize(src)`) dels marcadors catalans del src que
        són formes reservades. Es mira en els marcadors del GD (amb spaCy),
        no en paraules soltes: "l'Estat" no és el participi "estat"."""
        return {i for i, f in x.get("marcadors_src", []) if f in self.res_cat}

    # --- tipus 0, 1, 2 i 4 -------------------------------------------------

    def positiu(self, x: dict) -> None:
        part = particio(x["doc"])
        src, mt = x["src"], x["mt"]
        marcadors = [(i, f) for i, f in x["marcadors"] if f in self.P]
        if len(marcadors) < 2:
            self.stats["positius_sense_parell"] += 1
            return
        meta = {"id": x["id"], "font": x["font"], "n_marcadors": len(marcadors)}
        self.afig(part, "0_positiu", src, mt, 0.9, **meta)
        res_src = self.reservats_src(x)
        if not res_src:
            self.afig(part, "1_sense_traduir", src, src, 0.1, **meta)
        else:
            self.stats[f"{part}:1_omes_per_reserva"] += 1

        elegibles = [(i, f) for i, f in marcadors if f not in self.res_val]
        if elegibles:
            fraccio = self.rng.choice(FRACCIONS)
            k = max(1, round(fraccio * len(elegibles)))
            triats = self.rng.sample(elegibles, k)
            mt2 = comu.catalanitza(mt, [i for i, _ in triats], self.P, self.G)
            if mt2 != mt:
                self.afig(part, "2_dialecte_parcial", src, mt2, score_parcial(k, len(marcadors)),
                          **meta, fraccio=fraccio, canviats=sorted(f for _, f in triats))

        mt4 = self.mescla(src, mt, res_src)
        if mt4 is not None:
            self.afig(part, "4_mescla", src, mt4, 0.3, **meta)

    def mescla(self, src: str, mt: str, res_src: set[int]) -> str | None:
        """Cada bloc diferent, del src o del mt a l'atzar (almenys un de
        cada). Els blocs del src amb una forma reservada (`res_src`, índexs
        de token) es queden en valencià."""
        ts = [t.surface for t in comu.tokenize(src)]
        tm = [t.surface for t in comu.tokenize(mt)]
        ops = difflib.SequenceMatcher(None, ts, tm, autojunk=False).get_opcodes()
        diferents = [k for k, op in enumerate(ops) if op[0] != "equal"]
        if len(diferents) < 2:
            return None
        forcats = {k for k in diferents if any(ops[k][1] <= i < ops[k][2] for i in res_src)}
        tria = {k: "mt" if k in forcats else self.rng.choice(("src", "mt")) for k in diferents}
        lliures = [k for k in diferents if k not in forcats]
        if all(tria[k] == "mt" for k in diferents) and lliures:
            tria[self.rng.choice(lliures)] = "src"
        if all(tria[k] == "src" for k in diferents):
            tria[self.rng.choice(diferents)] = "mt"
        eixida = []
        for k, (tag, a1, a2, b1, b2) in enumerate(ops):
            if tag == "equal" or tria[k] == "mt":
                eixida.extend(tm[b1:b2])
            else:
                eixida.extend(ts[a1:a2])
        res = comu.contrau("".join(eixida))
        return None if res in (src, mt) else res

    # --- tipus 3 -----------------------------------------------------------

    def error_homograf(self, mt: str, i: int, forma_src: str, forma_mt: str) -> tuple[str, str] | None:
        """(lectura, mt amb la lectura equivocada) o `None`."""
        h = self.H[forma_src]
        tokens = comu.tokenize(mt)
        if h["tipus"] == "homonimia":
            d = h["dialectal"]
            if forma_mt == forma_src:
                lectura, nova, genere, canvi = "compartida", d, None, False
            elif forma_mt == d:
                tots, canvis = self.G
                lectura, nova, genere, canvi = "dialectal", forma_src, tots.get(d), d in canvis
            else:
                return None
        else:
            if forma_mt not in h["candidates"]:
                return None
            nova = next(c for c in h["candidates"] if c != forma_mt)
            genere = self.genere_val.get(nova)
            lectura, canvi = forma_mt, genere is not None and genere != self.genere_val.get(forma_mt)
        comu.substituix(tokens, i, nova, genere, canvi)
        return lectura, comu.contrau(comu.detokenize(tokens))

    def homografs_corpus(self, files: list[dict]) -> None:
        per_cas = collections.defaultdict(list)
        for x in files:
            ts, tm = comu.tokenize(x["src"]), comu.tokenize(x["mt"])
            ws, wm = paraules_tokens(ts), paraules_tokens(tm)
            ops = difflib.SequenceMatcher(None, [w for _, w in ws], [w for _, w in wm], autojunk=False).get_opcodes()
            for tag, a1, a2, b1, b2 in ops:
                if tag not in ("equal", "replace") or (a2 - a1) != (b2 - b1):
                    continue
                for k in range(a2 - a1):
                    forma_src = ws[a1 + k][1]
                    if forma_src not in self.H:
                        continue
                    i_mt, forma_mt = wm[b1 + k]
                    r = self.error_homograf(x["mt"], i_mt, forma_src, forma_mt)
                    if r is not None and r[1] != x["mt"]:
                        per_cas[(forma_src, r[0])].append((x, r[1]))
        for (forma, lectura), casos in sorted(per_cas.items()):
            # Fórmules repetides del BOE ("S'afegeix un nou article 468 bis"):
            # una sola per plantilla (el src sense xifres).
            plantilles, unics = set(), []
            for x, mt_error in casos:
                p = re.sub(r"\d+", "0", comu.norm(x["src"]))
                if p not in plantilles:
                    plantilles.add(p)
                    unics.append((x, mt_error))
            casos = unics
            self.stats[f"homograf_corpus:{forma}:{lectura}"] = len(casos)
            self.rng.shuffle(casos)
            for x, mt_error in casos[:MAX_HOMOGRAF_CORPUS]:
                part = particio(x["doc"])
                meta = {"id": x["id"], "font": x["font"], "forma": forma, "lectura": lectura}
                self.afig(part, "0_positiu", x["src"], x["mt"], 0.9, **meta)
                self.afig(part, "3_error_sentit", x["src"], mt_error, 0.1, **meta)

    def homografs_creats(self) -> None:
        creats = json.loads(CREATS.read_text(encoding="utf-8"))
        E = self.E
        for n, x in enumerate(creats):
            motiu = E.motiu(x["src"], x["mt"])
            if motiu:
                print(f"AVÍS: frase creada {n} exclosa ({motiu}): {x['src']}", file=sys.stderr)
                self.stats["creats_exclosos"] += 1
                continue
            idx = f"HC-{n:03d}"
            part = particio(idx)
            meta = {"id": idx, "font": "creada", "forma": x["forma"], "lectura": x["lectura"]}
            self.afig(part, "0_positiu", x["src"], x["mt"], 0.9, **meta)
            self.afig(part, "3_error_sentit", x["src"], x["mt_error"], 0.1, **meta)

    # --- test de circularitat ---------------------------------------------

    def circularitat(self, positius: list[dict]) -> list[dict]:
        files = []
        for x in positius:
            if particio(x["doc"]) == "train":
                continue
            marcadors = [(i, f) for i, f in x["marcadors"] if f in self.P]
            reservats = [(i, f) for i, f in marcadors if f in self.res_val]
            if not reservats:
                continue
            lliures = [(i, f) for i, f in marcadors if f not in self.res_val]
            meta = {"id": x["id"], "font": x["font"], "n_marcadors": len(marcadors)}
            n = len(reservats)
            files.append({"tipus": "circ_original", "src": x["src"], "mt": x["mt"], "score": 0.9, **meta})
            mt_r = comu.catalanitza(x["mt"], [i for i, _ in reservats], self.P, self.G)
            files.append({"tipus": "circ_reservats", "src": x["src"], "mt": mt_r,
                          "score": score_parcial(n, len(marcadors)), **meta,
                          "canviats": sorted(f for _, f in reservats),
                          "families": sorted({self.familia[f] for _, f in reservats})})
            if len(lliures) >= n:
                triats = self.rng.sample(lliures, n)
                mt_c = comu.catalanitza(x["mt"], [i for i, _ in triats], self.P, self.G)
                files.append({"tipus": "circ_control", "src": x["src"], "mt": mt_c,
                              "score": score_parcial(n, len(marcadors)), **meta,
                              "canviats": sorted(f for _, f in triats)})
        return files


def escriu(path_csv, files: list[dict]) -> None:
    with open(path_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["src", "mt", "score"])
        for x in files:
            w.writerow([x["src"], x["mt"], x["score"]])
    with open(path_csv.with_name(path_csv.stem + "_meta.jsonl"), "w", encoding="utf-8") as f:
        for x in files:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--llavor", type=int, default=20261118)
    ap.add_argument("--sense-reserva", action="store_true",
                    help="sense reservar res (per al model final); eixida en complet/")
    args = ap.parse_args()

    g = Generador(args.sense_reserva, args.llavor)
    positius = [json.loads(l) for l in open(comu.EIXIDA / "positius.jsonl", encoding="utf-8")]
    homografs = [json.loads(l) for l in open(comu.EIXIDA / "homografs_corpus.jsonl", encoding="utf-8")]
    for k, x in enumerate(positius):
        g.positiu(x)
        if (k + 1) % 2000 == 0:
            print(f"  {k + 1}/{len(positius)} positius", flush=True)
    g.homografs_corpus(homografs)
    g.homografs_creats()

    eixida = comu.EIXIDA / "complet" if args.sense_reserva else comu.EIXIDA
    eixida.mkdir(parents=True, exist_ok=True)
    for part in ("train", "val", "test"):
        files = g.files[part]
        g.rng.shuffle(files)
        escriu(eixida / f"{part}.csv", files)
    if not args.sense_reserva:
        circ = g.circularitat(positius)
        escriu(eixida / "test_circularitat.csv", circ)
        g.stats.update(f"circularitat:{x['tipus']}" for x in circ)

    resum = dict(sorted(g.stats.items()))
    for part in ("train", "val", "test"):
        scores = [x["score"] for x in g.files[part]]
        resum[f"{part}:files"] = len(scores)
        resum[f"{part}:score_mitjana"] = round(sum(scores) / len(scores), 3)
    (eixida / "estadistiques_corpus.json").write_text(json.dumps(resum, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in resum.items():
        if not k.startswith("homograf_corpus"):
            print(f"  {k}: {v}")
    print("Homògrafs del corpus (forma:lectura):",
          {k.split(":", 1)[1]: v for k, v in resum.items() if k.startswith("homograf_corpus")})


if __name__ == "__main__":
    main()
