"""
traductor/llm/ -- Capes OPCIONALS de postprocessat amb LLM, una per
direcció (21/10/2026). El motor de regles tradueix i deixa uns "punts
ambigus" on la decisió depén del significat; el LLM només tria una
etiqueta d'una llista tancada per a cada punt. Mai escriu text lliure, i si
no respon o respon una cosa no vàlida es queda la sortida del motor.

- `cat_val.py`: "aquest" -> "este"/"eixe" i combinacions B4 ("l'hi"...).
- `val_cat.py`: mode verbal (indicatiu/subjuntiu) en 1a persona del
  singular i 3a del plural.
- `client.py`: client d'Ollama (sense dependències noves).
- `punts.py`: estructura comuna (`PuntAmbigu`, `resol`).

Sense Ollama el traductor funciona igual que sempre: `traductor.translate`
i `traductor.translate_cat_val` NO usen esta capa.
"""

from .cat_val import tradueix_cat_val
from .client import ClientLLM
from .val_cat import tradueix_val_cat

__all__ = ["ClientLLM", "tradueix_cat_val", "tradueix_val_cat"]
