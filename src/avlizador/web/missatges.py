"""Textos de la interfície i de la API en les dues llengües (valencià de
l'AVL i castellà), un JSON per llengua en `textos/`. La llengua es tria
amb `?idioma=es|ca-valencia`, després amb la galeta tècnica `idioma` i,
si no n'hi ha cap, amb la capçalera `Accept-Language`; per defecte,
valencià.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

IDIOMES_INTERFICIE = ("ca-valencia", "es")
PER_DEFECTE = "ca-valencia"
CARPETA = Path(__file__).resolve().parent / "textos"


@cache
def textos(idioma: str) -> dict:
    """
    >>> sorted(textos("es")) == sorted(textos("ca-valencia"))
    True
    """
    idioma = idioma if idioma in IDIOMES_INTERFICIE else PER_DEFECTE
    return json.loads((CARPETA / f"{idioma}.json").read_text(encoding="utf-8"))


def tria_idioma(parametre: str | None, accept_language: str | None, galeta: str | None = None) -> str:
    """
    >>> tria_idioma("es", None), tria_idioma(None, "es-ES,es;q=0.9"), tria_idioma(None, "en"), tria_idioma("xx", None)
    ('es', 'es', 'ca-valencia', 'ca-valencia')
    >>> tria_idioma(None, "es-ES", galeta="ca-valencia")
    'ca-valencia'
    """
    for valor in (parametre, galeta):
        if valor in IDIOMES_INTERFICIE:
            return valor
    for part in (accept_language or "").split(","):
        codi = part.split(";")[0].strip().lower()
        if codi.startswith("es"):
            return "es"
        if codi.startswith("ca"):
            return "ca-valencia"
    return PER_DEFECTE


def missatge(idioma: str, clau: str, **valors) -> str:
    return textos(idioma)["api"][clau].format(**valors)


def nombre(n: int) -> str:
    """Milers amb punt, com s'escriu en valencià i en castellà.

    >>> nombre(20000), nombre(999)
    ('20.000', '999')
    """
    return f"{n:,}".replace(",", ".")
