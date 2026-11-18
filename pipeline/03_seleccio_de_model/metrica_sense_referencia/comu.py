"""Peces comunes de la mètrica sense referència (fase 2: corpus sintètic).

- Rutes i normalització.
- `Exclusions`: totes les dades d'avaluació (benchmarks manual, homògrafs,
  151, gplsi, BOE estricte/ampli complets, mostra BOE, gènere), per frase
  i, per al manual, per document. Res d'això pot entrar a l'entrenament.
- Pares val -> cat del lèxic: els MATEIXOS carregadors que el GD i el
  traductor (vore `grau_dialectal/gd.py`), sense cap llista a mà.
- Homògrafs de cat -> val trets del lèxic (`homonimia_lexica` amb la
  forma catalana ambigua i `colision_homonima`).
- `substituix`: canvia una paraula d'una frase valenciana per la catalana
  arreglant l'elisió, l'article, les contraccions i el determinant amb les
  funcions del motor.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
if str(RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(RAIZ / "src"))

from avlizador.grau_dialectal import gd  # noqa: E402
from avlizador.traductor_cat_val.rules import (  # noqa: E402
    Token,
    aplica_amb_prefix_elidit,
    corregeix_article_abans,
    corregeix_contraccio_al_abans,
    corregeix_determinant_abans,
    corregeix_elisio_de_abans,
    detokenize,
    preserva_majuscula,
    separa_prefix_elidit,
    te_problema,
    tokenize,
)

DADES = RAIZ / "dades"
BENCH = DADES / "benchmarks"
EIXIDA = DADES / "metrica_sense_referencia"
LEXIC_GENERAL = DADES / "lexic" / "lexico_general.json"

_APOS = str.maketrans({"’": "'", "ʼ": "'"})
_ESPAIS = re.compile(r"\s+")
_PARAULA = re.compile(r"[a-zà-ÿ·]+")


def norm(text: str) -> str:
    """Normalització per a comparar frases: apòstrofs, espais, minúscules."""
    return _ESPAIS.sub(" ", text.translate(_APOS)).strip().lower()


def paraules(text: str) -> list[str]:
    return _PARAULA.findall(norm(text))


def llig_json(path: Path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    if isinstance(d, dict):
        for clau in ("frases", "benchmark", "items", "data"):
            if isinstance(d.get(clau), list):
                return d[clau]
    return d


# --------------------------------------------------------------------------
# Dades d'avaluació (no poden entrar a l'entrenament)
# --------------------------------------------------------------------------

# Benchmarks xicotets: a més de la frase exacta, també es descarten les
# quasi iguals (Jaccard de paraules >= 0,6, com `construeix_pool.py`).
AVALUACIO_PETITS = [
    BENCH / "manual" / "benchmark_manual_cat_val.json",
    BENCH / "homografs" / "benchmark_homografs_cat_val.json",
    BENCH / "homografs" / "benchmark_homografs_v2_cat_val.json",
    BENCH / "homografs" / "benchmark_sistema_final_cat_val.json",
    BENCH / "curat_151" / "benchmark_corpus.json",
    BENCH / "gplsi" / "benchmark_gplsi.json",
    DADES / "benchmark_manual" / "benchmark_genero.json",
    DADES / "boe_net" / "muestra_test_dialectal.json",
]
# Benchmarks grans del BOE (publicats sencers a Hugging Face): frase exacta.
AVALUACIO_GRANS = [
    BENCH / "boe_dialectal" / "benchmark_boe_dialectal_estricte_complet.json",
    BENCH / "boe_dialectal" / "benchmark_boe_dialectal_ampli_complet.json",
    BENCH / "boe_dialectal" / "benchmark_boe_mostra_2000.json",
]
# Revisions del benchmark manual: d'ací es trauen els documents d'origen.
REVISIONS_MANUAL = [
    DADES / "benchmark_manual" / "revisio_boe_v2.json",
    DADES / "benchmark_manual" / "revisio_persona1.json",
    DADES / "benchmark_manual" / "revisio_persona2.json",
]
CAMPS_TEXT = ("oriental", "occidental", "texto_valenciano", "texto_catalan_boe",
              "oriental_corregit", "occidental_corregit")
JACCARD_MAX = 0.6


class Exclusions:
    """Frases i documents d'avaluació."""

    def __init__(self) -> None:
        self.frases: set[str] = set()
        self.docs: set[str] = set()
        self.ids: set[str] = set()
        self._petites: list[set[str]] = []
        self._index: dict[str, list[int]] = defaultdict(list)
        for path in AVALUACIO_PETITS:
            if not path.exists():
                print(f"AVÍS: no existix {path}", file=sys.stderr)
                continue
            for x in llig_json(path):
                for camp in CAMPS_TEXT:
                    if isinstance(x.get(camp), str) and x[camp].strip():
                        self._afig_petita(x[camp])
        for path in AVALUACIO_GRANS:
            for x in llig_json(path):
                for camp in ("oriental", "occidental"):
                    self.frases.add(norm(x[camp]))
        for path in REVISIONS_MANUAL:
            for x in llig_json(path):
                if x.get("document"):
                    self.docs.add(str(x["document"]))
                if x.get("id_origen"):
                    self.ids.add(str(x["id_origen"]))
                for camp in CAMPS_TEXT:
                    if isinstance(x.get(camp), str) and x[camp].strip():
                        self._afig_petita(x[camp])

    def _afig_petita(self, text: str) -> None:
        n = norm(text)
        if n in self.frases:
            return
        self.frases.add(n)
        ps = set(paraules(text))
        i = len(self._petites)
        self._petites.append(ps)
        for p in ps:
            if len(p) >= 6:
                self._index[p].append(i)

    def motiu(self, *textos: str, id: str | None = None, doc: str | None = None) -> str | None:
        """Per què cal excloure el parell (o `None` si es pot usar). Amb
        `doc`, també es descarten els documents d'on ix el manual (opcional:
        les lleis del BOE són llargues i se'n perd molt de text)."""
        if id is not None and id in self.ids:
            return "linia_manual"
        if doc is not None and doc in self.docs:
            return "document_manual"
        for t in textos:
            if norm(t) in self.frases:
                return "frase_avaluacio"
        for t in textos:
            ps = set(paraules(t))
            if not ps:
                continue
            comptes: dict[int, int] = defaultdict(int)
            for p in ps:
                if len(p) >= 6:
                    for i in self._index.get(p, ()):
                        comptes[i] += 1
            for i, c in comptes.items():
                if c < 2:
                    continue
                altra = self._petites[i]
                if len(ps & altra) / len(ps | altra) >= JACCARD_MAX:
                    return "quasi_igual_avaluacio"
        return None


# --------------------------------------------------------------------------
# Lèxic
# --------------------------------------------------------------------------

def parells_val_cat() -> dict[str, tuple[str, str]]:
    """`{forma valenciana: (forma catalana, font)}` d'una sola paraula, amb
    les dues formes dins dels marcadors del GD (que ja han tret
    ambigüitats, col·lisió verbal i homògrafs irresolubles). Primer els
    carregadors val -> cat (trien la canònica) i després els inversos per
    a les formes que falten."""
    formes = gd.carrega_formes_dialectals()
    occ = formes.occ_simple | formes.occ_verbal
    orr = formes.or_simple | formes.or_verbal
    directes = {
        "lexic": gd.carrega_lexic(),
        "demostratius": gd.carrega_demostratius(),
        "numerals": gd.carrega_numerals(),
        "possessius": gd._carrega_possessius(),
        "conjugacions": gd._carrega_conjugacions_pures(),
    }
    inversos = {
        "lexic": gd.carrega_lexic_invers(),
        "demostratius": gd.carrega_demostratius_invers(),
        "numerals": gd.carrega_numerals_invers(),
        "possessius": gd.carrega_possessius_invers(),
    }
    res: dict[str, tuple[str, str]] = {}

    def afig(v: str, c: str, font: str) -> None:
        v, c = v.lower(), c.lower()
        if v == c or " " in v or " " in c or v not in occ or c not in orr:
            return
        res.setdefault(v, (c, font))

    for font, d in directes.items():
        for v, c in d.items():
            afig(v, c, font)
    for font, d in inversos.items():
        for c, v in d.items():
            afig(v, c, font)
    return res


def entrades_lexic() -> list[dict]:
    with open(LEXIC_GENERAL, encoding="utf-8") as f:
        return json.load(f)


def generes_cat() -> tuple[dict[str, str], dict[str, str]]:
    """Dos diccionaris `{forma valenciana: gènere de la catalana}` trets
    del lèxic: el primer amb totes les entrades que en porten (per a
    desfer "l'" en "la": "l'eixida" -> "la sortida"), el segon només quan
    el gènere canvia ("gasto" m -> "despesa" f), per a corregir el
    determinant."""
    tots, canvi = {}, {}
    for e in entrades_lexic():
        gc, gv = e.get("genero_cat"), e.get("genero_val")
        if gc not in ("m", "f"):
            continue
        v = e["valenciano"].lower()
        tots.setdefault(v, gc)
        if isinstance(gv, str) and gv != gc:
            canvi.setdefault(v, gc)
    return tots, canvi


def homografs_cat_val() -> dict[str, dict]:
    """Formes catalanes ambigües per a cat -> val, trets del lèxic:

    - `homonimia_lexica` amb la forma problemàtica al costat català
      (`lado: "val"`) i valencià d'una paraula: `{"tipus": "homonimia",
      "dialectal": forma valenciana}` ("nou" -> "anou").
    - `colision_homonima`: `{"tipus": "colisio", "candidates": [...]}`
      ("cop" -> "colp" / "vegada").
    """
    res: dict[str, dict] = {}
    for e in entrades_lexic():
        cat, val = e["catalan"].lower(), e["valenciano"].lower()
        if " " in val or " " in cat:
            continue
        if te_problema(e, "colision_homonima"):
            d = res.setdefault(cat, {"tipus": "colisio", "candidates": []})
            if val not in d["candidates"]:
                d["candidates"].append(val)
        elif te_problema(e, "homonimia_lexica") and e.get("lado") == "val" \
                and e.get("forma_problematica", "").lower() == cat:
            res[cat] = {"tipus": "homonimia", "dialectal": val}
    return res


# --------------------------------------------------------------------------
# Substitució dins d'una frase
# --------------------------------------------------------------------------

def substituix(tokens: list[Token], i: int, nova: str, genere: str | None = None,
               canvia_genere: bool = False) -> None:
    """Posa `nova` en `tokens[i]` (que pot portar prefix elidit) i arregla
    l'entorn: elisió, article, contraccions i, si `canvia_genere`, el
    determinant (segons `genere`).

    Treballa sobre `translated` (la forma actual del token), així que les
    substitucions d'una frase s'han de fer de DRETA A ESQUERRA: el
    determinant valencià es corregix primer ("d'este gasto" -> "d'esta
    despesa") i després, si toca, es canvia ell ("d'aquesta despesa"). Les
    taules de determinants del motor són valencianes.

    >>> P = parells_val_cat(); _, canvi = generes_cat()
    >>> toks = tokenize("Parle d'este gasto.")
    >>> substituix(toks, 4, P["gasto"][0], canvi["gasto"], True)
    >>> substituix(toks, 2, P["esta"][0])
    >>> detokenize(toks)
    "Parle d'aquesta despesa."
    """
    tok = tokens[i]
    pr = separa_prefix_elidit(tok.translated)
    if pr is not None:
        prefix, resta = pr
        aplica_amb_prefix_elidit(tokens, i, prefix, resta, nova, genere or "")
    else:
        tok.translated = preserva_majuscula(tok.translated, nova)
        corregeix_elisio_de_abans(tokens, i)
        corregeix_contraccio_al_abans(tokens, i)
        corregeix_article_abans(tokens, i)
    tok.is_translated = True
    if canvia_genere and genere in ("m", "f") and pr is None:
        corregeix_determinant_abans(tokens, i, genere)
        corregeix_article_abans(tokens, i)


def catalanitza(text: str, indexs: list[int], P: dict, generes: tuple[dict, dict]) -> str:
    """Canvia per la forma catalana les paraules de `text` en les
    posicions `indexs` (índexs de `tokenize(text)`), de dreta a esquerra.

    >>> P = parells_val_cat(); G = generes_cat()
    >>> catalanitza("L'eixida del xiquet és hui.", [0, 4, 8], P, G)
    'La sortida del noi és avui.'
    """
    tots, canvi = generes
    tokens = tokenize(text)
    for i in sorted(set(indexs), reverse=True):
        v = forma_actual(tokens[i])
        if v is None or v not in P:
            continue
        substituix(tokens, i, P[v][0], tots.get(v), v in canvi)
    return contrau(detokenize(tokens))


# "de els" -> "dels": `corregeix_determinant_abans` no contrau el plural
# davant de vocal ("de les ensenyances" -> "de els ensenyaments").
_CONTRACCIO_PLURAL = re.compile(r"\b(de|a|per)( )(els)\b", re.IGNORECASE)
_CONTRACCIONS = {"de": "dels", "a": "als", "per": "pels"}


def contrau(text: str) -> str:
    """>>> contrau("La durada de els ensenyaments i A els xiquets.")
    'La durada dels ensenyaments i Als xiquets.'
    """
    return _CONTRACCIO_PLURAL.sub(
        lambda m: preserva_majuscula(m.group(1), _CONTRACCIONS[m.group(1).lower()]), text)


def forma_actual(tok: Token) -> str | None:
    """La paraula actual del token (`translated`) sense prefix elidit."""
    return paraula_del_token(tok.translated)


def paraula_del_token(surface: str) -> str | None:
    """La paraula sense prefix elidit, en minúscules (o `None`)."""
    p = gd._paraula_per_lookup(surface)
    return p.lower() if p else None


__all__ = [
    "RAIZ", "DADES", "EIXIDA", "Exclusions", "norm", "paraules", "llig_json",
    "parells_val_cat", "generes_cat", "homografs_cat_val", "substituix",
    "paraula_del_token", "tokenize", "detokenize", "gd",
]
