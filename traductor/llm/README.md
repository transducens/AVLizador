# `traductor/llm/` — capes de postprocessat amb LLM (21/10/2026)

*[Léelo en castellano](README.es.md)*

Dos capes **opcionals i independents**, una per direcció. El motor de
regles tradueix i deixa uns **punts ambigus** on la decisió depén del
significat. El LLM només **tria una etiqueta d'una llista tancada** per a
cada punt: mai escriu text lliure. Si no respon o respon una cosa que no
és a la llista, es queda la sortida del motor.

`traductor.translate()` i `traductor.translate_cat_val()` **no usen** esta
capa: sense Ollama tot funciona igual que abans.

- **cat→val** (`cat_val.py`): "aquest" → "este"/"eixe" (per defecte
  "este") i B4 "l'hi", "la hi", "les hi", "els hi" i enclítics → `datiu`
  (li'l, li la…), `neutre` (li ho), `plural` (los el) o `lloc` (igual, per
  defecte).
- **val→cat** (`val_cat.py`): mode verbal en 1a persona del singular i 3a
  del plural (`indicatiu` / `subjuntiu` / `cap`, per defecte `cap`). És la
  "via C" de `pipeline/08_traduccio_corpus/postprocessat_llm/` portada dins
  de `traductor/` amb les dades de `traductor/data/`.

Avaluació: `pipeline/08_traduccio_corpus/postprocessat_llm/avalua_capa_llm.py`
i, en Abaco, `slurm/avalua_capa_llm.sh`. Detall complet a `README.es.md`.
