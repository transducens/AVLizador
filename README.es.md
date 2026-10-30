*[Llegeix-ho en català](README.md)*

# AVLizador: traductor dialectal catalán → valenciano y Grado Dialectal

AVLizador convierte texto en **catalán oriental** (norma IEC) a
**valenciano occidental** (norma de la AVL) y mide cuánto de valenciano o
de catalán tiene un texto. No traduce entre idiomas: cambia solo lo
dialectal (léxico, conjugaciones, demostrativos, posesivos, numerales...).

Se instala como un paquete de Python, `avlizador`, con dos herramientas:

| Herramienta | Qué hace | Importación |
|---|---|---|
| **Traductor catalán → valenciano** | Motor de reglas con los diccionarios del proyecto y spaCy, más un modelo de lenguaje pequeño (FLOR-760M) que resuelve las palabras ambiguas ("cop" → *colp* o *vegada*, "nou" → *nou* o *anou*) | `avlizador.traductor_cat_val` |
| **Grado Dialectal** (GD, GDV, GDC) | Índices de 0 a 1 que dicen si un texto es valenciano o catalán | `avlizador.grau_dialectal` |

Funciona **solo con CPU**, sin GPU ni servicios externos: está pensado para
equipos con pocos recursos.

## Instalación

Requiere Python 3.10 o posterior. Desde una copia del repositorio:

```bash
pip install ".[ml]" --extra-index-url https://download.pytorch.org/whl/cpu
```

- `[ml]` instala `torch` (versión CPU) y `transformers` para el modelo de
  lenguaje FLOR-760M, que se descarga de Hugging Face la primera vez que
  se usa (1,5 GB; se guarda en la carpeta de `HF_HOME`). Es la instalación
  recomendada.
- Sin `[ml]` (`pip install .`) funciona solo el motor de reglas: el
  traductor lo usa y avisa una vez de que falta el modelo
  (`AvisSenseModelLlengua`).
- El modelo catalán de spaCy (`ca_core_news_md`) se instala solo.
- `[avaluacio]` añade `sacrebleu` para evaluar con los benchmarks; `[dev]`,
  `pytest`.

## Uso

En Python:

```python
from avlizador import translate_cat_val, calcula_gd, calcula_gdv, calcula_gdc

translate_cat_val("Aquest noi necessita ajuda. Un cop acabada la reunió, marxem.")
# 'Este xic necessita ajuda. Una vegada acabada la reunió, marxem.'

calcula_gd("Este xiquet vol vindre hui.")["gd"]     # 1.0: valenciano
calcula_gdv("Este xiquet vol vindre hui.")["gdv"]   # 1.0: valenciano puro
calcula_gdc("Aquest nen vol venir avui.")["gdc"]    # 1.0: catalán puro
```

Desde la línea de órdenes:

```bash
avlizador tradueix "Aquest noi necessita ajuda."
avlizador tradueix --fitxer entrada.txt > salida.txt   # una frase o párrafo por línea
avlizador tradueix --motor "..."                       # solo el motor, sin el modelo
avlizador gd --text "Este xiquet vol vindre hui."      # también gdv y gdc
avlizador gd --corpus corpus.jsonl --camp text --html informe.html  # informe HTML frase a frase
avlizador avalua --benchmarks manual                   # evaluación (necesita [avaluacio])
avlizador --help
```

## Resultados

Benchmark de evaluación: **manual mezcla** (458 frases del BOE y de la
AVL, revisadas a mano). TER y WER: porcentaje de palabras que hay que
editar para llegar a la referencia (cuanto más bajos, mejor).

| Sistema | Exactas | BLEU | chrF | TER | WER |
|---|---|---|---|---|---|
| Motor + FLOR-760M (sistema principal) | **227/458 (49,6 %)** | **90,88** | **96,34** | **5,61** | **6,01** |
| Motor solo | 214/458 (46,7 %) | 90,39 | 96,10 | 5,91 | 6,30 |

En las frases de la AVL acierta exactamente el 92 %. En las del BOE las
frases exactas bajan (13 %) porque la traducción oficial reformula mucho
(futuro donde el catalán usa presente, sinónimos no dialectales...), pero
el TER se queda en 9: una palabra de cada diez. Todos los benchmarks y
métricas, en
[`pipeline/03_seleccio_de_model/resultats_benchmarks_cat_val.md`](pipeline/03_seleccio_de_model/resultats_benchmarks_cat_val.md).

## Benchmarks

Todos están en [`dades/benchmarks/`](dades/benchmarks/) (ver su README):
el manual (mezcla, BOE y AVL), el banco curado de 151 frases, el de
homógrafos, los del BOE (estricto y amplio, muestras y completos) y el
dataset público gplsi (CC BY 4.0). Formato: lista de
`{"id", "oriental", "occidental"}` (catalán y valenciano).

```bash
pip install ".[ml,avaluacio]" --extra-index-url https://download.pytorch.org/whl/cpu
avlizador avalua                      # todos (sin los completos del BOE)
avlizador avalua --benchmarks manual  # solo el de evaluación
avlizador avalua --llista             # los disponibles
```

## Estructura del repositorio

```
src/avlizador/            el paquete que se instala
  traductor_cat_val/        traductor: reglas (rules/), modelo de lenguaje (model_llengua/), data/
  grau_dialectal/           GD, GDV y GDC
  avaluacio/                métricas y evaluación con los benchmarks
  cli.py                    orden `avlizador`
dades/
  lexic/                    diccionarios del proyecto (fuente única)
  benchmarks/               benchmarks de evaluación
scripts/sync_data.py      copia dades/lexic/ a src/avlizador/traductor_cat_val/data/
tests/                    pytest: doctests, API y órdenes
documentacio/             metodología, resultados y hojas de ruta
pipeline/                 registro del trabajo que construyó y validó las herramientas (etapas 01-09)
```

`pipeline/` no se instala: es la infraestructura del proyecto (scraping
de la AVL, reglas, corpus del BOE, selección de modelos, capas de LLM
descartadas...). La historia completa, con las decisiones y lo que se
descartó, está en
[`documentacio/metodologia_i_resultats.md`](documentacio/metodologia_i_resultats.md).

## Desarrollo

```bash
pip install -e ".[ml,avaluacio,dev]" --extra-index-url https://download.pytorch.org/whl/cpu
pytest                                  # doctests + pruebas de la API y las órdenes
```

Para cambiar el léxico, se editan **solo** los ficheros de `dades/lexic/`
y después:

```bash
python scripts/sync_data.py            # regenera src/avlizador/traductor_cat_val/data/
python scripts/sync_data.py --check    # tiene que decir "Tot sincronitzat"
pytest
avlizador avalua --benchmarks manual   # comparar con la tabla de resultados
```

La dirección valenciano → catalán está en el código
(`traductor_cat_val/rules/val_cat/`, la usa el GD) pero no forma parte
de la API pública.

## Licencia

Pendiente de confirmar (previsiblemente Creative Commons BY 4.0). El
dataset gplsi de `dades/benchmarks/gplsi/` es CC BY 4.0 de sus autores
(ver su README).
