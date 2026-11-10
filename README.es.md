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

Guía paso a paso para Windows, Linux y macOS (entorno virtual,
instalación, pruebas y problemas habituales): [`documentacio/guia_instalacion.md`](documentacio/guia_instalacion.md).
En resumen, requiere Python 3.10 o posterior y, desde una copia del repositorio:

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
pip install ".[ml,web]" --extra-index-url https://download.pytorch.org/whl/cpu
avlizador web          # http://127.0.0.1:8000
```

Con Docker (la imagen lleva spaCy y FLOR-760M dentro y funciona **sin
internet**; la primera construcción descarga unos 2 GB):

```bash
docker compose up --build     # http://localhost:8000
```

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
| `AVLIZADOR_MODE` | `complet` | `complet` = motor + FLOR; `motor` = solo reglas (sin cargar FLOR: ~1,5 GB menos de RAM y arranque más rápido) | `motor` en equipos con menos de 4 GB de RAM o si hace falta rapidez antes que acertar los homógrafos |
| `MAX_CARACTERS` | 20000 | longitud máxima del texto por petición; si se pasa, HTTP 413 con un mensaje | subirla si se traducen documentos largos y el equipo lo aguanta; bajarla si las peticiones tardan demasiado |
| `MAX_TRADUCCIONS_SIMULTANIES` | 2 | traducciones a la vez; si ya hay tantas, HTTP 429 ("El servicio está ocupado") | según los núcleos (regla de abajo); 1 en equipos de 2 núcleos |
| `OMP_NUM_THREADS` | 2 | hilos de cálculo de PyTorch (y de otras librerías numéricas) | según los núcleos (regla de abajo) |
| `TORCH_NUM_THREADS` | 2 | hilos que usa FLOR: la lee AVLizador (`torch.set_num_threads`); PyTorch no la lee por sí solo | igual que `OMP_NUM_THREADS`; normalmente el mismo valor |
| `HF_HUB_OFFLINE` | `1` | no intentar conectarse a Hugging Face (los modelos ya están dentro de la imagen) | no hace falta cambiarla en Docker |
| `UVICORN_LOG_LEVEL` | `warning` | nivel de los mensajes del servidor (arranque, avisos, errores). No vuelve a activar las líneas por petición: no se registran nunca (privacidad) | `info` o `debug` solo para investigar un problema de arranque |
| `AVLIZADOR_DOCS` | `0` | `1` = documentación interactiva de la API en `/docs` (carga JavaScript de un CDN) | solo en desarrollo, nunca en producción |

**Regla de los núcleos**: `MAX_TRADUCCIONS_SIMULTANIES` ×
`TORCH_NUM_THREADS` ≤ núcleos del equipo (con los valores por defecto, 4
núcleos). Si se pasa, las traducciones compiten por los mismos núcleos y
todas van más lentas.

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

[Apache 2.0](LICENSE): el código y los datos propios del proyecto (el
léxico de `dades/lexic/`, recopilado a mano por el equipo, y los
benchmarks). Las piezas de terceros mantienen su licencia y se detallan
en [`NOTICE`](NOTICE):

- el modelo catalán de spaCy (`ca_core_news_md`) es **GPL 3.0**: no se
  incluye, pip lo instala como dependencia, y quien lo redistribuya tiene
  que cumplir esa licencia;
- FLOR-760M es Apache 2.0 (adaptación de BLOOM-1.1B);
- el dataset gplsi de `dades/benchmarks/gplsi/` es CC BY 4.0 de sus
  autores;
- los textos del BOE y de la AVL se reutilizan citando su fuente.

**Imagen Docker.** El código de AVLizador es Apache 2.0, pero la
imagen Docker incluye componentes de terceros con otras licencias (ver
[`NOTICE`](NOTICE)), entre ellos el modelo de spaCy `ca_core_news_md`,
con licencia GPL-3.0, y FLOR-760M, con las restricciones de uso de la
licencia RAIL de BLOOM. Quien distribuya una imagen con estos modelos
dentro tiene que cumplir esas licencias. Por eso recomendamos construir
la imagen en local (`docker compose build`) en lugar de distribuirla.
