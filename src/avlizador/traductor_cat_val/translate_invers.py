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
FLOR-760M, que continua disponible amb `model="flor"`.
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


MODELS = ("kenlm", "flor")
# Model per defecte (13/11/2026, decisió de l'usuari): KenLM + classificador
# de sentit. Iguala o millora FLOR en tots els benchmarks menys una frase del
# 151 i una de gplsi, és unes 8.000 vegades més ràpid i no necessita torch.
# Xifres i motius: `documentacio/resultats_model_llengua_kenlm.md`.
MODEL_PER_DEFECTE = "kenlm"


def translate_cat_val(text: str, model: str | None = None) -> str:
    """Convertix `text` de català oriental a valencià occidental: motor de
    regles + model de llengua per als homògrafs.

    `model`:
    - `None` (per defecte, des del 13/11/2026): KenLM + classificador de
      sentit (`model_llengua/kenlm.py`, `sentit.py`). Cal el paquet `kenlm`
      (extra `[kenlm]`) i els fitxers en `AVLIZADOR_KENLM_DIR`. Si falta
      alguna cosa, usa el motor sol i avisa una vegada
      (`AvisSenseModelLlengua`).
    - `"kenlm"`: el mateix, però si falta alguna cosa llança `FaltaKenLM`
      (s'ha demanat expressament: no torna al motor en silenci).
    - `"flor"`: FLOR-760M (el model per defecte fins al 12/11/2026; extra
      `[ml]`: `torch` i `transformers`). Sense l'extra, motor sol i avís.

    >>> translate_cat_val("Tinc vuitanta anys i la meva obra és francesa.", model="flor")
    'Tinc huitanta anys i la meua obra és francesa.'
    >>> translate_cat_val("En un nou procés d'expansió.", model="flor")
    "En un nou procés d'expansió."
    >>> translate_cat_val("Un cop acabada la reunió, marxem.", model="flor")
    'Una vegada acabada la reunió, marxem.'

    >>> translate_cat_val("Hola.", model="gpt")
    Traceback (most recent call last):
    ...
    ValueError: model desconegut: 'gpt' (opcions: kenlm, flor)
    """
    if model is not None and model not in MODELS:
        raise ValueError(f"model desconegut: {model!r} (opcions: {', '.join(MODELS)})")
    if model is None:
        from .model_llengua.kenlm import kenlm_disponible

        if not kenlm_disponible():
            _avisa_sense_model("kenlm")
            return translate_cat_val_motor(text)
        model = MODEL_PER_DEFECTE
    if model == "kenlm":
        from .model_llengua import translate_cat_val_kenlm

        return translate_cat_val_kenlm(text)
    if not model_llengua_disponible():
        _avisa_sense_model("flor")
        return translate_cat_val_motor(text)

    from .model_llengua import translate_cat_val_ml

    return translate_cat_val_ml(text)


class AvisSenseModelLlengua(UserWarning):
    """Avís: falta el model de llengua i `translate_cat_val` usa el motor sol."""


_AVISAT = False


def model_llengua_disponible() -> bool:
    """True si estan instal·lats `torch` i `transformers` (extra `[ml]`, per
    a FLOR). No els importa (importar `torch` tarda uns segons)."""
    from importlib.util import find_spec

    return find_spec("torch") is not None and find_spec("transformers") is not None


_COM_INSTALLAR = {
    "kenlm": ("KenLM (el paquet 'kenlm' o els fitxers del model en AVLIZADOR_KENLM_DIR)",
              'pip install "avlizador[kenlm]" (Linux o Docker) i defineix AVLIZADOR_KENLM_DIR'),
    "flor": ("FLOR-760M ('torch' i 'transformers')", 'pip install "avlizador[ml]"'),
}


def _avisa_sense_model(model: str = "kenlm") -> None:
    global _AVISAT
    if not _AVISAT:
        que, com = _COM_INSTALLAR[model]
        warnings.warn(
            f"Falta el model de llengua {que}: s'usa el motor de regles sol, que "
            "no resol els homògrafs ('cop', 'nou', 'manca'...). Per al sistema "
            f"complet: {com}.",
            AvisSenseModelLlengua,
            stacklevel=3,
        )
        _AVISAT = True
