# `traductor/model_llengua/` — homògrafs cat→val amb un model de llengua

Postprocessat **opcional** (23/10/2026) per a les paraules catalanes
ambigües que el motor de regles no pot resoldre a soles. `translate_cat_val`
no canvia i no necessita res d'açò (ni `torch` ni `transformers`).

## Què resol

Els punts ixen del lèxic (`traductor/data/lexic_general.json`), sense cap
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
canvia el motor si guanya per més de 5; `resoluble` → spaCy dins del motor.
El model es va descartar primer als irresolubles, però la causa era un
error de dades (E0592 "hamaces"; el plural és "hamaques", corregit amb
permís de l'usuari). Criteri per defecte: FLOR-760M, PMI 0,5, suma, marge
5, concordança `variants`. Resultats: benchmark combinat motor 190/253 →
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
token), `marge` (als homògrafs el model només canvia el motor si guanya
per més de `marge` punts) i `concordanca` (`motor` o `variants`,
experimental: formes de l'altre gènere de les dos paraules d'abans, i el
model tria).

Models: `projecte-aina/FLOR-760M` per defecte (1,5 GB, CPU) i
`BSC-LT/salamandra-2b` (4,5 GB).

## Fitxers

`punts.py` (punts i candidats, sense model), `puntuador.py`
(`ModelLlengua`), `__init__.py` (`tradueix_cat_val_ml`),
`frases_homografs.json` (frases catalanes amb el sentit esperat),
`genera_benchmark.py` (crea `benchmark_homografs_cat_val.json` amb el
motor; **les referències s'han de revisar a mà**) i `avalua.py` (prova
tots els criteris amb cada model).

## Executar (des de l'arrel del repo)

```bash
python -m traductor.model_llengua.genera_benchmark        # no sobreescriu sense --sobreescriu
python -m traductor.model_llengua.avalua
python -m traductor.model_llengua.avalua --models projecte-aina/FLOR-760M BSC-LT/salamandra-2b
```

Resultats a `pipeline/03_seleccio_de_model/resultats/benchmark_homografs_ml_<model>_<data>.json`.
