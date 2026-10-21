"""
llm/punts.py -- Estructura comuna de les dos capes de LLM: un "punt
ambigu" és un lloc de la frase on el motor de regles ha hagut de triar
una opció per defecte (o deixar el text sense tocar) perquè la decisió
depén del significat. Cada punt porta les opcions TANCADES (el text exacte
de cada token per a cada opció) i quina és la del motor.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..rules import Token, detokenize


@dataclass
class PuntAmbigu:
    """`opcions[etiqueta]` dona el text nou de cada token de `indexs`, en
    el mateix orde. `per_defecte` és l'etiqueta que equival a la sortida
    actual del motor (no canviar res)."""

    tipus: str
    indexs: tuple[int, ...]
    marcada: str
    opcions: dict[str, tuple[str, ...]]
    per_defecte: str
    decisio: str | None = None
    resposta_llm: str = ""
    extra: dict = field(default_factory=dict)

    def aplica(self, tokens: list[Token], etiqueta: str) -> None:
        for index, text in zip(self.indexs, self.opcions[etiqueta]):
            tokens[index].translated = text
            tokens[index].is_translated = True


def resol(text: str, tokens: list[Token], punts: list[PuntAmbigu], prompts: dict, client) -> tuple[str, list[PuntAmbigu]]:
    """Per a cada punt, demana al LLM (si n'hi ha) una etiqueta de les
    opcions i l'aplica. Si no hi ha client, o el model no tria una opció
    vàlida, es queda la del motor (`per_defecte`)."""
    for punt in punts:
        etiqueta = None
        if client is not None:
            system, construeix_prompt = prompts[punt.tipus]
            etiqueta, punt.resposta_llm = client.tria(
                system, construeix_prompt(text, punt), list(punt.opcions)
            )
        punt.decisio = etiqueta or punt.per_defecte
        if punt.decisio != punt.per_defecte:
            punt.aplica(tokens, punt.decisio)
    return detokenize(tokens), punts
