*[Llegeix-ho en català](README.md)*

# AVLizador: traductor dialectal catalán → valenciano y Grado Dialectal

AVLizador convierte texto en **catalán oriental** (norma IEC) a
**valenciano occidental** (norma de la AVL) y mide cuánto de valenciano o
de catalán tiene un texto. No traduce entre idiomas: cambia solo lo
dialectal (léxico, conjugaciones, demostrativos, posesivos, numerales...).

Se instala como un paquete de Python, `avlizador`, con dos herramientas:

| Herramienta | Qué hace | Importación |
|---|---|---|
| **Traductor catalán → valenciano** | Motor de reglas con los diccionarios del proyecto y spaCy, más un modelo de lenguaje de n-gramas (KenLM) y un clasificador de sentido que resuelven las palabras ambiguas ("cop" → *colp* o *vegada*, "nou" → *nou* o *anou*); FLOR-760M, opcional | `avlizador.traductor_cat_val` |
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

- `[kenlm]` instala la biblioteca KenLM, el modelo de lenguaje por
  defecto de las palabras ambiguas (desde el 13/11/2026). Se compila al
  instalarla: hace falta un compilador de C++. En Linux y macOS funciona;
  en Windows normalmente no se instala: usad Docker (abajo), FLOR o el
  motor solo.
- Los ficheros del modelo KenLM no están en git ni en el paquete: ver
  [Modelo de lenguaje](#modelo-de-lenguaje) (`AVLIZADOR_KENLM_DIR`).
- Sin KenLM o sin sus ficheros funciona solo el motor de reglas: el
  traductor lo usa y avisa una vez de que falta el modelo
  (`AvisSenseModelLlengua`).
- `[ml]` (opcional) instala `torch` (versión CPU) y `transformers` para
  FLOR-760M, el modelo por defecto hasta el 12/11/2026:
  `pip install ".[ml]" --extra-index-url https://download.pytorch.org/whl/cpu`.
  Se descarga de Hugging Face la primera vez que se usa (1,5 GB; se guarda
  en la carpeta de `HF_HOME`).
- El modelo catalán de spaCy (`ca_core_news_md`) se instala solo.
- `[avaluacio]` añade `sacrebleu` para evaluar con los benchmarks; `[dev]`,
  `pytest`.

### Modelo de lenguaje

Las palabras ambiguas del léxico ("cop", "nou", "manca"...) las decide un
modelo KenLM de orden 5 entrenado con frases valencianas de MaCoCu-ca y
del DOGV (2025-2026), más un clasificador de sentido (Naive Bayes) para
"cop" (*colp* o *vegada*). Hace falta una carpeta, indicada con la
variable de entorno `AVLIZADOR_KENLM_DIR`, con tres ficheros:

| Fichero | Qué es |
|---|---|
| `valencia_net_dogv_o5.binary` | el modelo KenLM (77 MB) |
| `valencia_net_dogv_freq.json` | frecuencias de las palabras (para el prior) |
| `sentit.json` (o el antiguo `nb.json`) | el clasificador de sentido de las palabras ambiguas (~730 KB; hoy tienen cop, cops y deu) |

De momento se piden al equipo; más adelante se publicarán en Hugging
Face. Coste: ~0,1 ms por frase candidata y ~74 MB de memoria (FLOR: 833
ms y ~1,5 GB). Por qué KenLM y todas las cifras:
[`documentacio/resultats_model_llengua_kenlm.md`](documentacio/resultats_model_llengua_kenlm.md).

## Uso

En Python:

```python
from avlizador import translate_cat_val, calcula_gd, calcula_gdv, calcula_gdc

translate_cat_val("Aquest noi necessita ajuda. Un cop acabada la reunió, marxem.")
# 'Este xic necessita ajuda. Una vegada acabada la reunió, marxem.'
# model="kenlm": error (FaltaKenLM) si falta KenLM; model="flor": FLOR-760M (necesita [ml])

calcula_gd("Este xiquet vol vindre hui.")["gd"]     # 1.0: valenciano
calcula_gdv("Este xiquet vol vindre hui.")["gdv"]   # 1.0: valenciano puro
calcula_gdc("Aquest nen vol venir avui.")["gdc"]    # 1.0: catalán puro
```

Desde la línea de órdenes:

```bash
avlizador tradueix "Aquest noi necessita ajuda."
avlizador tradueix --fitxer entrada.txt > salida.txt   # una frase o párrafo por línea
avlizador tradueix --motor "..."                       # solo el motor, sin el modelo
avlizador tradueix --model flor "..."                  # FLOR-760M en lugar de KenLM (necesita [ml])
avlizador gd --text "Este xiquet vol vindre hui."      # también gdv y gdc
avlizador gd --corpus corpus.jsonl --camp text --html informe.html  # informe HTML frase a frase
avlizador avalua --benchmarks manual                   # evaluación (necesita [avaluacio])
avlizador --help
```

## Interfaz web y Docker

Una interfaz web accesible (WCAG 2.2 AA), en valenciano y castellano,
con el título **Traductor Transducens**: una portada, "Traducción de
idiomas" (preparada para otros traductores; todavía ningún par),
"Adaptador dialectal" con la adaptación del catalán al valenciano
(`/dialectes/adaptador`) y el Grado Dialectal (`/dialectes/gd`), y
"Acerca de". El catalán y el valenciano son la misma lengua: la interfaz
lo presenta como una adaptación entre dialectos, no como una traducción
entre idiomas. Los textos no se guardan ni se registran.

Sin Docker, desde una copia del repositorio:

```bash
pip install ".[kenlm,web]"
avlizador web          # http://127.0.0.1:8000
```

Con Docker (la imagen lleva spaCy y KenLM dentro, sin torch ni FLOR, y
funciona **sin internet**). Antes de construirla, poned los tres ficheros
del [modelo de lenguaje](#modelo-de-lenguaje) en `docker/kenlm/` (carpeta
ignorada por git): la construcción los copia en `/opt/kenlm` y se detiene
con un mensaje claro si falta alguno.

```bash
docker compose up --build     # http://localhost:8000
```

La imagen necesita ~1 GB de RAM (`mem_limit: 2g` en
`docker-compose.yml`).

Para un equipo sin internet, la imagen se copia como un fichero:

```bash
docker save avlizador:1.2.0 > avlizador.tar   # en el equipo donde se ha construido
docker load < avlizador.tar                   # en el equipo de destino
docker compose up                             # con docker-compose.yml al lado
```

Por defecto solo se puede entrar desde el mismo equipo
(`127.0.0.1:8000`); para abrirla a la red, cambiad el puerto en
`docker-compose.yml` (y, fuera de una red interna, poned un proxy HTTPS
delante). La imagen se ejecuta sin root y con el sistema de ficheros de
solo lectura. Detalle del diseño:
[`documentacio/hoja_de_ruta_interfaz_docker.md`](documentacio/hoja_de_ruta_interfaz_docker.md).

### Variables de entorno

Se cambian en `docker-compose.yml` (`environment:`) sin reconstruir la
imagen; fuera de Docker, como variables de entorno antes de
`avlizador web`.

| Variable | Por defecto | Qué hace | Cuándo cambiarla |
|---|---|---|---|
| `AVLIZADOR_MODE` | `complet` | `complet` = motor + KenLM; `motor` = solo reglas. Si en modo `complet` faltan los ficheros de KenLM, el servidor lo avisa en el registro y usa `motor` | `motor` si no se tienen los ficheros del modelo o si hace falta rapidez antes que acertar los homógrafos |
| `AVLIZADOR_KENLM_DIR` | `/opt/kenlm` (en la imagen) | carpeta con los tres ficheros del [modelo de lenguaje](#modelo-de-lenguaje) | fuera de Docker, donde hayáis puesto los ficheros |
| `MAX_CARACTERS` | 20000 | longitud máxima del texto por petición; si se pasa, HTTP 413 con un mensaje | subirla si se traducen documentos largos y el equipo lo aguanta; bajarla si las peticiones tardan demasiado |
| `MAX_TRADUCCIONS_SIMULTANIES` | 2 | traducciones a la vez; si ya hay tantas, HTTP 429 ("El servicio está ocupado") | según los núcleos (regla de abajo); 1 en equipos de 1 núcleo |
| `UVICORN_LOG_LEVEL` | `warning` | nivel de los mensajes del servidor (arranque, avisos, errores). No vuelve a activar las líneas por petición: no se registran nunca (privacidad) | `info` o `debug` solo para investigar un problema de arranque |
| `AVLIZADOR_DOCS` | `0` | `1` = documentación interactiva de la API en `/docs` (carga JavaScript de un CDN) | solo en desarrollo, nunca en producción |

**Regla de los núcleos**: KenLM usa un núcleo por traducción, así que
`MAX_TRADUCCIONS_SIMULTANIES` ≤ núcleos del equipo. Si se pasa, las
traducciones compiten por los mismos núcleos y todas van más lentas.

## Resultados

Benchmark de evaluación: **manual mezcla** (458 frases del BOE y de la
AVL, revisadas a mano). TER y WER: porcentaje de palabras que hay que
editar para llegar a la referencia (cuanto más bajos, mejor). Medida del
13/11/2026 (`avlizador avalua`):

| Sistema | Exactas | BLEU | chrF | TER | WER |
|---|---|---|---|---|---|
| Motor + KenLM + clasificador (por defecto) | **232/458 (50,7 %)** | **91,00** | **96,34** | **5,58** | **5,96** |
| Motor + FLOR-760M (opcional) | 231/458 (50,4 %) | 90,98 | 96,33 | 5,59 | 5,97 |
| Motor solo | 218/458 (47,6 %) | 90,49 | 96,08 | 5,90 | 6,27 |

Frases exactas en el resto de benchmarks (13/11/2026):

| Benchmark | KenLM + clasificador | FLOR-760M | Motor solo |
|---|---|---|---|
| homógrafos v1 (151 + homógrafos, 253) | **227** | 217 | 181 |
| homógrafos v2 (160) | **111** | 96 | 82 |
| 151 (154) | 144 | **145** | 142 |
| BOE estricto, muestra (2.000) | **1.894** | **1.894** | 1.800 |
| gplsi (1.958) | 1.550 | **1.551** | 1.533 |

En las 257 decisiones de los homógrafos, KenLM + clasificador acierta
193 y comete 1 error grave (cambia el sentido). Detalle:
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
avlizador avalua --model kenlm flor --motor  # KenLM, FLOR (necesita [ml]) y el motor solo
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

Para probar también FLOR, añadid `ml` y
`--extra-index-url https://download.pytorch.org/whl/cpu`.

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

[Apache 2.0](LICENSE): el código y los datos propios del proyecto (el
léxico de `dades/lexic/`, recopilado a mano por el equipo, y los
benchmarks). Las piezas de terceros mantienen su licencia y se detallan
en [`NOTICE`](NOTICE):

- el modelo catalán de spaCy (`ca_core_news_md`) es **GPL 3.0**: no se
  incluye, pip lo instala como dependencia, y quien lo redistribuya tiene
  que cumplir esa licencia;
- la biblioteca KenLM es **GNU LGPL 2.1** (https://github.com/kpu/kenlm);
  el modelo KenLM lo ha entrenado el proyecto con MaCoCu-ca 1.0 (CC0 1.0)
  y textos del DOGV, y las condiciones de reutilización del DOGV se tienen
  que revisar antes de publicarlo;
- FLOR-760M (opcional, no se incluye) es Apache 2.0 (adaptación de
  BLOOM-1.1B);
- el dataset gplsi de `dades/benchmarks/gplsi/` es CC BY 4.0 de sus
  autores;
- los textos del BOE y de la AVL se reutilizan citando su fuente.

**Imagen Docker.** El código de AVLizador es Apache 2.0, pero la
imagen Docker incluye componentes de terceros con otras licencias (ver
[`NOTICE`](NOTICE)), entre ellos el modelo de spaCy `ca_core_news_md`,
con licencia GPL-3.0, la biblioteca KenLM (LGPL 2.1) y el modelo KenLM
del proyecto. Desde el 13/11/2026 la imagen ya no lleva FLOR-760M. Quien
distribuya una imagen con estos componentes dentro tiene que cumplir esas
licencias. Por eso recomendamos construir la imagen en local
(`docker compose build`) en lugar de distribuirla.
