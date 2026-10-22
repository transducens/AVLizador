# `traductor/llm/` — capa de postprocessat amb LLM (val→cat)

*[Léelo en castellano](README.es.md)*

> **22/10/2026 — nova capa cat→val (`cat_val.py`)**, també opcional:
> homògrafs de la **mateixa categoria** que spaCy no pot resoldre, trets del
> lèxic (`homonimia_lexica` amb la forma ambigua al costat català): hui
> "calces" (bragues / calces de pantaló), "gandula" i "gandules" (hamaca /
> dona gandula). El motor tradueix sempre; el LLM només respon `si` (es
> queda la traducció) o `no` (es deixa la paraula catalana). Una frase
> sense eixes paraules no crida el model. Prova en local:
> `python -m traductor.llm.prova_cat_val "frase"` (`--sense-llm` per a vore
> els punts sense Ollama, `--model`, `--verbose`). Sense avaluar encara: als
> corpus només hi ha 3 casos.
>
> El de baix descriu la capa de val→cat (congelada).

Capa **opcional** només per a valencià→català. Des del 21/10/2026 està
**congelada**: funciona i millora el motor, pero no es continua millorant.
`traductor.translate()` i `traductor.translate_cat_val()` **no la usen**;
les eines que s'entreguen (traductor cat→val i IPD, només CPU) no la
necessiten.

- `val_cat.py`: mode verbal (indicatiu / subjuntiu / cap) en 3a persona
  del plural i 1a del singular. Prompt copiat literalment de la via C
  original (129/151 amb `qwen3:8b`).
- `client.py`, `punts.py`: client d'Ollama i estructura comuna.

**Resultats en Abaco (`qwen3:8b`, 21/10/2026)**: benchmark de 151, 100 →
109 frases exactes; BOE (2.000 línies), encert en els punts de mode verbal
20% → 71% (229 guanys, 17 pèrdues).

**Errors catalogats per a reprendre-la** (detall i exemples a
`README.es.md`): relatius normatius tractats com a reals (70 al BOE) i a
l'inrevés (11); 1a persona amb "indicatiu" sense subjecte "jo", que genera
formes agramaticals com "realitzo" (18); "quan" de condició futura (6);
"si" + subjuntiu (2); frases llargues (17). Els errors de 1a persona i de
"si" són regles gramaticals que es poden corregir sense el model.

La capa de cat→val es va retirar el 21/10/2026: avaluada en Abaco, no
canviava cap frase del 151 ni del BOE ("aquest" empitjorava i B4 no hi
apareix). Vore `README.es.md`.
