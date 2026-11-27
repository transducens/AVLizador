*[Llegeix-ho en català](README.md)*

# AVLizador: traductor dialectal catalán → valenciano y Grado Dialectal

AVLizador convierte texto en **catalán oriental** (norma IEC) a
**valenciano occidental** (norma de la AVL) y mide cuánto de valenciano o
de catalán tiene un texto. No traduce entre idiomas: cambia solo lo
dialectal (léxico, conjugaciones, demostrativos, posesivos, numerales...).

Se instala como un paquete de Python, `avlizador`, con dos herramientas:

| Herramienta | Qué hace | Importación |
|---|---|---|
| **Traductor catalán → valenciano** | Motor de reglas con los diccionarios del proyecto y spaCy, más un modelo de lenguaje de n-gramas (KenLM) y un clasificador de sentido que resuelven las palabras ambiguas ("cop" → *colp* o *vegada*, "nou" → *nou* o *anou*). Cuando un nombre cambia de género ("el préssec" → "la bresquilla"), hace concordar el determinante, los adjetivos y el atributo | `avlizador.traductor_cat_val` |
| **Grado Dialectal** (GD, GDV, GDC) | Índices de 0 a 1 que dicen si un texto es valenciano o catalán | `avlizador.grau_dialectal` |

Funciona **solo con CPU**, sin GPU ni servicios externos: está pensado para
equipos con pocos recursos.

## Instalación

Guía paso a paso para Windows, Linux y macOS (entorno virtual,
instalación, pruebas y problemas habituales): [`documentacio/guia_instalacion.md`](documentacio/guia_instalacion.md).
En resumen, requiere Python 3.10 o posterior y, desde una copia del repositorio:

```bash
pip install ".[kenlm]"
```

- `[kenlm]` instala la biblioteca KenLM, el modelo de lenguaje de las
  palabras ambiguas. Se compila al instalarla: hace falta un compilador de
  C++. En Linux y macOS funciona; en Windows normalmente no se instala:
  usad la imagen Docker de la [interfaz web](https://github.com/transducens/traductor-transducens-web) o el motor solo.
- Los ficheros del modelo KenLM no están en git ni en el paquete: se
  descargan de Hugging Face la primera vez que se usan (ver
  [Modelo de lenguaje](#modelo-de-lenguaje)).
- Sin KenLM o sin sus ficheros funciona solo el motor de reglas: el
  traductor lo usa y avisa una vez de que falta el modelo
  (`AvisSenseModelLlengua`).
- El modelo catalán de spaCy (`ca_core_news_md`) se instala solo.
- `[avaluacio]` añade `sacrebleu` para evaluar con los benchmarks; `[dev]`,
  `pytest`.

### Modelo de lenguaje

Las palabras ambiguas del léxico ("cop", "nou", "manca"...) las decide un
modelo KenLM de orden 5 entrenado con frases valencianas de MaCoCu-ca y
del DOGV (2025-2026), más un clasificador de sentido (Naive Bayes; hoy
para "cop", "cops" y "deu") entrenado con el mismo texto y textos de la
AVL. Son tres ficheros, publicados en Hugging Face:
[`transducens/avlizador-kenlm-va`](https://huggingface.co/transducens/avlizador-kenlm-va)
(CC BY 4.0).

| Fichero | Qué es |
|---|---|
| `valencia_net_dogv_o5.binary` | el modelo KenLM (82 MB) |
| `valencia_net_dogv_freq.json` | frecuencias de las palabras (para el prior) |
| `sentit.json` (o el antiguo `nb.json`) | el clasificador de sentido de las palabras ambiguas (~730 KB) |

El paquete los descarga solo la primera vez que se usan (hace falta
`huggingface_hub`, que viene con `[kenlm]`, e internet esa vez) y los
guarda en la caché de Hugging Face (`HF_HOME`); después funciona sin
internet.

Para dejarlo listo antes (en una instalación, al construir una imagen o
para trabajar después sin internet), la orden `avlizador model`:

```bash
avlizador model info                      # qué modelo usa esta versión, dónde está y si está listo (sin red)
avlizador model descarrega                # a la caché de Hugging Face, donde lo busca el paquete
avlizador model descarrega --desti /opt/kenlm --origen copias/  # a una carpeta, para AVLIZADOR_KENLM_DIR
avlizador model comprova                  # compara los ficheros con la revisión de Hugging Face
```

`descarrega` descarga siempre la revisión de esta versión del paquete y
comprueba cada fichero con el tamaño y la huella (sha256 o sha1 de git) que
tiene en Hugging Face: una copia de otra revisión no se usa, se vuelve a
descargar. `--origen` aprovecha copias locales que correspondan; `--lemes`
trae también la opción con lemas; `--sense-comprovar`, para trabajar sin
red con `--origen`. Escribe en la salida estándar la carpeta donde queda el
modelo y sale con 1 si algo falla. En Python, `info_model`,
`descarrega_model` y `comprova_model` (`avlizador.traductor_cat_val`).

#### Qué versión del modelo descarga cada versión del paquete

Cada versión del paquete descarga siempre **el mismo commit** del
repositorio del modelo en Hugging Face, fijado en `REVISIO_HF`
([`src/avlizador/traductor_cat_val/model_llengua/kenlm.py`](src/avlizador/traductor_cat_val/model_llengua/kenlm.py)).
Así, si más adelante se sube un modelo nuevo, las instalaciones de una
versión anterior siguen descargando el suyo y traducen igual. Se fija por
commit, y no por etiqueta, porque la web de Hugging Face no permite crear
etiquetas.

| Versión del paquete | Commit del modelo en Hugging Face | Modelo |
|---|---|---|
| 2.0.0 | [`db4a1f1`](https://huggingface.co/transducens/avlizador-kenlm-va/tree/db4a1f10d55bbc30ad54728e1639d17d32526ef7) (`db4a1f10d55bbc30ad54728e1639d17d32526ef7`, 17/11/2026) | KenLM `valencia_net_dogv2` (MaCoCu + DOGV 2025-2026) + clasificador `sentit_dogv2_avl` (+ AVL) |
| 2.0.1 | [`684993c`](https://huggingface.co/transducens/avlizador-kenlm-va/tree/684993c83721bb000d424bbeb7286247c40e9154) (`684993c83721bb000d424bbeb7286247c40e9154`, 23/11/2026) | El mismo KenLM y clasificador; la tabla de frecuencias nueva (con «brolladors», que faltaba desde el léxico del 18/11) y el KenLM de lemas de la opción `kenlm-lemes` |

Subir a Hugging Face otro fichero (por ejemplo, la ficha `README.md`) crea
un commit nuevo, pero no cambia nada para las versiones ya publicadas.

**Publicar un modelo nuevo** (para una versión nueva del paquete):

1. Generar la carpeta: `python scripts/hf_model/kenlm.py --dir ... --nom ...
   --fonts ...` (ver su docstring) → `dades/hf_model/kenlm/`.
2. Subirla a Hugging Face (*Files and versions* → *Add file* → *Upload
   files*, o `hf upload transducens/avlizador-kenlm-va dades/hf_model/kenlm . --repo-type model`).
3. Copiar el identificador completo del commit nuevo: *Files and versions*
   → *History*, o `python -c "from huggingface_hub import HfApi;
   print(HfApi().model_info('transducens/avlizador-kenlm-va').sha)"`.
4. Ponerlo en `REVISIO_HF`, añadir una fila a la tabla de arriba (y en
   [`README.md`](README.md)), pasar los tests y sacar la versión nueva del
   paquete.

| Variable de entorno | Qué hace |
|---|---|
| `AVLIZADOR_KENLM_DIR` | usar una carpeta local con los tres ficheros en lugar de Hugging Face |
| `AVLIZADOR_KENLM_DESCARREGA=0` o `HF_HUB_OFFLINE=1` | no descargar nada (solo la caché o la carpeta local) |
| `AVLIZADOR_KENLM_REVISIO` | otra revisión del modelo en Hugging Face (commit, rama o etiqueta) en lugar de la de `REVISIO_HF` |

Coste: ~0,1 ms por frase candidata y ~80 MB de memoria, sin GPU ni
PyTorch. Hasta el 12/11/2026 el modelo era FLOR-760M (833 ms y ~1,5 GB);
desde la versión 2.0.0 ya no está en el paquete.

**Opción con lemas** (desde la 2.0.1, no por defecto): `--model kenlm-lemes`
usa un KenLM de lemas parciales en lugar del de formas (198 aciertos y 1
error grave en las 237 decisiones de los homógrafos, frente a 196 y 0; en
las frases con palabra ambigua, la traducción tarda unas 2 veces más: spaCy
lematiza el contexto). Sus dos ficheros están en el mismo repositorio de
Hugging Face y se descargan, como los demás, la primera vez que se usa la
opción (quien no la usa no los descarga); también se pueden poner en la
carpeta de `AVLIZADOR_KENLM_DIR`. Detalle en
[`model_llengua/README.es.md`](src/avlizador/traductor_cat_val/model_llengua/README.es.md).

Por qué KenLM y todas las cifras:
[`documentacio/resultats_model_llengua_kenlm.md`](documentacio/resultats_model_llengua_kenlm.md).

## Uso

En Python:

```python
from avlizador import translate_cat_val, calcula_gd, calcula_gdv, calcula_gdc

translate_cat_val("Aquest noi necessita ajuda. Un cop acabada la reunió, marxem.")
# 'Este xic necessita ajuda. Una vegada acabada la reunió, marxem.'
translate_cat_val("El préssec és molt bo. Les despeses previstes són altes.")
# 'La bresquilla és molt bona. Els gastos previstos són alts.'  (cambio de género)
# model="kenlm": error (FaltaKenLM) si falta KenLM, en lugar del motor solo con aviso

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
avlizador model info                                   # el modelo KenLM (ver «Modelo de lenguaje»)
avlizador --help
```

### API pública

Lo que se puede usar desde otro programa (por ejemplo, la [interfaz web](https://github.com/transducens/traductor-transducens-web)) es
lo que exportan `avlizador`, `avlizador.traductor_cat_val` y
`avlizador.grau_dialectal` (sus `__all__`):

| Dónde | Qué |
|---|---|
| `avlizador.traductor_cat_val` | `translate_cat_val`, `translate_cat_val_motor`, `AvisSenseModelLlengua`; el modelo: `info_model`, `descarrega_model`, `comprova_model`, `ErrorModel`, `kenlm_disponible` |
| `avlizador.grau_dialectal` | `calcula_gd`, `calcula_gdv`, `calcula_gdv_corpus`, `calcula_gdc`, `calcula_gdc_corpus`, `resalta_html` (el texto en HTML accesible con los marcadores resaltados) |
| `avlizador` | `__version__` y las funciones principales de los dos anteriores |

Los demás módulos son internos y pueden cambiar en cualquier versión.
Cambiar o quitar algo de la API pública exige una versión mayor (3.0.0…);
añadir, una menor. Lo vigila `tests/test_api_publica.py`.

## Interfaz web y Docker

La interfaz web **Traductor Transducens** (adaptador catalán → valenciano
y Grado Dialectal, accesible, en valenciano y castellano) y su imagen
Docker están, desde el 27/11/2026, en un repositorio aparte:
[`transducens/traductor-transducens-web`](https://github.com/transducens/traductor-transducens-web). Instala AVLizador como
una dependencia, en una versión fijada, y solo usa su [API
pública](#api-pública). Hasta la 2.0.1, la web estaba aquí (`avlizador web`,
extra `[web]`); el diseño original está en
[`documentacio/hoja_de_ruta_interfaz_docker.md`](documentacio/hoja_de_ruta_interfaz_docker.md).

## Resultados

Benchmark de evaluación: **manual mezcla** (458 frases del BOE y de la
AVL, revisadas a mano). TER y WER: porcentaje de palabras que hay que
editar para llegar a la referencia (cuanto más bajos, mejor). Versión
2.0.1, medida del 23/11/2026 (`avlizador avalua`; el manual da lo mismo que la 2.0.0); FLOR-760M (el modelo
de antes, ya no incluido) y el motor solo, del 13/11/2026:

| Sistema | Exactas | BLEU | chrF | TER | WER |
|---|---|---|---|---|---|
| Motor + KenLM + clasificador (por defecto) | **232/458 (50,7 %)** | **91,00** | **96,34** | **5,58** | **5,96** |
| Motor + FLOR-760M (hasta la 1.2.0) | 231/458 (50,4 %) | 90,98 | 96,33 | 5,59 | 5,97 |
| Motor solo | 218/458 (47,6 %) | 90,49 | 96,08 | 5,90 | 6,27 |

Por partes (2.0.1): BOE 35/246 (BLEU 84,01, TER 9,21) y AVL 197/212
(BLEU 99,10, TER 0,41). La versión 1.2.0 (FLOR) sacaba 33 y 195
(228/458).

Frases exactas en el resto de benchmarks (homógrafos, 23/11/2026, versión
2.0.1, con los homógrafos corregidos el mismo día: sin «recuita», v1 249 y
v2 144 frases, FLOR no se ha medido en ellos; 151, 16-17/11/2026; BOE y
gplsi, 13/11/2026 con el modelo KenLM anterior):

| Benchmark | KenLM + clasificador | FLOR-760M (de antes) | Motor solo |
|---|---|---|---|
| homógrafos v1 (151 + homógrafos, 249) | **228** | — | 179 |
| homógrafos v2 (144) | **113** | — | 75 |
| 151 (154) | 144 | **145** | 142 |
| BOE estricto, muestra (2.000) | **1.894** | **1.894** | 1.800 |
| gplsi (1.958) | 1.550 | **1.551** | 1.533 |

En las 237 decisiones de los homógrafos, KenLM + clasificador acierta
196 y no comete ningún error grave (que cambie el sentido; la 2.0.0, 186 y 0). Detalle:
[`documentacio/resultats_model_llengua_kenlm.md`](documentacio/resultats_model_llengua_kenlm.md).

Histórico, medida del 30/10/2026 (versión 1.0.1, con FLOR-760M como
modelo por defecto; el léxico ha cambiado desde entonces):

| Sistema | Exactas | BLEU | chrF | TER | WER |
|---|---|---|---|---|---|
| Motor + FLOR-760M (sistema principal entonces) | 227/458 (49,6 %) | 90,88 | 96,34 | 5,61 | 6,01 |
| Motor solo | 214/458 (46,7 %) | 90,39 | 96,10 | 5,91 | 6,30 |

En esa medida, en las frases de la AVL acertaba exactamente el 92 %. En
las del BOE las frases exactas bajan (13 %) porque la traducción oficial
reformula mucho (futuro donde el catalán usa presente, sinónimos no
dialectales...), pero el TER se queda en 9: una palabra de cada diez.
Todos los benchmarks y métricas, en
[`pipeline/03_seleccio_de_model/resultats_benchmarks_cat_val.md`](pipeline/03_seleccio_de_model/resultats_benchmarks_cat_val.md).

## Benchmarks

Todos están en [`dades/benchmarks/`](dades/benchmarks/) (ver su README):
el manual (mezcla, BOE y AVL), el banco curado de 151 frases, el de
homógrafos, los del BOE (estricto y amplio, muestras y completos) y el
dataset público gplsi (CC BY 4.0). Formato: lista de
`{"id", "oriental", "occidental"}` (catalán y valenciano).

```bash
pip install ".[kenlm,avaluacio]"
avlizador avalua                      # todos (sin los completos del BOE), con KenLM
avlizador avalua --benchmarks manual  # solo el de evaluación
avlizador avalua --motor               # también el motor solo, para comparar
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
pip install -e ".[kenlm,avaluacio,dev]"
pytest                                  # doctests + pruebas de la API y las órdenes
```

FLOR-760M (el modelo hasta la 1.2.0) ya no está en el paquete; para
repetir los experimentos que lo comparan con KenLM, su puntuador está en
`pipeline/03_seleccio_de_model/model_llengua/flor.py` (hacen falta `torch`
y `transformers` aparte).

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

[GNU GPL 2.0 o posterior](LICENSE) (GPL-2.0-or-later), desde el
26/11/2026: el código y los datos propios del proyecto (el léxico de
`dades/lexic/`, recopilado a mano por el equipo, y los benchmarks). Las
versiones publicadas hasta la 2.0.1 incluida son Apache 2.0. Las piezas de
terceros mantienen su licencia y se detallan en [`NOTICE`](NOTICE):

- el diccionario morfológico catalán de `dades/lexic/`
  (`catalan_sin_top_loc_prefijos_participios.txt`) viene de Apertium
  ([`apertium-cat`](https://github.com/apertium/apertium-cat)), con
  licencia **GPL 2.0**: es el motivo de la licencia GPL de AVLizador;

- el modelo catalán de spaCy (`ca_core_news_md`) es **GPL 3.0**: no se
  incluye, pip lo instala como dependencia, y quien lo redistribuya tiene
  que cumplir esa licencia;
- la biblioteca KenLM es **GNU LGPL 2.1** (https://github.com/kpu/kenlm);
  el modelo KenLM lo ha entrenado el proyecto con MaCoCu-ca 1.0 (CC0 1.0),
  textos del DOGV y, el clasificador, textos de la AVL, y está publicado en
  Hugging Face con licencia **CC BY 4.0**
  ([`transducens/avlizador-kenlm-va`](https://huggingface.co/transducens/avlizador-kenlm-va));
- el dataset gplsi de `dades/benchmarks/gplsi/` es CC BY 4.0 de sus
  autores;
- los textos del BOE y de la AVL se reutilizan citando su fuente.
