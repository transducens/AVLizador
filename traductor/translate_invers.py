"""
translate_invers.py -- Punt d'entrada públic del traductor en sentit
invers: `translate_cat_val(text) -> str`. Mateix patró que
`translate.py` (orquestra `RuleEngineInvers`, reutilitzat entre crides)
-- vore eixe fitxer per al raonament complet de per què existix esta
indirecció.
"""

from __future__ import annotations

from .rules.cat_val.engine import RuleEngineInvers

_ENGINE_INVERS: RuleEngineInvers | None = None


def translate_cat_val(text: str) -> str:
    """Convertix `text` de català oriental a valencià occidental.

    >>> translate_cat_val("Tinc vuitanta anys i la meva obra és francesa.")
    'Tinc huitanta anys i la meua obra és francesa.'
    """
    global _ENGINE_INVERS
    if _ENGINE_INVERS is None:
        _ENGINE_INVERS = RuleEngineInvers()
    return _ENGINE_INVERS.translate(text)
