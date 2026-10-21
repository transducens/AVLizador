"""
traductor/llm/ -- Capa OPCIONAL de postprocessat amb LLM, NOMÉS per a
valencià -> català (mode verbal). El motor de regles tradueix i deixa uns
"punts ambigus" on la decisió depén del significat; el LLM només tria una
etiqueta d'una llista tancada per a cada punt. Mai escriu text lliure, i si
no respon o respon una cosa no vàlida es queda la sortida del motor.

- `val_cat.py`: mode verbal (indicatiu/subjuntiu) en 1a persona del
  singular i 3a del plural. CONGELADA el 21/10/2026: funciona i millora el
  motor, pero no es continua millorant; els errors coneguts estan
  documentats a `README.es.md`.
- `client.py`: client d'Ollama (sense dependències noves).
- `punts.py`: estructura comuna (`PuntAmbigu`, `resol`).

La capa per a català -> valencià es va RETIRAR el 21/10/2026: avaluada en
Abaco amb qwen3:8b, no canviava cap frase del benchmark de 151 ni del BOE
(vore `README.es.md`). L'eina que s'entrega (cat->val per a la
Conselleria, només CPU) no necessita cap LLM.

Sense Ollama el traductor funciona igual que sempre: `traductor.translate`
i `traductor.translate_cat_val` NO usen esta capa.
"""

from .client import ClientLLM
from .val_cat import tradueix_val_cat

__all__ = ["ClientLLM", "tradueix_val_cat"]
