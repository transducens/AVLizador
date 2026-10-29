"""
translate_invers.py -- Punt d'entrada públic del traductor en sentit
invers (català oriental -> valencià occidental). Mateix patró que
`translate.py` (orquestra `RuleEngineInvers`, reutilitzat entre crides)
-- vore eixe fitxer per al raonament complet de per què existix esta
indirecció.

ESTRUCTURA FINAL (29/10/2026, decisió de l'usuari): `translate_cat_val` és
SEMPRE el motor de regles + el postprocessat amb model de llengua
(`traductor/model_llengua/`, FLOR-760M en CPU) per als homògrafs del lèxic.
Necessita `torch` i `transformers`; el model es carrega la primera vegada
(~5 s) i es reutilitza. `translate_cat_val_motor` és el motor sol, per a
comparar (`evalua_models.py --model traductor --direccio cat-val`) i per als
doctests de les regles.
"""

from __future__ import annotations

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


def translate_cat_val(text: str) -> str:
    """Convertix `text` de català oriental a valencià occidental: motor de
    regles + model de llengua (FLOR-760M) per als homògrafs.

    >>> translate_cat_val("Tinc vuitanta anys i la meva obra és francesa.")
    'Tinc huitanta anys i la meua obra és francesa.'
    >>> translate_cat_val("En un nou procés d'expansió.")
    "En un nou procés d'expansió."
    >>> translate_cat_val("Un cop acabada la reunió, marxem.")
    'Una vegada acabada la reunió, marxem.'
    """
    from .model_llengua import translate_cat_val_ml

    return translate_cat_val_ml(text)
