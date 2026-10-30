# Hoja de ruta: entrega, baseline de LLM y trazas de FLOR (30/10/2026)

Tres frentes pedidos por el usuario el 30/10/2026, más la evaluación del
sistema final en todos los benchmarks (`avalua_sistema_final.py`, en
marcha ese día):

- **A. Baseline**: comparar el sistema final cat→val (motor + FLOR-760M)
  con LLM generalistas en Abaco, sin ocupar todas las GPU.
- **B. Paquete de entrega + repositorio profesional**: traductor y
  GD/GDV/GDC instalables (`pyproject.toml`, dependencias, CLI),
  benchmarks disponibles en el repo, estructura de carpetas limpia,
  subido a GitHub; `pipeline/` se queda como registro del trabajo.
- **C. Trazas de FLOR**: análisis detallado de los homógrafos y
  colisiones, frase a frase, con lo que dice spaCy y lo que puntúa FLOR.

## Decisiones del usuario (30/10/2026, tarde)

- **Baseline = modelos base tal cual**: sin ajustar su prompt ni
  añadirles reglas; la pregunta es si nuestro sistema mejora lo que ya
  existe. Se evalúan en el **benchmark manual mezcla (458)**, el de
  evaluación. La lista de modelos se decide más adelante. Esto sustituye
  lo de "Prompt" y "Benchmarks y métricas" de la sección A.
- **Estructura**: paquete `avlizador` con `traductor` y `grau_dialectal`,
  y una carpeta de datos con el léxico y los benchmarks.
- **Licencia**: probablemente Creative Commons 4.0 (por confirmar).
- **Benchmarks del BOE**: se suben todos, también los completos.
- Antes de seguir: documentar la ejecución de `avalua_sistema_final.py`
  (hecho) y hacer el commit.

## Orden y prioridad

| Orden | Tarea | Prioridad | Por qué en este orden |
|---|---|---|---|
| 0 | Commit de todo lo pendiente (23-30/10) | **Bloqueante** | Antes de mover carpetas hay que tener un punto de vuelta limpio en git |
| 1 | B1. Decidir la estructura y mover los benchmarks a una carpeta en git | **Alta** | A y B dependen de ella: Abaco usa el clon de git y los benchmarks del BOE hoy no están en git (`dades/boe/` está en `.gitignore`) |
| 2 | A. Preparar y lanzar el baseline en Abaco | **Alta** | Tarda horas en la cola y en ejecutarse: se lanza pronto y se trabaja en B mientras tanto |
| 3 | B2-B6. Paquete, CLI, tests, documentación, GitHub | **Alta** (es el entregable) | Es lo más largo; avanza mientras Abaco calcula |
| 4 | C. Trazas de FLOR | **Media** | Interno: sirve para mejorar y justificar el sistema, no bloquea la entrega. Encaja mejor con el paquete ya ordenado (la traza será una opción de la propia librería) |

Dicho de otra forma: B es lo más importante, pero primero se fija la
estructura (paso 1) para que el baseline (A) se lance sobre rutas que ya
no van a cambiar, y así A corre en paralelo con el resto de B.

---

## 0. Commit pendiente (bloqueante)

El trabajo del 23-29/10 ya está en git (commits `a68a289`-`650ee48`).
Queda lo del 30/10: TER/WER en `evalua_models.py`,
`avalua_sistema_final.py`, `resultats_benchmarks_cat_val.md` y la
documentación. Como manda CLAUDE.md, se revisa la lista con el usuario y
**el usuario hace el commit**. Sueltos a decidir: `evaluar_modelos_cambio_lexico_orden.txt`
(en la raíz), los informes del 15/10 modificados y el del 23/10.

## B. Paquete de entrega y repositorio profesional

### B1-bis. Propuesta concreta (30/10/2026, tarde; SUSTITUYE el borrador de B1 de abajo)

Se trabaja en una **rama temporal `empaquetat`** que sale de `main`
(`4684d03`); se fusiona cuando todo pase las pruebas de la lista final.

```
AVLizador/
├── pyproject.toml                 # distribución "avlizador" 1.0.0, Python >= 3.10
├── README.md · README.es.md · LICENSE (CC BY 4.0, por confirmar) · CHANGELOG.md
├── src/avlizador/                 # lo que se instala (pip install .)
│   ├── __init__.py                # API: translate_cat_val, translate_cat_val_motor,
│   │                              #      translate (val→cat), calcula_gd/gdv/gdc, __version__
│   ├── __main__.py / cli.py       # orden única: avlizador tradueix | gd | avalua
│   ├── traductor/                 # = traductor/ de ahora: rules/, model_llengua/
│   │   │                          #   (solo puntuador, punts, __init__), translate*.py
│   │   └── data/                  # lexic_general.json + conjugacions_dialectals.json (12 MB)
│   ├── grau_dialectal/            # gd.py, gdv.py, gdc.py (desde pipeline/09), imports normales
│   └── avaluacio/                 # métricas (BLEU, chrF, chrF++, TER, WER) +
│                                  #   avalua_sistema_final sobre dades/benchmarks/
├── dades/
│   ├── lexic/                     # fuentes del proveedor (ver decisión 2)
│   ├── benchmarks/                # EN GIT, con README (origen, tamaño, licencia)
│   │   ├── manual/                # mezcla 458 (evaluación), BOE 246, AVL 212
│   │   ├── curat_151/             # benchmark_corpus.json
│   │   ├── homografs/             # combinado 253 + homógrafos 98
│   │   ├── boe_dialectal/         # estricto y amplio: muestras y completos (22 MB el mayor)
│   │   └── gplsi/                 # 1.958 (CC BY 4.0, atribución del dataset)
│   └── avl/, boe/, ...            # datos brutos de ahora: siguen fuera de git, sin moverlos
├── scripts/sync_data.py           # herramienta de desarrollo: dades/lexic → src/.../data
├── tests/                         # pytest: los doctests + pruebas de las órdenes y de la API
├── documentacio/
└── pipeline/                      # registro del trabajo (01-09); sus scripts pasan a importar
                                   #   avlizador.traductor en vez de traductor
```

Puntos de la propuesta:

- **Import `avlizador.traductor` y `avlizador.grau_dialectal`** (no
  `traductor` suelto): "traductor" es un nombre genérico que puede chocar
  con otros paquetes instalados. Cambia los imports de 12 scripts de
  `pipeline/` y de los `.sh` de Abaco (cambio mecánico).
- **Diseño `src/`**: obliga a probar el paquete instalado, no la carpeta
  del repo (es como detectar que falta un JSON en la wheel).
- **Qué se queda fuera del paquete**: `traductor/llm/` (necesita Ollama;
  capa de val→cat congelada) → `pipeline/08_traduccio_corpus/postprocessat_llm/`;
  `model_llengua/avalua.py`, `genera_benchmark.py` y sus JSON →
  `pipeline/03_seleccio_de_model/` o `dades/benchmarks/homografs/`;
  `sync_data.py` → `scripts/` (lee las fuentes del repo, no sirve
  instalado). `mesura_corpus.py` y el visor del GD se quedan en
  `pipeline/09_grau_dialectal/`.
- **Dependencias** (`pyproject.toml`):
  - base: `spacy>=3.8,<3.9` y `ca_core_news_md` 3.8.0 (dependencia por
    URL de la wheel oficial de spaCy: vale para instalar desde GitHub o
    desde la wheel, no para PyPI);
  - `[ml]` (sistema principal): `torch` (CPU), `transformers>=5`,
    `huggingface_hub>=1.5,<2.0`. FLOR-760M se descarga de Hugging Face
    la primera vez (1,5 GB; documentar `HF_HOME` y el uso sin conexión);
  - `[avaluacio]`: `sacrebleu>=2.4`; `[dev]`: `pytest`.
  - Sin `[ml]`, `translate_cat_val` avisa y usa el motor solo (o falla con
    un mensaje claro: a decidir).
- **Benchmarks**: se **copian** (no se mueven) a `dades/benchmarks/`;
  los originales y los scripts que los construyen siguen donde están.

**Decisiones del usuario antes de empezar:**

1. ¿Import `avlizador.traductor` (propuesta) o `traductor` suelto?
2. **Fuentes del léxico**: ¿se mueven de
   `pipeline/02_regles_dialectals/lexic/diccionarios/` a `dades/lexic/`?
   Ojo: el compañero las edita ahí (rama `lista-lexico`); moverlas cambia
   su forma de trabajar. Alternativa: dejarlas donde están y que
   `scripts/sync_data.py` las siga leyendo de ahí.
3. ¿`translate` (val→cat, aparcado) entra en el paquete?
4. Sin `[ml]` instalado: ¿motor solo con aviso, o error?
5. ¿Una orden `avlizador` con subórdenes (propuesta) o tres órdenes
   sueltas?

**Pruebas antes de fusionar la rama**:
1. Doctests: 648/648 en el paquete instalado.
2. Mismas traducciones antes y después en todos los benchmarks: el
   manual mezcla tiene que dar 227/458, y lo mismo el resto (A/B frase a
   frase con los JSON del 30/10).
3. Instalación en un entorno nuevo (`python -m venv`, `pip install
   ".[ml]"`) en Windows y en Linux (Abaco, solo CPU), y las órdenes de
   ejemplo del README funcionan.
4. `pipeline/` sigue funcionando (`evalua_models.py`, `mesura_corpus.py`).

### B1. Estructura propuesta (borrador inicial, superado por B1-bis)

```
AVLizador/
├── pyproject.toml          # un único paquete instalable: "avlizador"
├── README.md / README.es.md
├── LICENSE                 # a decidir
├── CHANGELOG.md
├── traductor/              # sin cambios de nombre (ya se importa así)
│   └── data/               # JSON del léxico y conjugaciones (package data)
├── grau_dialectal/         # NUEVO: gd.py, gdv.py, gdc.py (desde pipeline/09)
├── benchmarks/             # NUEVO: todos los benchmarks cat→val en git
│   ├── README.md           # origen, tamaño, licencia y cómo se construyó cada uno
│   ├── manual/             # BOE 246, AVL 212, mezcla 458
│   ├── curat_151/          # benchmark_corpus.json
│   ├── homografs/          # 253 combinado + 98 homógrafos
│   ├── boe_dialectal/      # estricto y amplio (muestras de 2.000; ¿completos?)
│   └── gplsi/              # 1.958 (CC BY 4.0, con su atribución)
├── avaluacio/              # NUEVO: avalua_sistema_final.py + métricas, apuntando a benchmarks/
├── tests/                  # pytest: doctests + pruebas de humo de CLI
├── documentacio/
└── pipeline/              # se queda como registro del trabajo (01-09)
```

- **GD**: `gd.py`, `gdv.py`, `gdc.py` pasan a `grau_dialectal/` con
  imports normales (`from traductor.rules import ...`) en vez de añadir
  la raíz a `sys.path`. En `pipeline/09_grau_dialectal/` se dejan
  `mesura_corpus.py`, el visor y los README (que apuntan al paquete).
- **Benchmarks**: se **copian** a `benchmarks/` (los originales no se
  tocan, regla fija) y los scripts pasan a leer de ahí. Tamaño: los
  manuales, 151, homógrafos, gplsi y las muestras del BOE son unos pocos
  MB; los completos del BOE, a decidir.

### B2. `pyproject.toml` y dependencias

- Paquete `avlizador` (versión 1.0.0) con los subpaquetes `traductor` y
  `grau_dialectal`, y los JSON de `traductor/data/` como datos del paquete.
- Dependencias base: `spacy` y el modelo `ca_core_news_md` (la wheel se
  instala desde la URL de spaCy; documentarlo o dar un comando
  `avlizador-setup`).
- Extra `[ml]` para FLOR: `torch` (CPU), `transformers`,
  `huggingface_hub>=1.5,<2.0` (la versión que el 29/10 rompió
  transformers). FLOR-760M se descarga de Hugging Face la primera vez.
  Sistema principal = motor + FLOR, así que la instalación recomendada
  es `pip install "avlizador[ml]"`; sin el extra queda el motor solo.
- Extra `[dev]` para la evaluación: `sacrebleu`, `pytest`.
- Probar la instalación en un entorno limpio (venv nuevo), solo CPU.

### B3. CLI

- `avlizador-tradueix` (texto, fichero o stdin → valenciano; `--motor`
  para el motor solo). Reutiliza `traductor/cli.py`.
- `avlizador-gd` (GD, GDV y GDC de un texto o fichero, con `--html`).
- `avlizador-avalua` (= `avalua_sistema_final.py` sobre `benchmarks/`).

### B4. Tests

- `pytest` que corre los doctests de `traductor/` y `grau_dialectal/`
  (hoy 648) y pruebas de humo de las tres CLI.
- Opcional: GitHub Actions en CPU (instalar, pasar los tests). Los tests
  con FLOR (1,5 GB) solo en local o marcados como lentos.

### B5. Documentación

- README principal nuevo (qué es, instalación, uso en 5 líneas,
  resultados, estructura), en catalán y castellano como ahora.
- `benchmarks/README.md` y un README por paquete.
- `CHANGELOG.md` con la v1.0.0.

### B6. GitHub

- En una rama (`entrega-v1`), revisión con el usuario y merge en `main`.
  Commits y push los hace el usuario.
- Revisar que no se suba nada sensible ni pesado; CLAUDE.md sigue en
  local (ya está en `.gitignore`).
- Etiqueta `v1.0.0`.

### Decisiones del usuario para B

1. Nombres: ¿paquete `avlizador` con `traductor` y `grau_dialectal`
   dentro, o otros nombres?
2. Licencia del código y de los datos (léxico del proveedor, textos de
   la AVL, BOE, gplsi CC BY 4.0).
3. ¿Se suben los benchmarks completos del BOE o solo las muestras de 2.000?
4. ¿El repo `transducens/AVLizador` es o será público?
5. ¿El GD se mueve fuera de `pipeline/09` (propuesta) o se queda ahí y
   solo se empaqueta?

## A. Baseline del sistema final contra LLM (Abaco)

### Qué hay ya y qué falta

- `evalua_models.py --model ollama` ya habla con Ollama, pero **su
  prompt (`SYSTEM_PROMPT_BASE`) traduce de valenciano a catalán**: hace
  falta un prompt catalán → valenciano (norma AVL).
- `comparativa_salamandraTA_gemma/comparar_salamandraTA_gemma.sh` (22/09)
  es la plantilla de SLURM con Ollama en Abaco: sirve de base, pero
  pedía 5 GPU de golpe.
- `baseline_models_llengua.sh` (29/10) es solo CPU y para los modelos que
  puntúan homógrafos, no para traducir.

### Modelos candidatos

Abaco: GPU de 11 GB (Turing, compute capability 7.5). Con Ollama en 4
bits caben modelos de hasta unos 14B.

| Modelo | Tamaño | Por qué |
|---|---|---|
| llama3.1:8b | 8B | Referencia general, ya probado |
| qwen2.5:7b | 7B | Ya probado |
| qwen2.5:14b | 14B | El mejor de las pruebas de septiembre (val→cat) |
| qwen3:8b | 8B | El de la capa de LLM de val→cat (con `/no_think`) |
| qwen3:14b | 14B | Cabe justo en 11 GB |
| gemma3:12b | 12B | Ya probado; buen catalán |
| gemma4 | ? | Comprobar en Ollama si existe y qué tamaño cabe en 11 GB |
| salamandra-7b-instruct (BSC) | 7B | Entrenado con mucho catalán y valenciano |
| SalamandraTA-7b (BSC) | 7B | Específico de traducción; necesita vLLM y 2 GPU en bf16 (o GGUF). Opcional por el gasto de GPU |
| **Apertium cat → cat_valencia** | reglas, CPU | **El competidor más directo**: traductor de reglas libre con variante valenciana (el que usa Softcatalà). Sin GPU |

Descartados: NLLB (no distingue catalán y valenciano); modelos de 27B o
más (no caben en 11 GB). Modelos por API (Claude, GPT) como techo:
opcional, envía los benchmarks a un servicio externo y cuesta dinero;
solo si el usuario lo pide.

### Cómo se ejecuta sin acaparar Abaco

- **Job array con 1 GPU por tarea y como mucho 2 a la vez**:
  `#SBATCH --array=0-8%2`, `--gres=gpu:1`. Cada tarea levanta su Ollama
  en su puerto (`--ollama-url`), aísla la GPU con
  `CUDA_VISIBLE_DEVICES`, `OLLAMA_VULKAN=0`, y la apaga al acabar.
- Apertium, en una tarea solo CPU.
- Todo desde el clon `~/scrapeo/AVLizador` (`git pull`), leyendo de
  `benchmarks/`.

### Benchmarks y métricas

- Núcleo (siempre): manual BOE, manual AVL, 151 y combinado de
  homógrafos (unas 865 frases; con un 14B, entre 30 y 60 min por modelo).
- Ampliado (opcional, horas por modelo): BOE estricto y amplio (2.000
  cada uno) y gplsi (1.958).
- Métricas: exactas, BLEU, chrF, chrF++, TER, WER y **GDV de la salida**
  (si un LLM devuelve catalán o mezcla, el GDV lo detecta aunque el BLEU
  sea alto).

### Prompt (decidir con el usuario)

- Instrucción corta en valenciano: "traduïx del català al valencià
  normatiu de l'AVL; canvia només el que siga dialectal; retorna només
  la frase".
- Opción: 2-3 ejemplos (few-shot) sacados de fuera de los benchmarks.
- La misma instrucción para todos los modelos; `temperature=0`.

### Pasos

1. Prompt cat→val en `evalua_models.py` (`--direccio cat-val` con
   `--model ollama`); prueba local con el qwen2.5:7b del portátil.
2. Adaptador de Apertium (`apertium cat-cat_valencia`), en local o en Abaco.
3. `slurm/baseline_llm_cat_val.sh` (job array, `%2`).
4. Script para combinar resultados → tabla en
   `resultats_benchmarks_cat_val.md` y un informe nuevo.

### Decisiones del usuario para A

1. La lista final de modelos (¿SalamandraTA sí o no?, ¿gemma4?).
2. ¿Zero-shot o con ejemplos?
3. ¿Solo el núcleo de benchmarks o también los de 2.000?
4. ¿Cuántas GPU a la vez como mucho? (propuesta: 2)

## C. Trazas de FLOR y spaCy en los homógrafos

**Objetivo**: para cada aparición de un homógrafo o colisión ("cop",
"nou", "manca", "calces", "gandula"...), saber qué pasó y por qué:

| Campo | Ejemplo |
|---|---|
| frase, id, benchmark | BM-AVL-191 |
| palabra y tipo de punto | "anous", `homonimia_lexica` |
| spaCy: POS, lema y rasgos morfológicos de la palabra (y de la frase entera) | NOUN, "anou", Gender=Masc |
| capa que decide | regla de spaCy (`decisio_spacy`) / FLOR / sin decisión |
| candidatos y frases completas puntuadas | "les anous" / "les nous" |
| puntuación de FLOR de cada uno (log-prob, PMI) y margen | −42,1 / −38,7; margen 3,4 < 5 |
| elegido, el del motor y la referencia | "nous" / "anous" / "anous" → **fallo** |

**Cómo**:

1. Opción `traca=` en `traductor/model_llengua` (`tradueix_cat_val_ml`
   y `puntua_punts`) que devuelva esta información sin cambiar la
   traducción (comprobar con los doctests y con los benchmarks que la
   salida es idéntica).
2. Script `traca_homografs.py`: recorre el benchmark de homógrafos (98),
   el combinado (253) y los manuales, y escribe un JSONL con una línea
   por punto.
3. Informe (Markdown o HTML) agrupado por palabra: aciertos y fallos,
   en qué capa se decide, matriz de confusión del POS de spaCy frente al
   sentido correcto, distribución de márgenes (para ver si el margen 5
   está bien puesto) y los fallos explicados uno a uno.

**Para qué sirve**: separar los fallos de spaCy (etiqueta mal) de los de
FLOR (prefiere la forma frecuente, como "colp" o "nou") y de los datos
(como el "hamaces" del 23/10), y justificar el margen y la regla de
spaCy en la documentación de decisiones (punto 4 del plan del 30/10).

**Decisión del usuario para C**: ¿informe en Markdown o página HTML
interactiva (filtros por palabra o por capa)?
