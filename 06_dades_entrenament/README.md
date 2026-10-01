*[Llegeix-ho en castellà](README.es.md)*

# Dataset d'entrenament — preparació final abans del finetuning

Esta carpeta prepara les dades que de veres es donen a un model per a
fer-li finetuning: partix el corpus sintètic (AVL) en train/dev/test, i
normalitza el corpus real del BOE a un fitxer a banda per a poder avaluar
generalització fora de domini. No entrena res — només deixa els fitxers
llestos.

## Fitxers font necessaris (abans d'executar res)

| Fitxer | D'on ix | Què és |
|---|---|---|
| `dades/sintetico/corpus_sintetic_val_cat.jsonl` | `04_corpus_sintetic/genera_corpus_sintetico.py` (vore `04_corpus_sintetic/README.md`) | El corpus sintètic **amb metadades** (`doc_id`, `motius_sospita`...) — **NO** uses `parallel_val_cat.jsonl` per a açò, eixe export ja no té `doc_id` i no es pot agrupar per document. |
| `dades/boe/corpus_entrenamiento.jsonl` | `boe/exportar_entrenamiento.py` (vore `boe/README.md`) | El corpus real del BOE ja filtrat (268.735 parells en la versió actual). |
| `03_seleccio_de_model/benchmark_corpus.json` | Ja existix, no es toca | Les 150 frases amb traducció de referència humana — el test final "de veres", fora de tot açò. |

Si algun dels dos primers no existix encara, genera abans eixe corpus —
este script no descarrega ni tradueix res, només reorganitza el que ja
està generat.

## Com executar-ho

```bash
cd 06_dades_entrenament
python prepara_dataset.py
```

Amb les rutes per defecte assumix l'estructura de dalt (relativa a l'arrel
del repositori). Per a usar un altre fitxer (p. ex. quan acabe la
regeneració v2 del corpus sintètic, o si té un altre nom):

```bash
python prepara_dataset.py --sintetic ../dades/sintetico/corpus_sintetic_val_cat_v2.jsonl
```

Altres arguments:

| Argument | Per defecte | Què controla |
|---|---|---|
| `--boe` | `dades/boe/corpus_entrenamiento.jsonl` | Ruta al corpus BOE |
| `--sintetic` | `dades/sintetico/corpus_sintetic_val_cat.jsonl` | Ruta al corpus sintètic (amb metadades) |
| `--output-dir` | `dades/dataset_entrenamiento/` | On s'escriuen els fitxers d'eixida |
| `--seed` | `42` | Llavor del barajat — mateix seed, mateix split sempre (reproduïble) |
| `--prop-dev` | `0.05` (5%) | Proporció aproximada de frases del sintètic per a `dev.jsonl` |
| `--prop-test` | `0.05` (5%) | Proporció aproximada de frases del sintètic per a `test.jsonl` |

És determinista: rellançar-lo amb els mateixos fitxers d'entrada i el
mateix `--seed` reproduïx exactament el mateix split.

## Estat actual del split (última execució)

Corpus sintètic: **28.576 frases, 100% traduïdes amb gemma4:12b**
(confirmat comptant el camp `model` de cada registre — no és una mescla
de models). 341 sospitoses descartades → 28.235 frases netes.

| Fitxer | Frases |
|---|---|
| `train.jsonl` | 25.407 |
| `dev.jsonl` | 1.414 |
| `test.jsonl` | 1.414 |
| `boe_eval.jsonl` | 199.575 |

## Què genera, i per a què servix cada fitxer

```
dades/dataset_entrenamiento/
├── train.jsonl       # entrenar el model — NOMÉS corpus sintètic
├── dev.jsonl         # validar durant l'entrenament (early stopping, triar checkpoint) — NOMÉS sintètic
├── test.jsonl        # avaluació final dins del mateix domini (AVL) — NOMÉS sintètic
└── boe_eval.jsonl    # avaluació de generalització FORA de domini (legal/BOE) — mai s'entrena amb açò
```

### Nomenclatura: per què `dev` i no `val`

`dev` (development set) i `val`/`validation set` són sinònims exactes en
ML — el conjunt que s'usa **durant** l'entrenament per a vigilar
sobreajustament i triar el millor checkpoint (mai per a entrenar
directament, ni per al número final que es reporta — açò és `test.jsonl`).
Ací s'usa deliberadament **`dev`, mai `val`**, perquè `val` ja significa
alguna cosa molt concreta en tot este projecte: el camp amb el text en
**valencià** en cada registre (`{"val": "...", "cat": "..."}`). Un fitxer
anomenat `val.jsonl` les línies del qual tenen un camp també anomenat
`val` —però amb un significat totalment distint— seria una font de
confusió real, no només teòrica. Resum per a no perdre's:

| Paraula | Significat en este projecte |
|---|---|
| `val` (camp dins d'un JSON) | Text en **valencià** |
| `cat` (camp dins d'un JSON) | Text en **català** |
| `dev` (nom de fitxer/split) | Conjunt de **validació** durant l'entrenament |
| `test` (nom de fitxer/split) | Conjunt d'avaluació final, mateix domini que `train` |
| `boe_eval` (nom de fitxer/split) | Avaluació de generalització fora de domini |

Cada línia és un JSON amb el mateix esquema en els quatre fitxers:

```json
{"val": "frase en valencià", "cat": "frase en català", "origen": "avl_sintetic", "doc_id": "...", "similitud": null}
```

(`similitud` només té valor real en `boe_eval.jsonl` — ve de l'alineació
per Bleualign del corpus BOE, vore `boe/README.md`; al sintètic sempre
és `null`.)

**Per què el corpus real (BOE) NO es mescla amb l'entrenament**: la
decisió del projecte és entrenar només amb el corpus sintètic. El BOE
normalitzat al mateix esquema servix, a banda, per a comprovar si el
model generalitza a un registre real (legal) que mai ha vist en
entrenament — si el model només funciona bé en `test.jsonl` (mateix
domini que `train.jsonl`) però s'enfonsa en `boe_eval.jsonl`, és un
senyal de sobreajustament al registre institucional de l'AVL.

`boe_eval.jsonl` té ~200.000 frases — massa per a avaluar en cada època
d'entrenament. Per a comprovacions ràpides, mostreja unes 3.000-5.000 a
l'atzar; guarda l'avaluació sobre el fitxer complet per al final.

## Decisions de disseny (per què està fet així)

- **Split per document, no per frase solta**: totes les frases d'un
  mateix `doc_id` cauen sempre en el mateix split. Si es partira frase a
  frase, frases molt semblants del mateix document (mateix article de
  llei, mateix glossari) podrien caure una en train i una altra en test
  — el model "veuria" en entrenament vocabulari/estil quasi idèntic al
  de test, i infla la mètrica de forma artificial.
- **Es descarten les frases sospitoses del sintètic** (`motius_sospita`
  no buit) abans de res — mateix criteri que usa
  `04_corpus_sintetic/genera_corpus_sintetico.py::exporta_nets()` per a
  produir `parallel_val_cat.jsonl`, però aplicat ací sobre el fitxer amb
  metadades per a no perdre el `doc_id`.
- **Deduplicació exacta dins de cada corpus** (abans del split): el BOE
  en concret té molta redundància real (fórmules legals fixes repetides
  entre documents — en l'última execució, 268.735 → 199.575 després de
  dedup, un 26%). Sense deduplicar abans de partir, un duplicat exacte
  podria acabar a la vegada en dos splits distints.
- **`boe_eval.jsonl` es neteja de qualsevol frase idèntica a alguna del
  `train.jsonl` sintètic** — si per casualitat coincidira text exacte
  entre els dos corpus, eixa frase ja no seria una prova vàlida de
  "domini no vist".

## Pròxim pas (fora de l'abast d'esta carpeta)

Amb `train.jsonl`/`dev.jsonl` llestos, el pròxim bloc és el finetuning
en si — candidats avaluats: NLLB-200 (distilled-600M/1.3B, primer
experiment recomanat), SalamandraTA-7b-instruct amb LoRA (el de més
recorregut esperat, ja "sap" traduir variants catalanes de fàbrica),
LoRA sobre qwen2.5:7b/gemma3:4b per a no dependre del prompt llarg de
regles en producció. Vore la conversa/decisió del projecte per al
detall de per què cada un.
