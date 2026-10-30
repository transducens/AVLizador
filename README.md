*[Léelo en castellano](README.es.md)*

# AVLizador: traductor dialectal català → valencià i Grau Dialectal

AVLizador convertix text en **català oriental** (norma de l'IEC) a
**valencià occidental** (norma de l'AVL) i mesura quant de valencià o de
català té un text. No tradueix entre llengües: canvia només el que és
dialectal (lèxic, conjugacions, demostratius, possessius, numerals...).

S'instal·la com un paquet de Python, `avlizador`, amb dues eines:

| Eina | Què fa | Importació |
|---|---|---|
| **Traductor català → valencià** | Motor de regles amb els diccionaris del projecte i spaCy, més un model de llengua menut (FLOR-760M) que resol les paraules ambigües ("cop" → *colp* o *vegada*, "nou" → *nou* o *anou*) | `avlizador.traductor_cat_val` |
| **Grau Dialectal** (GD, GDV, GDC) | Índexs de 0 a 1 que diuen si un text és valencià o català | `avlizador.grau_dialectal` |

Funciona **només amb CPU**, sense GPU ni serveis externs: està pensat per
a equips amb pocs recursos.

## Instal·lació

Cal Python 3.10 o posterior. Des d'una còpia del repositori:

```bash
pip install ".[ml]" --extra-index-url https://download.pytorch.org/whl/cpu
```

- `[ml]` instal·la `torch` (versió CPU) i `transformers` per al model de
  llengua FLOR-760M, que es baixa de Hugging Face la primera vegada que
  s'usa (1,5 GB; es guarda en la carpeta de `HF_HOME`). És la instal·lació
  recomanada.
- Sense `[ml]` (`pip install .`) funciona només el motor de regles: el
  traductor l'usa i avisa una vegada que falta el model
  (`AvisSenseModelLlengua`).
- El model català de spaCy (`ca_core_news_md`) s'instal·la sol.
- `[avaluacio]` afig `sacrebleu` per a avaluar amb els benchmarks; `[dev]`,
  `pytest`.

## Ús

En Python:

```python
from avlizador import translate_cat_val, calcula_gd, calcula_gdv, calcula_gdc

translate_cat_val("Aquest noi necessita ajuda. Un cop acabada la reunió, marxem.")
# 'Este xic necessita ajuda. Una vegada acabada la reunió, marxem.'

calcula_gd("Este xiquet vol vindre hui.")["gd"]     # 1.0: valencià
calcula_gdv("Este xiquet vol vindre hui.")["gdv"]   # 1.0: valencià pur
calcula_gdc("Aquest nen vol venir avui.")["gdc"]    # 1.0: català pur
```

Des de la línia d'ordres:

```bash
avlizador tradueix "Aquest noi necessita ajuda."
avlizador tradueix --fitxer entrada.txt > eixida.txt   # una frase o paràgraf per línia
avlizador tradueix --motor "..."                       # només el motor, sense el model
avlizador gd --text "Este xiquet vol vindre hui."      # també gdv i gdc
avlizador gd --corpus corpus.jsonl --camp text --html informe.html  # informe HTML frase a frase
avlizador avalua --benchmarks manual                   # avaluació (cal [avaluacio])
avlizador --help
```

## Resultats

Benchmark d'avaluació: **manual mescla** (458 frases del BOE i de l'AVL,
revisades a mà). TER i WER: percentatge de paraules que cal editar per a
arribar a la referència (com més baixos, millor).

| Sistema | Exactes | BLEU | chrF | TER | WER |
|---|---|---|---|---|---|
| Motor + FLOR-760M (sistema principal) | **227/458 (49,6 %)** | **90,88** | **96,34** | **5,61** | **6,01** |
| Motor sol | 214/458 (46,7 %) | 90,39 | 96,10 | 5,91 | 6,30 |

En les frases de l'AVL encerta exactament el 92 %. En les del BOE les
frases exactes baixen (13 %) perquè la traducció oficial reformula molt
(futur on el català usa present, sinònims no dialectals...), però el TER
es queda en 9: una paraula de cada deu. Tots els benchmarks i mètriques,
en
[`pipeline/03_seleccio_de_model/resultats_benchmarks_cat_val.md`](pipeline/03_seleccio_de_model/resultats_benchmarks_cat_val.md).

## Benchmarks

Tots són en [`dades/benchmarks/`](dades/benchmarks/) (vegeu-ne el README):
el manual (mescla, BOE i AVL), el banc curat de 151 frases, el
d'homògrafs, els del BOE (estricte i ampli, mostres i complets) i el
dataset públic gplsi (CC BY 4.0). Format: llista de
`{"id", "oriental", "occidental"}` (català i valencià).

```bash
pip install ".[ml,avaluacio]" --extra-index-url https://download.pytorch.org/whl/cpu
avlizador avalua                      # tots (sense els complets del BOE)
avlizador avalua --benchmarks manual  # només el d'avaluació
avlizador avalua --llista             # els disponibles
```

## Estructura del repositori

```
src/avlizador/            el paquet que s'instal·la
  traductor_cat_val/        traductor: regles (rules/), model de llengua (model_llengua/), data/
  grau_dialectal/           GD, GDV i GDC
  avaluacio/                mètriques i avaluació amb els benchmarks
  cli.py                    ordre `avlizador`
dades/
  lexic/                    diccionaris del projecte (font única)
  benchmarks/               benchmarks d'avaluació
scripts/sync_data.py      copia dades/lexic/ a src/avlizador/traductor_cat_val/data/
tests/                    pytest: doctests, API i ordres
documentacio/             metodologia, resultats i fulls de ruta
pipeline/                 registre del treball que va construir i validar les eines (etapes 01-09)
```

`pipeline/` no s'instal·la: és la infraestructura del projecte (scraping
de l'AVL, regles, corpus del BOE, selecció de models, capes de LLM
descartades...). La història completa, amb les decisions i el que es va
descartar, és en
[`documentacio/metodologia_i_resultats.md`](documentacio/metodologia_i_resultats.md).

## Desenvolupament

```bash
pip install -e ".[ml,avaluacio,dev]" --extra-index-url https://download.pytorch.org/whl/cpu
pytest                                  # doctests + proves de l'API i les ordres
```

Per a canviar el lèxic, s'editen **només** els fitxers de `dades/lexic/`
i després:

```bash
python scripts/sync_data.py            # regenera src/avlizador/traductor_cat_val/data/
python scripts/sync_data.py --check    # ha de dir "Tot sincronitzat"
pytest
avlizador avalua --benchmarks manual   # comparar amb la taula de resultats
```

La direcció valencià → català és en el codi
(`traductor_cat_val/rules/val_cat/`, l'usa el GD) però no forma part de
l'API pública.

## Llicència

Pendent de confirmar (previsiblement Creative Commons BY 4.0). El dataset
gplsi de `dades/benchmarks/gplsi/` és CC BY 4.0 dels seus autors (vegeu-ne
el README).
