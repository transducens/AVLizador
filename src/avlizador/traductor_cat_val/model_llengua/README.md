# `avlizador.traductor_cat_val.model_llengua` — homògrafs cat→val amb un model de llengua

Postprocessat (23/10/2026) per a les paraules catalanes ambigües que el
motor de regles no pot resoldre a soles. Des del 29/10/2026 forma part
del **sistema principal** (`translate_cat_val`); cal l'extra `[ml]`
(`torch` + `transformers`). Sense ell, `translate_cat_val` usa el motor
sol i avisa una vegada (`AvisSenseModelLlengua`).

## Què resol

Els punts ixen del lèxic (`traductor_cat_val/data/lexic_general.json`), sense cap
paraula escrita al codi:

| tipus | d'on ix | exemple | què fa hui el motor |
|---|---|---|---|
| `colisio` | `problema: "colision_homonima"` | cop → colp / vegada; cops → colps / vegades | no tradueix (dos candidats, cap canònic) |
| `irresoluble` | `homonimia_lexica`, lectures de la mateixa categoria | calces → bragues / calces; gandula → hamaca / gandula | tradueix sempre |
| `resoluble` | `homonimia_lexica` que spaCy separa | nou → anou / nou; manca → carència / manca | decidix spaCy |

**Sistema final (decisió de l'usuari, 23/10/2026)**: `colisio` ("cop",
"cops") → model de llengua; `irresoluble` ("calces", "gandula/es") → (1)
spaCy, si dona una categoria que només té l'altra lectura dels `lemas`
("molt gandula": ADJ → no es tradueix), i (2) si no, el model, que només
canvia el motor si guanya per més de 5 (des del 05/11/2026, marge 2 amb la catalana per defecte); `resoluble` → spaCy dins del motor.
El model es va descartar primer als irresolubles, però la causa era un
error de dades (E0592 "hamaces"; el plural és "hamaques", corregit amb
permís de l'usuari). Criteri per defecte: FLOR-760M, PMI 0,5, suma, marge
2 amb la paraula catalana per defecte (`per_defecte="catala"`, des del
05/11/2026: només es tradueix si FLOR veu la traducció més probable per
més de 2 punts; si no, es queda la paraula catalana; abans, marge 5 a
favor del motor; vore la secció "Margen 2 con la catalana por defecto" del
README.es.md), concordança `variants`. Mesurat el 06/11/2026 frente al
marge 5: 151 + homògrafs 233 → 218/253, homògrafs v2 124 → 95/160 (les
frases que deixen la catalana, 42 → 57/59; les que demanen la
valenciana, 82 → 38/101), manual 228/458 sense canvis. Resultats: benchmark combinat motor 190/253 →
sistema 227/253 (151 sense cap canvi, colisio 0 → 31/33, irresoluble 12 →
18/24; "calces" no la separa); BOE ampli 1.206/2.000. La
funció és `translate_cat_val_ml(text)`; `evalua_models.py --model
traductor_ml --direccio cat-val` l'avalua sobre
`pipeline/03_seleccio_de_model/benchmark_sistema_final_cat_val.json` (el de
151 + els homògrafs, `construeix_benchmark_sistema_final.py`).

## Com funciona

1. El motor tradueix la frase.
2. Per a cada punt es construïxen les frases valencianes **completes**, una
   per candidat, sobre una "base neutra" (la frase del motor amb la paraula
   ambigua sense tocar) i amb el determinant concordat:
   "**Una vegada** acabada la reunió…" / "**Un colp** acabada la reunió…".
3. El model de llengua puntua cada frase (log-probabilitat) i guanya la
   més probable. El model no genera text ni respon preguntes.

Opcions del criteri (`Criteri`), per a provar amb `avalua.py`: `lam` (PMI,
es resta `lam` × log P(candidat sol)), `norma` (`suma` / `mitjana` per
token), `marge` i `per_defecte` (als homògrafs la forma per defecte,
`catala` o `motor`, només canvia si l'altra guanya per més de `marge`
punts) i `concordanca` (`motor` o `variants`,
experimental: formes de l'altre gènere de les dos paraules d'abans, i el
model tria).

**Des del 29/10/2026 `avlizador.translate_cat_val` és sempre este sistema**
(motor + FLOR-760M); el motor sol és `translate_cat_val_motor`. Eixe
mateix dia els resolubles també passen pel model i "nou", "manca",
"recuita"… són irresolubles (els `lemas` diuen que l'adjectiu també fa de
nom).

**Paràgraf valencià davant (03/11/2026)**: FLOR preferix la forma que ha
vist més vegades, quasi sempre la catalana ("vegada" davant de "colp",
"rentadora" davant de "llavadora"). Des del 03/11 cada frase es puntua
com a continuació d'un paràgraf curt en valencià
(`puntuador.CONTEXT_PER_DEFECTE`; `ModelLlengua(context=None)` el lleva).
El paràgraf passa pel model una sola vegada (`past_key_values`): no costa
temps. 151 + homògrafs 226 → **233/253**, homògrafs v2 111 → **122/160**,
gplsi 1.544 → 1.547; manual, 151 i BOE sense canvis. Perd "manca" verb
(→ "carència") en 2 frases més. Proves (paràgrafs, freqüències, LoRA) en
`pipeline/03_seleccio_de_model/model_llengua/sesgo/README.md`.

**Concordança amb el determinant (03/11/2026)**: si spaCy dona ADJ a la
paraula ambigua i el seu gènere no és el del determinant d'abans ("una
nou", "les nous"), la capa d'spaCy no decidix i passa al model
(`punts.decisio_spacy`). Amb NUM no (un numeral fa de nom amb qualsevol
article: "la nou" = la jugadora del dorsal nou). Homògrafs v2 122 → 124,
manual 227 → 228, homògrafs 233 igual. Detall en
`pipeline/03_seleccio_de_model/traces/README.md`.

Models: `projecte-aina/FLOR-760M` per defecte (1,5 GB, CPU) i
`BSC-LT/salamandra-2b` (4,5 GB).

Baseline del 29/10/2026 amb 9 models xicotets (FLOR, salamandra, EuroLLM,
bloom, Qwen2.5 i Qwen3): **FLOR-760M continua sent el millor** (227/253 al
combinat; el següent, salamandra-2b, 222) i el més ràpid. Els models que
no coneixen el valencià trien "vegada" quasi sempre. Detall a
`documentacio/resultats_baseline_models_llengua.md`; pendent FLOR-1.3B.

## Fitxers

`punts.py` (punts i candidats, sense model), `puntuador.py`
(`ModelLlengua`), `__init__.py` (`tradueix_cat_val_ml`); fora del paquet, en
`pipeline/03_seleccio_de_model/model_llengua/`: `frases_homografs.json` (frases catalanes amb el sentit esperat),
`genera_benchmark.py` (crea `benchmark_homografs_cat_val.json` amb el
motor; **les referències s'han de revisar a mà**) i `avalua.py` (prova
tots els criteris amb cada model).

## Executar (des de l'arrel del repo)

```bash
python pipeline/03_seleccio_de_model/model_llengua/genera_benchmark.py        # no sobreescriu sense --sobreescriu
python pipeline/03_seleccio_de_model/model_llengua/avalua.py
python pipeline/03_seleccio_de_model/model_llengua/avalua.py --models projecte-aina/FLOR-760M BSC-LT/salamandra-2b
```

Resultats a `pipeline/03_seleccio_de_model/resultats/benchmark_homografs_ml_<model>_<data>.json`.
