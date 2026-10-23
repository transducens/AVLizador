*[Llegeix-ho en castellà](README.es.md)*

# Traductor dialectal valencià ↔ català oriental

Projecte per a construir un traductor automàtic entre valencià occidental
(norma AVL/GVA) i català oriental (norma IEC). L'objectiu no és la
traducció en si: el valencià és una llengua de recursos escassos, mentre
que el català oriental en té molts més — un traductor dialectal fiable
actua com a **pont** per a aprofitar eixos recursos en tasques que en
valencià serien inviables per falta de dades (p. ex. alinear anglés↔valencià
passant pel català).

## Què s'entrega (estat del 23/10/2026)

Dos eines, per a la Conselleria, en equips amb pocs recursos i només CPU.
La resta del repositori és la infraestructura que les construïx i les
valida.

1. **El traductor català → valencià** ([`traductor/`](traductor/), la
   direcció prioritària):
   - el **motor de regles** (`translate_cat_val`): diccionaris del
     proveïdor + spaCy, determinista, sense GPU ni LLM;
   - una **capa opcional** ([`traductor/model_llengua/`](traductor/model_llengua/),
     `translate_cat_val_ml`): un model de llengua menut (FLOR-760M) que
     només decidix unes poques paraules ambigües del lèxic ("cop" → colp o
     vegada; "gandula" → hamaca o gandula), triant entre les frases que
     construïx el motor.
2. **L'Índex de Puresa Dialectal (IPD)**
   ([`pipeline/09_index_puresa_dialectal/`](pipeline/09_index_puresa_dialectal/)).

L'estat i l'estructura actuals del traductor són al principi de
[`traductor/README.md`](traductor/README.md). La direcció valencià → català
existix ([`traductor/rules/val_cat/`](traductor/rules/val_cat/)) però està
aparcada des del 20/10/2026.

## Comença per ací

**[`documentacio/metodologia_i_resultats.md`](documentacio/metodologia_i_resultats.md)**
— la història completa del projecte en un sol document: d'on ix el text,
com es van decidir les regles, quins models es van comparar i amb quins
resultats, quins bugs es van trobar i com es van corregir, limitacions
conegudes. Cada carpeta d'etapa té a més el seu propi README amb el detall
d'ús d'eixa etapa en concret.

## Estructura del repositori

**Reestructurat el 14/10/2026**: les 9 etapes numerades viuen ara dins de
[`pipeline/`](pipeline/), separades del producte real (`traductor/`) i de
les dades (`dades/`). `boe/` (abans solt en l'arrel, sense número) ara és
`pipeline/05_corpus_boe/` — tanca el forat que hi havia en la numeració
(abans no existia cap "05") sense tocar cap de les altres 8 carpetes.

```
traductor/              # el motor real -- el PRODUCTE, no una etapa
  rules/cat_val/          # motor català -> valencià (el que s'entrega)
  rules/val_cat/          # motor valencià -> català (aparcat)
  model_llengua/          # capa opcional cat->val: homògrafs amb un model de llengua
  llm/                    # capes de LLM per preguntes (aparcades)
  data/                   # només les còpies dels dos diccionaris del proveïdor
pipeline/
  01_extraccio_i_neteja/
  02_regles_dialectals/
  03_seleccio_de_model/
  04_corpus_sintetic/
  05_corpus_boe/         # abans "boe/" solt en l'arrel, sense número
  06_dades_entrenament/
  07_entrenament_de_models/
  08_traduccio_corpus/
  09_index_puresa_dialectal/
dades/                   # transversal, el consumeixen diverses etapes
documentacio/            # transversal
```

| Carpeta | Què és |
|---|---|
| [`traductor/`](traductor/) | El motor de regles determinista — el producte del projecte, per això viu fora de `pipeline/`; amb una capa opcional de model de llengua per als homògrafs (`model_llengua/`). Veure `traductor/README.md` |
| [`pipeline/01_extraccio_i_neteja/`](pipeline/01_extraccio_i_neteja/) | Etapa 1 — scraping de la web de l'AVL i neteja/classificació dialectal |
| [`pipeline/02_regles_dialectals/`](pipeline/02_regles_dialectals/) | Etapa 2 — regles dialectals i lèxic diferencial valencià↔català |
| [`pipeline/03_seleccio_de_model/`](pipeline/03_seleccio_de_model/) | Etapa 3 — benchmark i selecció del model de traducció; hui, sobretot, `evalua_models.py`, amb què es mesuren el motor i el sistema final |
| [`pipeline/04_corpus_sintetic/`](pipeline/04_corpus_sintetic/) | Etapa 4 — generació del corpus sintètic complet |
| [`pipeline/05_corpus_boe/`](pipeline/05_corpus_boe/) | Etapa 5 — scripts del corpus real i alineat del BOE (abans `boe/`, sense número) |
| [`pipeline/06_dades_entrenament/`](pipeline/06_dades_entrenament/) | Etapa 6 — prepara el dataset final (train/dev/test) per al finetuning |
| [`pipeline/07_entrenament_de_models/`](pipeline/07_entrenament_de_models/) | Etapa 7 — finetuning, baselines i comparació de models |
| [`pipeline/08_traduccio_corpus/`](pipeline/08_traduccio_corpus/) | Etapa 8 — aplica el motor de regles a un corpus complet (no només al benchmark); postprocessat amb LLM dels casos ambigus |
| [`pipeline/09_index_puresa_dialectal/`](pipeline/09_index_puresa_dialectal/) | Etapa 9 — Índex de Puresa Dialectal (IPD): mètrica reutilitzable per a mesurar quin percentatge d'un text és occidental vs. oriental, basada en l'índex de parells de `traductor/` |
| [`documentacio/`](documentacio/) | La metodologia completa del projecte |

**Dades** (tot agrupat en [`dades/`](dades/), separat del codi):

| Carpeta | Què és |
|---|---|
| `dades/avl/` | Eixida crua i neta del scraping de l'AVL (raw/clean/final) — entrada de l'etapa 4 |
| `dades/boe/` | Corpus real del BOE: PDFs descarregats, extracció i alineació (`corpus_entrenamiento.jsonl`); a `dades/boe/benchmarks/`, els benchmarks "BOE dialectal" estricte i ampli |
| `dades/gplsi_ca_va_alignment_test/` | Dataset públic gplsi (1.958 parells català/valencià, CC BY 4.0), usat com a benchmark |
| `dades/sintetic/` | El corpus sintètic generat (etapa 4): `corpus_sintetic_val_cat.jsonl`, `parallel_val_cat.jsonl`... |
| `dades/dataset_entrenament/` | El dataset final ja partit (etapa 6): `train.jsonl`/`dev.jsonl`/`test.jsonl`/`boe_eval.jsonl` |

## Com es relacionen les carpetes

Les etapes 1-4 i 6 són codi actiu (scraping, regles, benchmark, generació
del corpus, split final); cada una llig/escriu en la seua subcarpeta
corresponent de `dades/`. L'etapa 7 consumeix l'eixida de la 6 per a
entrenar/avaluar models. `traductor/` és un paquet Python independent que
viu en l'arrel, fora de `pipeline/`, perquè s'importa com a mòdul des
d'altres parts del projecte i perquè no és una etapa d'un sol ús sinó el
producte que totes les etapes alimenten (a més, un mòdul Python no pot
començar per un dígit). `pipeline/05_corpus_boe/` és una font de dades
paral·lela i independent del pipeline AVL — el seu codi viu ahí, les
seues dades en `dades/boe/`, i no es mescla amb el corpus sintètic en
l'entrenament: s'usa per a avaluar generalització fora de domini (veure
`pipeline/06_dades_entrenament/README.md`).

## Nota si treballes també en un clúster remot

Esta estructura de carpetes es va reorganitzar localment (última vegada,
14/10/2026: les etapes numerades es van moure dins de `pipeline/` i
`boe/` va passar a ser `pipeline/05_corpus_boe/`) — si tens una còpia en
un altre lloc (p. ex. un clúster SLURM) sincronitzada a mà amb
`scp`/`rsync`, hauràs de replicar ahí els mateixos renombraments abans de
la teua pròxima sincronització, o les rutes no coincidiran. L'estructura
plana d'Abaco (`~/scrapeo/postprocesado_llm/`) es manté expressament
independent d'este canvi — veure `pipeline/08_traduccio_corpus/postprocessat_llm/README.md`.
