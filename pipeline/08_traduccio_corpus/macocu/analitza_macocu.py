"""
analitza_macocu.py -- Anàlisi del corpus MaCoCu-ca 1.0 SENCER (no del
filtrat): quant de català i quant de valencià hi ha (Grau Dialectal) i
quantes vegades apareixen les paraules problemàtiques del lèxic
(ambigües que decidix FLOR, homonímia, col·lisions, canvi de gènere).
Petició de l'usuari (09/11/2026): es vol entrenar amb tot i cal saber
què hi ha.

Tres passos (vore README.es.md d'esta carpeta):

1. `recompte` (una passada pel XML, sense spaCy, en paral·lel):
   - estadístiques del corpus: documents, paràgrafs per qualitat jusText,
     idioma, títols, fluïdesa (lm_score), frases i paraules;
   - **recompte de TOT el corpus** de cada forma catalana i valenciana de
     les entrades del lèxic amb `problema` (cambio_genero, colision,
     colision_homonima, homonimia_lexica) i de les 20 paraules que van a
     FLOR (`punts.carrega_punts`). Compta la forma escrita, sense mirar
     el sentit ("nou" adjectiu i "nou" fruit compten igual). En dos
     àmbits: tot el corpus i els paràgrafs bons (`good`, `ca`);
   - escriu totes les frases d'una **mostra de documents** (per hash de
     l'id del document, uniforme i determinista; `--fraccio`, 1 % per
     defecte) a `mostra_docs.jsonl`, per al pas 2.
   Eixides: `analisi_recompte.json`, `mostra_docs.jsonl`.

2. `gd` (spaCy, en paral·lel i reprenible): `calcula_gd(text)` sense
   `dialecte` (frase sense marcadors -> GD None, fora de les mitjanes) de
   cada frase de la mostra. Eixida: `mostra_gd.jsonl`.

3. `informe`: ajunta-ho tot en `analisi_macocu.json` i una taula en
   Markdown `analisi_macocu.md`: distribució del GD per frase i per
   document, GD/GDV/GDC globals, per subconjunt (tot, paràgrafs bons, les
   frases vàlides del filtre), per TLD, dominis més valencians, marcadors
   més freqüents i el recompte de les paraules del lèxic.

Ús (des de l'arrel del repositori):
    python pipeline/08_traduccio_corpus/macocu/analitza_macocu.py recompte --processos 6
    python pipeline/08_traduccio_corpus/macocu/analitza_macocu.py recompte --limit-mb 200   # prova
    python pipeline/08_traduccio_corpus/macocu/analitza_macocu.py gd --processos 6
    python pipeline/08_traduccio_corpus/macocu/analitza_macocu.py informe
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comu import (  # noqa: E402
    DIR,
    XML,
    _PARAULA,
    _SEPARA,
    frase_valida,
    paragraf_bo,
    paragrafs,
)

ARREL = Path(__file__).resolve().parents[3]
LEXIC = ARREL / "dades" / "lexic" / "lexico_general.json"
RECOMPTE = DIR / "analisi_recompte.json"
MOSTRA = DIR / "mostra_docs.jsonl"
MOSTRA_GD = DIR / "mostra_gd.jsonl"
PROGRES_GD = DIR / "progres_analisi_gd.json"
INFORME_JSON = DIR / "analisi_macocu.json"
INFORME_MD = DIR / "analisi_macocu.md"

PROBLEMES = ("homonimia_lexica", "colision_homonima", "colision", "cambio_genero")


# --------------------------------------------------------------------------
# Formes a comptar
# --------------------------------------------------------------------------

def tokens(text: str) -> list[str]:
    """Paraules en minúscules, com el primer tall de `filtra_macocu`
    (l'apòstrof separa: "d'aquest" -> "d", "aquest").

    >>> tokens("L'anou i el Cop d'ull.")
    ['l', 'anou', 'i', 'el', 'cop', 'd', 'ull']
    """
    return _PARAULA.findall(text.lower())


def entrades_lexic() -> list[dict]:
    """Entrades amb `problema` (pot ser llista) + les paraules que van a
    FLOR. Cada una amb les seues formes catalana i valenciana com a tuples
    de tokens (també expressions de diverses paraules)."""
    from avlizador.traductor_cat_val.model_llengua.punts import carrega_punts

    eixida = []
    for e in json.loads(LEXIC.read_text(encoding="utf-8")):
        p = e.get("problema")
        problemes = [x for x in (p if isinstance(p, list) else [p]) if x in PROBLEMES]
        if not problemes:
            continue
        eixida.append({
            "id": e["id"], "problema": problemes, "categoria": e.get("categoria"),
            "catalan": e.get("catalan", ""), "valenciano": e.get("valenciano", ""),
            "genero_cat": e.get("genero_cat"), "genero_val": e.get("genero_val"),
            "forma_problematica": e.get("forma_problematica"),
        })
    for forma, p in carrega_punts().items():
        for cand in p["candidats"]:
            if cand == forma:
                continue
            eixida.append({"id": f"FLOR:{forma}", "problema": [f"flor_{p['tipus']}"], "categoria": p["categoria"],
                           "catalan": forma, "valenciano": cand})
    return eixida


def index_formes(entrades: list[dict]) -> dict[str, list[tuple[str, ...]]]:
    """{primera paraula: [formes (tuples)]} per a buscar expressions."""
    idx: dict[str, set] = defaultdict(set)
    for e in entrades:
        for camp in ("catalan", "valenciano"):
            t = tuple(tokens(e[camp]))
            if t:
                idx[t[0]].add(t)
    return {k: sorted(v, key=len, reverse=True) for k, v in idx.items()}


# --------------------------------------------------------------------------
# Pas 1: recompte
# --------------------------------------------------------------------------

_IDX: dict | None = None


def _inicia_recompte(idx: dict) -> None:
    global _IDX
    _IDX = idx


def _compta_lot(lot: list[tuple[bool, str]]) -> tuple[Counter, Counter, int, int]:
    """Torna (formes en tot, formes en bons, paraules en tot, paraules en bons)."""
    tot, bons = Counter(), Counter()
    n_tot = n_bons = 0
    for bo, text in lot:
        toks = tokens(text)
        n_tot += len(toks)
        if bo:
            n_bons += len(toks)
        for i, t in enumerate(toks):
            formes = _IDX.get(t)
            if not formes:
                continue
            for f in formes:
                if len(f) == 1 or tuple(toks[i:i + len(f)]) == f:
                    k = " ".join(f)
                    tot[k] += 1
                    if bo:
                        bons[k] += 1
    return tot, bons, n_tot, n_bons


def en_mostra(doc_id: str, fraccio: float) -> bool:
    """Mostra uniforme i determinista de documents.

    >>> en_mostra("doc", 1.0), en_mostra("doc", 0.0)
    (True, False)
    """
    if fraccio >= 1.0:
        return True
    h = int.from_bytes(hashlib.blake2b(doc_id.encode(), digest_size=8).digest(), "big")
    return h / 2**64 < fraccio


def _bucket_lm(lm: float) -> str:
    return f"{min(int(lm * 10), 9) / 10:.1f}"


def recompte(args: argparse.Namespace) -> None:
    entrades = entrades_lexic()
    idx = index_formes(entrades)
    est: Counter = Counter()
    qualitat, idioma, lm = Counter(), Counter(), Counter()
    formes_tot, formes_bons = Counter(), Counter()
    docs_mostra = 0
    limit = args.limit_mb * 1_000_000 if args.limit_mb else None
    t0 = time.time()
    doc_actual = None
    lot: list[tuple[bool, str]] = []

    def suma(res) -> None:
        a, b, nt, nb = res
        formes_tot.update(a)
        formes_bons.update(b)
        est["paraules"] += nt
        est["paraules_bons"] += nb

    with mp.Pool(args.processos, initializer=_inicia_recompte, initargs=(idx,)) as pool, \
            open(MOSTRA, "w", encoding="utf-8") as out:
        pendents = []
        for doc, par, text in paragrafs(XML, limit):
            if doc.get("id") != doc_actual:
                doc_actual = doc.get("id")
                est["documents"] += 1
                dins = en_mostra(doc_actual or "", args.fraccio)
                docs_mostra += dins
            est["paragrafs"] += 1
            qualitat[par.get("quality", "?")] += 1
            idioma[par.get("lang", "?")] += 1
            if par.get("heading") == "yes":
                est["paragrafs_titol"] += 1
            lmv = float(par.get("lm_score", 0) or 0)
            lm[_bucket_lm(lmv)] += 1
            bo = par.get("quality") == "good" and par.get("lang") == "ca"
            est["paragrafs_bons"] += bo
            est["paragrafs_filtre"] += paragraf_bo(par, 0.7)
            lot.append((bo, text))
            frases = [f.strip() for f in _SEPARA.split(text) if f.strip()]
            est["frases"] += len(frases)
            if dins:
                domini = doc.get("domain", "")
                for i, f in enumerate(frases, 1):
                    out.write(json.dumps({
                        "id": f"{par.get('id')}.s{i}", "doc": doc_actual, "domini": domini,
                        "tld": domini.rsplit(".", 1)[-1] if "." in domini else "",
                        "quality": par.get("quality"), "lang": par.get("lang"),
                        "heading": par.get("heading") == "yes", "lm_score": lmv,
                        "filtre": paragraf_bo(par, 0.7) and frase_valida(f), "text": f,
                    }, ensure_ascii=False) + "\n")
                    est["frases_mostra"] += 1
            if len(lot) >= args.lot:
                pendents.append(pool.apply_async(_compta_lot, (lot,)))
                lot = []
                while len(pendents) > args.processos * 2:
                    suma(pendents.pop(0).get())
            if est["paragrafs"] % 1_000_000 == 0:
                print(f"  {est['paragrafs']:,} paràgrafs, {est['documents']:,} documents, "
                      f"{est['frases_mostra']:,} frases en la mostra, {time.time() - t0:,.0f} s", flush=True)
        if lot:
            pendents.append(pool.apply_async(_compta_lot, (lot,)))
        for p in pendents:
            suma(p.get())

    est["documents_mostra"] = docs_mostra
    est["segons"] = round(time.time() - t0)
    resum = {
        "fraccio": args.fraccio, "limit_mb": args.limit_mb, **est,
        "qualitat": dict(qualitat.most_common()), "idioma": dict(idioma.most_common()),
        "lm_score": dict(sorted(lm.items())),
        "entrades": entrades,
        "formes_tot": dict(formes_tot), "formes_bons": dict(formes_bons),
    }
    RECOMPTE.write_text(json.dumps(resum, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in resum.items() if k not in ("entrades", "formes_tot", "formes_bons")},
                     ensure_ascii=False, indent=2))


# --------------------------------------------------------------------------
# Pas 2: gd
# --------------------------------------------------------------------------

def _inicia_gd() -> None:
    from avlizador.grau_dialectal.gd import calcula_gd

    calcula_gd("Aquest servei és nou.")


def _gd_frase(linia: str) -> str:
    from avlizador.grau_dialectal.gd import calcula_gd

    r = json.loads(linia)
    g = calcula_gd(r["text"])
    del r["text"]
    r.update(paraules=g["total_paraules"], occ=g["total_occidentals"], ori=g["total_orientals"], gd=g["gd"],
             m_occ=g["marcadors_occidentals"], m_or=g["marcadors_orientals"])
    return json.dumps(r, ensure_ascii=False)


def gd(args: argparse.Namespace) -> None:
    progres = json.loads(PROGRES_GD.read_text()) if PROGRES_GD.exists() and not args.reinicia else {}
    fetes = progres.get("linies", 0)
    if fetes and MOSTRA_GD.exists():
        os.truncate(MOSTRA_GD, progres["mida"])
    else:
        fetes = 0
        MOSTRA_GD.write_text("", encoding="utf-8")
    t0 = time.time()
    with mp.Pool(args.processos, initializer=_inicia_gd) as pool, \
            open(MOSTRA, encoding="utf-8") as f, open(MOSTRA_GD, "a", encoding="utf-8") as out:
        for _ in range(fetes):
            next(f)
        linies = fetes
        while True:
            lot = [l for _, l in zip(range(args.lot), f)]
            if not lot:
                break
            for res in pool.imap(_gd_frase, lot, chunksize=64):
                out.write(res + "\n")
            out.flush()
            linies += len(lot)
            PROGRES_GD.write_text(json.dumps({"linies": linies, "mida": out.tell()}))
            print(f"  {linies:,} frases, {time.time() - t0:,.0f} s", flush=True)
    print(f"Fet: {linies:,} frases en {time.time() - t0:,.0f} s")


# --------------------------------------------------------------------------
# Pas 3: informe
# --------------------------------------------------------------------------

TRAMS = ("sense marcadors", "0 (català pur)", "(0, 0,25)", "[0,25, 0,5)", "[0,5, 0,75)", "[0,75, 1)",
         "1 (valencià pur)")


def tram(gd_: float | None) -> str:
    """
    >>> [tram(x) for x in (None, 0.0, 0.1, 0.5, 1.0)]
    ['sense marcadors', '0 (català pur)', '(0, 0,25)', '[0,5, 0,75)', '1 (valencià pur)']
    """
    if gd_ is None:
        return TRAMS[0]
    if gd_ == 0:
        return TRAMS[1]
    if gd_ == 1:
        return TRAMS[6]
    return TRAMS[2 + min(int(gd_ * 4), 3)]


class Acum:
    """Sumes per a un subconjunt de frases."""

    def __init__(self) -> None:
        self.frases = 0
        self.paraules = self.occ = self.ori = 0
        self.trams: Counter = Counter()
        self.purs2: Counter = Counter()  # GD 0 / 1 amb >= 2 marcadors

    def afig(self, r: dict) -> None:
        self.frases += 1
        self.paraules += r["paraules"]
        self.occ += r["occ"]
        self.ori += r["ori"]
        self.trams[tram(r["gd"])] += 1
        if r["gd"] in (0.0, 1.0) and r["occ"] + r["ori"] >= 2:
            self.purs2["cat" if r["gd"] == 0 else "val"] += 1

    def resum(self) -> dict:
        m = self.occ + self.ori
        return {
            "frases": self.frases, "paraules": self.paraules, "marcadors": m,
            "gd": round(self.occ / m, 4) if m else None,
            "gdv": round(1 - self.ori / self.paraules, 4) if self.paraules else None,
            "gdc": round(1 - self.occ / self.paraules, 4) if self.paraules else None,
            "trams": {t: self.trams[t] for t in TRAMS},
            "pures_2_marcadors": dict(self.purs2),
        }


def informe(args: argparse.Namespace) -> None:
    rec = json.loads(RECOMPTE.read_text(encoding="utf-8"))
    subconjunts = {"tot": Acum(), "bons": Acum(), "filtre": Acum()}
    per_tld: dict[str, Acum] = defaultdict(Acum)
    docs: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    dominis: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])  # occ, ori, frases
    m_occ, m_or = Counter(), Counter()
    with open(MOSTRA_GD, encoding="utf-8") as f:
        for linia in f:
            r = json.loads(linia)
            subconjunts["tot"].afig(r)
            if r["quality"] == "good" and r["lang"] == "ca":
                subconjunts["bons"].afig(r)
            if r["filtre"]:
                subconjunts["filtre"].afig(r)
            per_tld[r["tld"]].afig(r)
            d = docs[r["doc"]]
            d[0] += r["occ"]
            d[1] += r["ori"]
            dm = dominis[r["domini"]]
            dm[0] += r["occ"]
            dm[1] += r["ori"]
            dm[2] += 1
            m_occ.update(x.lower() for x in r["m_occ"])
            m_or.update(x.lower() for x in r["m_or"])

    docs_trams = Counter(tram(o / (o + c) if o + c else None) for o, c in docs.values())
    docs_valencians = sum(1 for o, c in docs.values() if o + c >= 5 and o / (o + c) >= 0.75)
    dominis_val = sorted(
        ((dm, o, c, n) for dm, (o, c, n) in dominis.items() if o + c >= args.min_marcadors_domini),
        key=lambda x: (-x[1] / (x[1] + x[2]), -(x[1] + x[2])))[:40]

    ft, fb = rec["formes_tot"], rec["formes_bons"]

    def n(forma: str, d: dict) -> int:
        return d.get(" ".join(tokens(forma)), 0)

    paraules = []
    for e in rec["entrades"]:
        paraules.append({**e, "n_cat": n(e["catalan"], ft), "n_val": n(e["valenciano"], ft),
                         "n_cat_bons": n(e["catalan"], fb), "n_val_bons": n(e["valenciano"], fb)})

    resum = {
        "corpus": {k: v for k, v in rec.items() if k not in ("entrades", "formes_tot", "formes_bons")},
        "gd": {k: a.resum() for k, a in subconjunts.items()},
        "gd_documents": {"documents": len(docs), "trams": {t: docs_trams[t] for t in TRAMS},
                         "documents_valencians_5_marcadors_075": docs_valencians},
        "gd_per_tld": {t: a.resum() for t, a in sorted(per_tld.items(), key=lambda x: -x[1].frases)[:15]},
        "dominis_mes_valencians": [{"domini": d, "occ": o, "ori": c, "frases": n_, "gd": round(o / (o + c), 4)}
                                   for d, o, c, n_ in dominis_val],
        "marcadors_occidentals": m_occ.most_common(60),
        "marcadors_orientals": m_or.most_common(60),
        "paraules_lexic": paraules,
    }
    INFORME_JSON.write_text(json.dumps(resum, ensure_ascii=False, indent=1), encoding="utf-8")
    INFORME_MD.write_text(markdown(resum), encoding="utf-8")
    print(markdown(resum))


def _pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f} %" if b else "-"


def markdown(r: dict) -> str:
    c = r["corpus"]
    L = ["# Anàlisi de MaCoCu-ca 1.0 (corpus sencer)", "",
         f"Documents {c['documents']:,}, paràgrafs {c['paragrafs']:,} (bons good+ca {c['paragrafs_bons']:,}; "
         f"filtre {c['paragrafs_filtre']:,}), frases {c['frases']:,}, paraules {c['paraules']:,}. "
         f"Mostra de GD: {c['documents_mostra']:,} documents ({c['fraccio']:.1%}), {c['frases_mostra']:,} frases.",
         "", "## GD per subconjunt (mostra)", "",
         "| Subconjunt | Frases | GD | GDV | GDC | " + " | ".join(TRAMS) + " |",
         "|---" * (5 + len(TRAMS)) + "|"]
    for k, a in r["gd"].items():
        L.append(f"| {k} | {a['frases']:,} | {a['gd']} | {a['gdv']} | {a['gdc']} | "
                 + " | ".join(_pct(a["trams"][t], a["frases"]) for t in TRAMS) + " |")
    d = r["gd_documents"]
    L += ["", f"## GD per document ({d['documents']:,} documents)", "",
          " | ".join(f"{t}: {_pct(d['trams'][t], d['documents'])}" for t in TRAMS),
          f"Documents valencians (≥5 marcadors, GD ≥ 0,75): {d['documents_valencians_5_marcadors_075']:,}",
          "", "## GD per TLD", "", "| TLD | Frases | GD | Valencià pur (≥2) | Català pur (≥2) |", "|---|---|---|---|---|"]
    for t, a in r["gd_per_tld"].items():
        L.append(f"| {t} | {a['frases']:,} | {a['gd']} | {a['pures_2_marcadors'].get('val', 0):,} | "
                 f"{a['pures_2_marcadors'].get('cat', 0):,} |")
    L += ["", "## Dominis més valencians", "", "| Domini | Frases | Occ. | Or. | GD |", "|---|---|---|---|---|"]
    for x in r["dominis_mes_valencians"][:25]:
        L.append(f"| {x['domini']} | {x['frases']:,} | {x['occ']:,} | {x['ori']:,} | {x['gd']} |")
    L += ["", "## Marcadors més freqüents (mostra)", "",
          "Occidentals: " + ", ".join(f"{m} {n:,}" for m, n in r["marcadors_occidentals"][:30]), "",
          "Orientals: " + ", ".join(f"{m} {n:,}" for m, n in r["marcadors_orientals"][:30])]
    L += ["", "## Paraules del lèxic (corpus sencer, forma escrita)", ""]
    grups: dict[str, list] = defaultdict(list)
    for p in r["paraules_lexic"]:
        for pr in p["problema"]:
            grups[pr].append(p)
    for pr, ps in grups.items():
        ps = sorted(ps, key=lambda p: -(p["n_cat"] + p["n_val"]))
        L += ["", f"### {pr} ({len(ps)} entrades; català {sum(p['n_cat'] for p in ps):,}, "
                  f"valencià {sum(p['n_val'] for p in ps):,})", "",
              "| Id | Català | n | Valencià | n | Gènere |", "|---|---|---|---|---|---|"]
        for p in ps:
            gen = f"{p.get('genero_cat') or ''}→{p.get('genero_val') or ''}" if p.get("genero_cat") else ""
            L.append(f"| {p['id']} | {p['catalan']} | {p['n_cat']:,} | {p['valenciano']} | {p['n_val']:,} | {gen} |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="pas", required=True)
    r = sub.add_parser("recompte", help="pas 1: estadístiques + paraules del lèxic (tot) + mostra de documents")
    r.add_argument("--processos", type=int, default=max(1, mp.cpu_count() - 2))
    r.add_argument("--fraccio", type=float, default=0.01, help="fracció de documents per a la mostra de GD (0,01)")
    r.add_argument("--lot", type=int, default=5000, help="paràgrafs per lot de recompte")
    r.add_argument("--limit-mb", type=int, default=0, help="llegir només els primers N MB (proves)")
    g = sub.add_parser("gd", help="pas 2: GD de cada frase de la mostra (spaCy)")
    g.add_argument("--processos", type=int, default=max(1, mp.cpu_count() - 2))
    g.add_argument("--lot", type=int, default=20_000)
    g.add_argument("--reinicia", action="store_true")
    i = sub.add_parser("informe", help="pas 3: ajunta-ho en analisi_macocu.{json,md}")
    i.add_argument("--min-marcadors-domini", type=int, default=50)
    args = p.parse_args(argv)
    {"recompte": recompte, "gd": gd, "informe": informe}[args.pas](args)


if __name__ == "__main__":
    main()
