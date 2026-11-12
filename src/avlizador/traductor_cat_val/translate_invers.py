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
doctests de les regles. Des del 12/11/2026, `translate_cat_val(text,
model="kenlm")` usa KenLM en lloc de FLOR (opció complementària).
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


MODELS = ("flor", "kenlm")


def translate_cat_val(text: str, model: str = "flor") -> str:
    """Convertix `text` de català oriental a valencià occidental: motor de
    regles + model de llengua per als homògrafs.

    `model` (12/11/2026): "flor" (FLOR-760M, per defecte) o "kenlm" (KenLM +
    classificador de sentit de "cop"; més lleuger i sense torch, vore
    `model_llengua/kenlm.py`). Amb "kenlm" cal el paquet `kenlm` i els
    fitxers en `AVLIZADOR_KENLM_DIR`: si falten, `FaltaKenLM` (no torna al
    motor sol en silenci, perquè s'ha demanat expressament).

    >>> translate_cat_val("Tinc vuitanta anys i la meva obra és francesa.")
    'Tinc huitanta anys i la meua obra és francesa.'
    >>> translate_cat_val("En un nou procés d'expansió.")
    "En un nou procés d'expansió."
    >>> translate_cat_val("Un cop acabada la reunió, marxem.")
    'Una vegada acabada la reunió, marxem.'

    Sense `torch` o `transformers` instal·lats (paquet sense l'extra
    `[ml]`), usa el motor sol i avisa una vegada amb
    `AvisSenseModelLlengua` (decisió del 30/10/2026).

    >>> translate_cat_val("Hola.", model="gpt")
    Traceback (most recent call last):
    ...
    ValueError: model desconegut: 'gpt' (opcions: flor, kenlm)
    """
    if model not in MODELS:
        raise ValueError(f"model desconegut: {model!r} (opcions: {', '.join(MODELS)})")
    if model == "kenlm":
        from .model_llengua import translate_cat_val_kenlm

        return translate_cat_val_kenlm(text)
    if not model_llengua_disponible():
        _avisa_sense_model()
        return translate_cat_val_motor(text)

    from .model_llengua import translate_cat_val_ml

    return translate_cat_val_ml(text)


class AvisSenseModelLlengua(UserWarning):
    """Avís: falta l'extra `[ml]` i `translate_cat_val` usa el motor sol."""


_AVISAT = False


def model_llengua_disponible() -> bool:
    """True si estan instal·lats `torch` i `transformers` (extra `[ml]`).
    No els importa (importar `torch` tarda uns segons)."""
    from importlib.util import find_spec

    return find_spec("torch") is not None and find_spec("transformers") is not None


def _avisa_sense_model() -> None:
    global _AVISAT
    if not _AVISAT:
        warnings.warn(
            "No estan instal·lats 'torch' i 'transformers': s'usa el motor de "
            "regles sense el model de llengua (FLOR-760M), que resol els "
            "homògrafs ('cop', 'nou', 'manca'...). Per al sistema complet: "
            'pip install "avlizador[ml]".',
            AvisSenseModelLlengua,
            stacklevel=3,
        )
        _AVISAT = True
