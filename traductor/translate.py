"""
translate.py -- Punt d'entrada públic del traductor: `translate(text) -> str`.

Orquestra el pipeline complet delegant en RuleEngine (rules/engine.py), amb
un únic RuleEngine reutilitzat entre crides (`_ENGINE`, carregat de manera
peresosa la primera vegada que cal). Això evita rellegir i re-indexar tots
els fitxers de dades de `traductor/data/` (lèxics, conjugacions,
excepcions...) en cada crida a translate() -- important si s'usa este
mòdul per a traduir moltes frases seguides (p.ex. des de l'adaptador
d'evalua_models.py o des de cli.py amb un fitxer sencer).

Esta indirecció (translate() en lloc d'exposar RuleEngine directament)
existix perquè cap altre mòdul (CLI, adaptador del benchmark, un futur
servei) hauria d'importar RuleEngine ell mateix -- si algun dia canvia com
s'orquesten les regles, només cal tocar este fitxer.
"""

from __future__ import annotations

from .rules.engine import RuleEngine

_ENGINE: RuleEngine | None = None


def translate(text: str) -> str:
    """Convertix `text` de valencià occidental a català oriental.

    >>> translate("Tinc huitanta anys i la meua obra és francesa.")
    'Tinc vuitanta anys i la meva obra és francesa.'
    """
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = RuleEngine()
    return _ENGINE.translate(text)
