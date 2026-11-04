"""Missatges de la API en les dues llengües de la interfície (valencià de
l'AVL i castellà). La llengua es tria amb `?idioma=es|ca-valencia` o, si
no n'hi ha, amb la capçalera `Accept-Language`; per defecte, valencià.
"""

from __future__ import annotations

IDIOMES_INTERFICIE = ("ca-valencia", "es")
PER_DEFECTE = "ca-valencia"

MISSATGES = {
    "ca-valencia": {
        "ocupat": "El servei està ocupat. Torna-ho a intentar en uns segons.",
        "massa_llarg": "El text és massa llarg: el màxim és de {maxim} caràcters i en té {n}.",
        "parell_desconegut": "Este parell d'idiomes no està disponible.",
        "peticio_no_valida": "La petició no és vàlida. Comprova el text i els idiomes triats.",
        "error_traduccio": "No s'ha pogut traduir el text. Torna-ho a intentar.",
        "error_gd": "No s'ha pogut calcular el Grau Dialectal. Torna-ho a intentar.",
    },
    "es": {
        "ocupat": "El servicio está ocupado. Vuelve a intentarlo en unos segundos.",
        "massa_llarg": "El texto es demasiado largo: el máximo es de {maxim} caracteres y tiene {n}.",
        "parell_desconegut": "Este par de idiomas no está disponible.",
        "peticio_no_valida": "La petición no es válida. Comprueba el texto y los idiomas elegidos.",
        "error_traduccio": "No se ha podido traducir el texto. Vuelve a intentarlo.",
        "error_gd": "No se ha podido calcular el Grado Dialectal. Vuelve a intentarlo.",
    },
}


def tria_idioma(parametre: str | None, accept_language: str | None) -> str:
    """
    >>> tria_idioma("es", None), tria_idioma(None, "es-ES,es;q=0.9"), tria_idioma(None, "en"), tria_idioma("xx", None)
    ('es', 'es', 'ca-valencia', 'ca-valencia')
    """
    if parametre in IDIOMES_INTERFICIE:
        return parametre
    for part in (accept_language or "").split(","):
        codi = part.split(";")[0].strip().lower()
        if codi.startswith("es"):
            return "es"
        if codi.startswith("ca"):
            return "ca-valencia"
    return PER_DEFECTE


def missatge(idioma: str, clau: str, **valors) -> str:
    return MISSATGES.get(idioma, MISSATGES[PER_DEFECTE])[clau].format(**valors)
