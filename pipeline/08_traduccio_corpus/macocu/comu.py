"""
comu.py -- Lectura de MaCoCu-ca 1.0 compartida pels filtres de
`catala/` i `valencia/`, l'anàlisi (`analitza_macocu.py`) i KenLM
(`kenlm/`): obrir el XML (o el .zip), recórrer-lo per paràgrafs, partir
en frases i el criteri de frase vàlida i de paràgraf bo.

Corpus: MaCoCu-ca 1.0 (CLARIN.SI, hdl 11356/1837, CC0), web de 2022,
5,9 M documents. Format "prevert": `<doc ...>` amb metadades, `<p ...>`
amb qualitat jusText, idioma, fluïdesa (lm_score) i si és títol o dada
sensible; el text del paràgraf va en les línies de dins.
"""

from __future__ import annotations

import hashlib
import html
import io
import re
import sys
import zipfile
from pathlib import Path
from typing import Iterator

ARREL = Path(__file__).resolve().parents[3]
DIR = ARREL / "dades" / "macocu"
XML = DIR / "MaCoCu-ca-1.0.xml"

MIN_PARAULES, MAX_PARAULES = 8, 40  # com construeix_pool.py

_ATRIBUTS = re.compile(r'(\w+)="([^"]*)"')
# Separador de frases de construeix_pool.py: punt/interrogació/exclamació
# + espai + majúscula o cometes. No tracta abreviatures ("Sr.", "núm."):
# una frase tallada per una abreviatura acaba sense punt o comença en
# minúscula i la descarta `frase_valida`.
_SEPARA = re.compile(r"(?<=[.!?])\s+(?=[«\"“A-ZÀ-Ý])")
_INICI_LLISTA = re.compile(r"^\s*(\d+[\.\)º]|[a-zA-Z]\s?\)|[-–—•·*]|[IVXLC]+\.)\s")
# Paraula per al primer tall: lletres amb "·" o "-" dins ("col·lidisca",
# "vint-i-tres"). L'apòstrof separa ("d'aquestes" -> "d", "aquestes").
_PARAULA = re.compile(r"[^\W\d_]+(?:[·\-][^\W\d_]+)*")


def frase_valida(text: str) -> bool:
    """Frase completa, de 8 a 40 paraules, sense llistes ni majúscules
    senceres, amb pocs números (còpia de `construeix_pool.frase_valida`).

    >>> frase_valida("Aquest servei es prestarà durant tot l'any als ciutadans de la comarca.")
    True
    >>> frase_valida("a) Aquest servei es prestarà durant tot l'any als ciutadans.")
    False
    >>> frase_valida("Només tres paraules.")
    False
    """
    t = text.strip()
    n = len(t.split())
    if not (MIN_PARAULES <= n <= MAX_PARAULES):
        return False
    if not t[0].isupper() and t[0] not in "«\"“":
        return False
    if t[-1] not in ".?!" or t.endswith("..."):
        return False
    if _INICI_LLISTA.match(t) or t.upper() == t:
        return False
    amb_digits = sum(any(c.isdigit() for c in p) for p in t.split())
    return amb_digits <= max(2, n // 8)


def clau_repetida(text: str) -> bytes:
    """Hash del text normalitzat (minúscules, sense números ni puntuació)
    per a llevar repetides.

    >>> clau_repetida("Hola, món 2022.") == clau_repetida("hola  MÓN.")
    True
    """
    norm = " ".join(_PARAULA.findall(re.sub(r"\d+", "", text.lower())))
    return hashlib.blake2b(norm.encode("utf-8"), digest_size=8).digest()


# --------------------------------------------------------------------------
# Lectura del XML
# --------------------------------------------------------------------------

def obri_corpus(path: Path):
    """Obri el XML; si no està descomprimit, el llig directament del `.zip`
    (`MaCoCu-ca-1.0.xml.zip`), sense ocupar 15 GB més de disc."""
    if path.exists():
        return open(path, encoding="utf-8")
    zip_path = path.with_name(path.name + ".zip")
    if not zip_path.exists():
        sys.exit(f"No trobe ni {path} ni {zip_path}")
    z = zipfile.ZipFile(zip_path)
    nom = next(n for n in z.namelist() if n.endswith(".xml"))
    return io.TextIOWrapper(z.open(nom), encoding="utf-8")


def paragrafs(path: Path, limit_bytes: int | None = None) -> Iterator[tuple[dict, dict, str]]:
    """Recorre el XML línia a línia i torna (atributs del document,
    atributs del paràgraf, text). No carrega el fitxer sencer."""
    doc: dict = {}
    par: dict | None = None
    linies: list[str] = []
    llegit = 0
    with obri_corpus(path) as f:
        for linia in f:
            llegit += len(linia)
            if linia.startswith("<doc "):
                doc = dict(_ATRIBUTS.findall(linia))
            elif linia.startswith("<p "):
                par = dict(_ATRIBUTS.findall(linia))
                linies = []
            elif linia.startswith("</p>"):
                if par is not None:
                    yield doc, par, html.unescape(" ".join(l.strip() for l in linies))
                par = None
                if limit_bytes and llegit > limit_bytes:
                    return
            elif par is not None:
                linies.append(linia)


def paragraf_bo(par: dict, lm_min: float) -> bool:
    return (
        par.get("quality") == "good"
        and par.get("lang") == "ca"
        and par.get("heading") != "yes"
        and par.get("sensitive") != "yes"
        and float(par.get("lm_score", 0)) >= lm_min
    )
