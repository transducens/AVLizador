"""Registre dels parells que oferix la interfície.

Cada parell és una entrada amb el codi d'origen i de destí (que també són
els valors de l'atribut `lang` de les caixes de text), el nom de cada
varietat en les llengües de la interfície, la funció que traduïx i el
**tipus** (10/11/2026, fase 7 de la interfície):

- `"idioma"`: traducció entre idiomes diferents (per exemple, castellà ->
  valencià quan existisca el traductor del repo de *finetuning*). Ix en
  la pàgina "Traducció d'idiomes".
- `"dialecte"`: adaptació entre varietats de la MATEIXA llengua. El
  català -> valencià d'AVLizador és d'este tipus, no una traducció entre
  idiomes. Ix en la secció "Adaptador dialectal".

Afegir un parell és afegir una entrada ací: les pàgines construïxen els
selectors amb els parells del seu tipus (`GET /api/parells?tipus=...`).

El valencià -> català del paquet existix però està congelat: no s'oferix.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

TIPUS = ("idioma", "dialecte")


@dataclass(frozen=True)
class Parell:
    origen: str
    desti: str
    nom_origen: dict[str, str]
    nom_desti: dict[str, str]
    tradueix: Callable[[str], str]
    tipus: str = "idioma"

    def __post_init__(self) -> None:
        if self.tipus not in TIPUS:
            raise ValueError(f"tipus ha de ser un de {TIPUS}, no {self.tipus!r}")

    def descriu(self, idioma: str) -> dict:
        return {
            "origen": self.origen,
            "desti": self.desti,
            "nom_origen": self.nom_origen.get(idioma, self.nom_origen["ca-valencia"]),
            "nom_desti": self.nom_desti.get(idioma, self.nom_desti["ca-valencia"]),
            "tipus": self.tipus,
        }


def parells_per_defecte(mode: str) -> dict[tuple[str, str], Parell]:
    """El registre que fa servir l'aplicació. `mode`: "complet" (motor +
    model de llengua; KenLM des del 13/11/2026) o "motor" (només regles). Els imports del traductor van
    dins: el paquet no es carrega fins que es crida."""

    def cat_val(text: str) -> str:
        from ..traductor_cat_val import translate_cat_val, translate_cat_val_motor

        return (translate_cat_val if mode == "complet" else translate_cat_val_motor)(text)

    parells = [
        Parell(
            origen="ca",
            desti="ca-valencia",
            nom_origen={"ca-valencia": "Català", "es": "Catalán"},
            nom_desti={"ca-valencia": "Valencià", "es": "Valenciano"},
            tradueix=cat_val,
            tipus="dialecte",
        ),
    ]
    return {(p.origen, p.desti): p for p in parells}
