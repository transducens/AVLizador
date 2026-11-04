"""Registre dels parells d'idiomes que oferix la interfície.

Cada parell és una entrada amb el codi d'origen i de destí (que també són
els valors de l'atribut `lang` de les caixes de text), el nom de cada
idioma en les llengües de la interfície i la funció que traduïx. Afegir un
parell (per exemple, castellà -> valencià quan existisca el traductor del
repo de *finetuning*) és afegir una entrada ací: la pàgina construïx els
selectors amb `GET /api/idiomes`.

El valencià -> català del paquet existix però està congelat: no s'oferix.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Parell:
    origen: str
    desti: str
    nom_origen: dict[str, str]
    nom_desti: dict[str, str]
    tradueix: Callable[[str], str]

    def descriu(self, idioma: str) -> dict:
        return {
            "origen": self.origen,
            "desti": self.desti,
            "nom_origen": self.nom_origen.get(idioma, self.nom_origen["ca-valencia"]),
            "nom_desti": self.nom_desti.get(idioma, self.nom_desti["ca-valencia"]),
        }


def parells_per_defecte(mode: str) -> dict[tuple[str, str], Parell]:
    """El registre que fa servir l'aplicació. `mode`: "complet" (motor +
    FLOR-760M) o "motor" (només regles). Els imports del traductor van
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
        ),
    ]
    return {(p.origen, p.desti): p for p in parells}
