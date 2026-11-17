"""
translate_invers.py -- Punt d'entrada públic del traductor en sentit
invers (català oriental -> valencià occidental). Mateix patró que
`translate.py` (orquestra `RuleEngineInvers`, reutilitzat entre crides)
-- vore eixe fitxer per al raonament complet de per què existix esta
indirecció.

`translate_cat_val` és SEMPRE el motor de regles + el postprocessat amb
model de llengua (`model_llengua/`) per als homògrafs del lèxic (decisió
de l'usuari, 29/10/2026). El model per defecte és, des del 13/11/2026,
**KenLM + classificador de sentit** (CPU, ~80 MB, sense torch); abans era
FLOR-760M, que des de la versió 2.0.0 ja no és en el paquet.
`translate_cat_val_motor` és el motor sol, per a comparar i per als
doctests de les regles.
"""

from __future__ import annotations

import warnings

from .rules.cat_val.engine import RuleEngineInvers

_ENGINE_INVERS: RuleEngineInvers | None = None


def translate_cat_val_motor(text: str) -> str:
    """Motor de regles sol, sense model de llengua.

    >>> translate_cat_val_motor("Tinc vuitanta anys i la meva obra és francesa.")
    'Tinc huitanta anys i la meua obra és francesa.'
    """
    global _ENGINE_INVERS
    if _ENGINE_INVERS is None:
        _ENGINE_INVERS = RuleEngineInvers()
    return _ENGINE_INVERS.translate(text)


MODELS = ("kenlm",)
# Model (13/11/2026, decisió de l'usuari): KenLM + classificador de sentit.
# Igualava o millorava FLOR-760M (el d'abans) en tots els benchmarks menys
# una frase del 151 i una de gplsi, és unes 8.000 vegades més ràpid i no
# necessita torch. Des de la versió 2.0.0 (17/11/2026) FLOR ja no és en el
# paquet, ni com a opció (decisió de l'usuari). Xifres i motius:
# `documentacio/resultats_model_llengua_kenlm.md`.
MODEL_PER_DEFECTE = "kenlm"


def translate_cat_val(text: str, model: str | None = None) -> str:
    """Convertix `text` de català oriental a valencià occidental: motor de
    regles + model de llengua (KenLM + classificador de sentit,
    `model_llengua/kenlm.py` i `sentit.py`) per als homògrafs.

    Cal el paquet `kenlm` (extra `[kenlm]`) i els tres fitxers del model,
    que es baixen de Hugging Face la primera vegada (o d'`AVLIZADOR_KENLM_DIR`).

    `model`:
    - `None` (per defecte): si falta alguna cosa, usa el motor sol i avisa
      una vegada (`AvisSenseModelLlengua`).
    - `"kenlm"`: el mateix, però si falta alguna cosa llança `FaltaKenLM`
      (s'ha demanat expressament: no torna al motor en silenci).

    >>> translate_cat_val("Hola.", model="flor")
    Traceback (most recent call last):
    ...
    ValueError: model desconegut: 'flor' (opcions: kenlm)
    """
    if model is not None and model not in MODELS:
        raise ValueError(f"model desconegut: {model!r} (opcions: {', '.join(MODELS)})")
    if model is None:
        from .model_llengua.kenlm import kenlm_disponible

        if not kenlm_disponible():
            _avisa_sense_model()
            return translate_cat_val_motor(text)
    from .model_llengua import translate_cat_val_kenlm

    return translate_cat_val_kenlm(text)


class AvisSenseModelLlengua(UserWarning):
    """Avís: falta el model de llengua i `translate_cat_val` usa el motor sol."""


_AVISAT = False


_COM_INSTALLAR = ("KenLM (el paquet 'kenlm' o els fitxers del model)",
                  'pip install "avlizador[kenlm]" (Linux o Docker); els fitxers es baixen de Hugging Face '
                  "la primera vegada (cal internet) o es llegixen d'AVLIZADOR_KENLM_DIR")


def _avisa_sense_model() -> None:
    global _AVISAT
    if not _AVISAT:
        que, com = _COM_INSTALLAR
        warnings.warn(
            f"Falta el model de llengua {que}: s'usa el motor de regles sol, que "
            "no resol els homògrafs ('cop', 'nou', 'manca'...). Per al sistema "
            f"complet: {com}.",
            AvisSenseModelLlengua,
            stacklevel=3,
        )
        _AVISAT = True
