# Hoja de ruta: interfaz web y Docker de AVLizador

Plan de trabajo (03/11/2026) para tener una interfaz web accesible y una
imagen Docker que levante todo el sistema (traductor cat→val + Grau
Dialectal) con una sola orden. Es un documento para **decidir**: cada
sección propone una opción y deja abiertas las preguntas que tiene que
contestar el equipo. Se irá actualizando a medida que se decida y se
construya.

## 1. Objetivo y para quién

- **Quién lo usa**: personal de la Administración (Conselleria) que tiene
  que pasar textos del catalán al valenciano de la AVL, sin conocimientos
  técnicos. Secundariamente, el equipo del proyecto para revisar
  traducciones.
- **Qué tiene que poder hacer**: elegir los idiomas, pegar un texto y
  obtener **solo la traducción** (como cualquier traductor: una caja de
  entrada y otra de salida, sin explicar qué ha cambiado ni cómo); y,
  en una pantalla aparte, comprobar el Grau Dialectal de un texto.
  **Decisión del usuario (03/11/2026)**: la pantalla de traducir no
  muestra nada del funcionamiento interno (ni palabras cambiadas, ni
  dudosas, ni GD).
- **Dónde se ejecuta**: en sus equipos o en un servidor interno, **solo
  CPU**, posiblemente **sin internet** (red de la Administración).

## 2. Restricciones de partida

| Restricción | Consecuencia para el diseño |
|---|---|
| Solo CPU | torch CPU (no CUDA); un solo proceso con el modelo cargado; colas cortas |
| FLOR-760M ocupa ~1,5 GB y tarda ~1,5 s por llamada | cargarlo **una vez** al arrancar; solo se llama en frases con palabras ambiguas |
| spaCy `ca_core_news_md` (~700 MB de RAM con todo cargado) | igual: una vez al arrancar |
| Memoria total estimada: 2,5-3 GB | el contenedor necesita ~4 GB de RAM |
| Textos de la Administración, posiblemente sensibles | **no guardar ni registrar los textos**; nada sale del equipo |
| Sector público | accesibilidad obligatoria (sección 6) y bilingüe valenciano/castellano |
| Licencias: spaCy `ca_core_news_md` es GPL-3.0; FLOR es Apache 2.0 derivado de BLOOM (RAIL) | ver sección 7.4 antes de publicar una imagen |

## 3. Qué ofrece ya el paquete

No hay que reimplementar nada: la interfaz y el Docker envuelven lo que
existe.

| Función | Dónde | Para la interfaz |
|---|---|---|
| `translate_cat_val(text)` | `avlizador.traductor_cat_val` | la traducción català → valencià (motor + FLOR) |
| `translate_cat_val_motor(text)` | ídem | sin FLOR, si `AVLIZADOR_MODE=motor` (no se elige en la pantalla) |
| `calcula_gd`, `calcula_gdv`, `calcula_gdc` | `avlizador.grau_dialectal` | pantalla del GD |
| `resalta_html(text)` | `grau_dialectal.gd` | pantalla del GD: marca las palabras valencianas/catalanas (6.5) |
| CLI `avlizador tradueix / gd / avalua` | `avlizador.cli` | no se usa en la web; útil dentro del contenedor |

Lo que **falta** en el paquete:

- Partir un **texto largo** en frases/párrafos y traducirlo conservando
  saltos de línea (la CLI ya va línea a línea).
- Nada más: como la pantalla de traducir solo enseña la traducción, ya
  **no hace falta** una función de "cambios palabra a palabra" (se
  propuso en la primera versión del plan y se descarta).

## 4. Arquitectura

### Opción recomendada: API + página propia

```
navegador ──HTTP──► contenedor avlizador
                    ├─ FastAPI (uvicorn, 1 proceso)
                    │   ├─ /            → la página (HTML + CSS + JS propios, sin framework)
                    │   ├─ /api/...     → JSON
                    │   └─ al arrancar: spaCy + FLOR en memoria
                    └─ paquete avlizador (el mismo de pip)
```

- **FastAPI**: ligero, documentación automática de la API (`/docs`), fácil
  de probar con `pytest`.
- **HTML propio, sin framework de interfaz**: control total del marcado
  para la accesibilidad, sin dependencias de JavaScript que mantener, y
  funciona aunque el JavaScript falle (formulario normal que se envía al
  servidor: *mejora progresiva*).
- **Un solo proceso** de uvicorn (cada proceso cargaría otra copia de
  FLOR) con las traducciones en un hilo aparte para no bloquear el
  servidor, y un límite de peticiones a la vez (abajo).

### Requisitos fijos del arranque de FastAPI (`main.py`)

Decididos el 03/11/2026; se implementan así desde la fase 1.

**1. Logs seguros.** Los textos que traducen los usuarios pueden ser
sensibles (documentos de la Administración) y **no deben aparecer nunca
en los logs**:

- El logger `uvicorn.access` va en nivel `warning`: ni una línea por
  petición, solo advertencias y errores. (uvicorn no registra los
  cuerpos de las peticiones por defecto, pero así tampoco quedan rutas,
  IP ni horas de uso.)
- Ningún middleware de logging propio registra `request.body()` ni
  ningún campo de los modelos Pydantic de entrada (`text`...).
- Las excepciones se registran sin el texto de entrada: el manejador de
  errores escribe el tipo de error y la longitud del texto, no el texto
  (un *traceback* puede llevar los argumentos de la función).
- El motivo se deja como comentario en el propio `main.py`, junto a la
  configuración.

**2. Semáforo de concurrencia.** Un `asyncio.Semaphore` creado al
arrancar la aplicación limita las traducciones simultáneas a
`MAX_TRADUCCIONS_SIMULTANIES` (variable de entorno, por defecto **2**):
con un solo proceso y FLOR en CPU, más traducciones a la vez solo
reparten los mismos núcleos y todas van más lentas.

- Se usa en `POST /api/tradueix` con `async with semaphore`; dentro, la
  traducción va a un hilo (`run_in_threadpool`) para no bloquear el
  servidor.
- **Si está lleno, no se espera: se rechaza.** `async with` por sí solo
  haría esperar la petición; por eso antes se comprueba
  `semaphore.locked()` y, si no queda hueco, se devuelve al momento
  **HTTP 429** con:
  `{"error": "El servei està ocupat. Torna-ho a intentar en uns segons."}`
  (en castellano si la interfaz está en castellano; ver 6.4).
- La interfaz muestra ese mensaje en la región de avisos
  (`aria-live`) y deja el botón de traducir activo para reintentar.

### Alternativas descartadas (de momento)

| Opción | Por qué no |
|---|---|
| Gradio / Streamlit | muy rápido de montar, pero poco control sobre el HTML y la accesibilidad; añade dependencias pesadas |
| React/Vue + API | más trabajo y una cadena de compilación de JavaScript que mantener, sin necesidad real para 2-3 pantallas |
| Varios contenedores (API + nginx + cola) | excesivo para un uso interno con pocos usuarios; se puede añadir nginx delante más adelante |

## 5. API (propuesta)

| Método y ruta | Entrada | Salida |
|---|---|---|
| `GET /api/idiomes` | — | los pares disponibles, p. ej. `[{"origen": "ca", "desti": "ca-valencia", "nom": "Català → Valencià"}]` (hoy solo uno) |
| `POST /api/tradueix` | `{text, origen: "ca", desti: "ca-valencia"}` | `{traduccio}` (solo la traducción) |
| `POST /api/gd` | `{text}` | `{gd, gdv, gdc, marcadors_occidentals, marcadors_orientals, total_paraules}` |
| `POST /api/tradueix-fitxer` | fichero `.txt` (y quizá `.docx`, decisión D6) | el fichero traducido |
| `GET /api/salut` | — | `{estat: "ok", models_carregats: bool}` (para el `HEALTHCHECK` de Docker) |
| `GET /api/versio` | — | versión del paquete, de FLOR y de spaCy |

- **Límite de longitud** por petición (p. ej. 20.000 caracteres; D5).
- **HTTP 429** en `/api/tradueix` (y en `/api/tradueix-fitxer`) cuando ya
  hay `MAX_TRADUCCIONS_SIMULTANIES` traducciones en marcha (sección 4).
- Un par de idiomas que no existe → HTTP 400 con un mensaje.
- **Preparada para más idiomas**: cada par es una entrada de un
  registro en el servidor (`origen`, `desti`, nombre que se muestra y la
  función que traduce). Hoy solo hay `ca` → `ca-valencia`
  (`translate_cat_val`); añadir un par (por ejemplo, castellano →
  valenciano cuando exista el traductor del repo de *finetuning*) es
  añadir una entrada, sin tocar la interfaz, que construye los
  selectores con `GET /api/idiomes`. El val→cat del repo existe pero
  está congelado: no se ofrece.
- Errores en JSON con un mensaje comprensible (y traducido).

## 6. Interfaz y accesibilidad

### 6.1 Normativa

- **Real Decreto 1112/2018** (accesibilidad de sitios web y aplicaciones
  del sector público) → norma **UNE-EN 301 549**, que remite a **WCAG 2.1
  nivel AA**. Objetivo del proyecto: **WCAG 2.2 AA** (incluye la 2.1).
- Hace falta una **declaración de accesibilidad** si se publica como
  servicio de la Administración (a cargo de quien lo despliegue; podemos
  dejar una plantilla).

### 6.2 Pantallas

1. **Traduir** (pantalla principal). **Solo la traducción** (decisión
   del usuario, 03/11/2026):

   ```
   ┌───────────────────────────────────────────────────────────┐
   │ Idioma d'origen [Català ▾]        Idioma de destí [Valencià ▾] │
   ├─────────────────────────────┬─────────────────────────────┤
   │ Text original               │ Traducció                   │
   │ ┌─────────────────────────┐ │ ┌─────────────────────────┐ │
   │ │                         │ │ │ (només lectura)         │ │
   │ │                         │ │ │                         │ │
   │ └─────────────────────────┘ │ └─────────────────────────┘ │
   │ 0 / 20.000 caràcters        │                             │
   ├─────────────────────────────┴─────────────────────────────┤
   │                       [ Traduir ]                         │
   └───────────────────────────────────────────────────────────┘
   ```

   - **Selectores de idioma** (`<select>` con etiqueta): hoy solo
     "Català" → "Valencià"; se llenan con `GET /api/idiomes`, así que
     cuando haya más pares aparecen solos. El de destino solo ofrece los
     destinos posibles para el origen elegido. Con un solo par, los dos
     se ven igualmente (dejan claro qué hace el traductor y la interfaz
     ya está lista para ampliarse).
   - **Caja de entrada** con su etiqueta visible, contador de caracteres
     y límite (`MAX_CARACTERS`).
   - **Botón "Traduir"**.
   - **Caja de salida** de solo lectura con la traducción. **Nada más**:
     ni palabras cambiadas, ni palabras dudosas, ni GD, ni el modo sin
     FLOR (el modo se fija con `AVLIZADOR_MODE` al desplegar).
   - Botón **"Copiar"** junto a la salida (D7, decidido): copia la
     traducción y lo anuncia ("Copiat") en la región `aria-live`.
   - En pantallas estrechas, las dos cajas una encima de la otra.
2. **Grau Dialectal** (pantalla aparte): pegar un texto y ver GD, GDV,
   GDC y las palabras marcadas (como lista, además de resaltadas; 6.5).
3. **Sobre**: qué hace el sistema, límites conocidos (homógrafos, "nou"
   como nuez…), versión, licencias y aviso de privacidad ("el texto no
   se guarda").

### 6.3 Requisitos de accesibilidad concretos

**Estructura y semántica**
- `<html lang="ca-valencia">` (o `es` en la versión castellana) y `lang`
  en las dos cajas según los idiomas elegidos: hoy la **entrada** en
  catalán (`lang="ca"`) y la **salida** en valenciano
  (`lang="ca-valencia"`); el atributo cambia con los selectores, para que
  el lector de pantalla pronuncie bien cada caja.
- Un solo `<h1>`, jerarquía de títulos sin saltos, regiones `header`,
  `nav`, `main`, `footer`.
- Enlace "Saltar al contingut" como primer elemento enfocable.
- Formularios con `<label>` asociado a cada campo; ayuda con
  `aria-describedby`; nada de solo *placeholder*.

**Teclado y foco**
- Todo usable solo con teclado, en un orden lógico.
- Foco **siempre visible** (contorno de al menos 2 px y contraste 3:1;
  WCAG 2.4.7 y 2.4.11).
- Tras traducir, el foco no salta solo; se anuncia el resultado (abajo).
- Ningún elemento con `tabindex` positivo; ninguna trampa de teclado.

**Estados y avisos**
- Región `aria-live="polite"` que anuncie "Traduint…" y "Traducció
  feta" (sin más detalle: la traducción se lee en la caja de salida).
- Errores con `role="alert"`, junto al campo, con texto que diga qué
  hacer.
- El botón se desactiva mientras traduce, pero sin quitarlo del orden de
  tabulación (`aria-disabled`), y con indicación de progreso.
- Sin límites de tiempo; si FLOR tarda, mensaje de espera.

**Color, contraste y visual**
- Contraste de texto ≥ 4,5:1 (≥ 3:1 en texto grande y en componentes de
  interfaz y gráficos).
- **El color nunca es la única señal**: en la pantalla del GD, las
  palabras marcadas llevan fondo **y** subrayado (6.5), y además van en
  una lista.
- Modo oscuro con `prefers-color-scheme` y contrastes revisados en los
  dos.
- Usable al 200 % de zoom y a 320 px de ancho sin desplazamiento
  horizontal (WCAG 1.4.10).
- `prefers-reduced-motion`: sin animaciones.
- Tamaño mínimo de los objetivos táctiles 24×24 px (WCAG 2.5.8).

**Contenido**
- Lenguaje claro; los términos técnicos (GD, homógrafo, model de
  llengua) explicados en la propia página.
- El resaltado de `resalta_html` se revisa: hoy usa solo colores; tarea
  concreta en 6.5.

### 6.5 Tarea: `resalta_html` sin depender solo del color (WCAG 1.4.1)

**Problema.** `grau_dialectal/gd.py::resalta_html()` envuelve cada
palabra marcada en `<span class="mk-occ">` (valenciana) o
`<span class="mk-or">` (catalana), y los estilos (en el informe de
`gd.py --html` y en `pipeline/09_grau_dialectal/visor_gd.html`) solo
cambian el **color**: fondo verde `#d7f3d9` / texto `#16652b` para la
valenciana y fondo naranja `#ffe2c7` / texto `#9c4b0a` para la catalana
(con sus versiones de modo oscuro). Incumple **WCAG 1.4.1** (el color no
puede ser la única señal): quien no distingue verde de naranja no ve
la diferencia.

**Cambios (fase 3, con la pantalla de GD):**

1. **HTML de `resalta_html()`**: se mantiene el color y se añaden
   - una **clase nueva** junto a la vieja: `class="mk-occ paraula-valenciana"`
     y `class="mk-or paraula-catalana"`. Se conservan `mk-occ`/`mk-or`
     para no romper el informe de `gd.py --html`, `visor_gd.html` ni el
     doctest;
   - un **texto oculto visualmente** para los lectores de pantalla:
     `<span class="visualment-amagat"> (valencià)</span>` /
     `(català)`. **No `aria-label` ni `title`**: `aria-label` en un
     `<span>` o `<mark>` no se lee de forma fiable (ARIA no deja dar
     nombre a esos elementos) y `title` solo aparece al pasar el ratón,
     no con teclado ni en el móvil. Opción del parámetro
     (`text_lector=True` por defecto) para poder quitarlo donde moleste
     (por ejemplo, en un texto con muchas marcas, en el que basta la
     lista de palabras de la pantalla de GD).

   Resultado:

   ```html
   El <span class="mk-occ paraula-valenciana">xiquet<span class="visualment-amagat"> (valencià)</span></span>
   i el <span class="mk-or paraula-catalana">nen<span class="visualment-amagat"> (català)</span></span>
   ```

   (`<span>` o `<mark>`: da igual para la accesibilidad, porque los
   lectores de pantalla no suelen anunciar `<mark>` por defecto; se
   queda `<span>` para no cambiar más de lo necesario.)

2. **Docstring de `resalta_html()`**: nota de que el HTML asume que la
   hoja de estilos de quien lo usa define `.paraula-valenciana` y
   `.paraula-catalana` con **subrayado además del color** (WCAG 1.4.1) y
   la clase `.visualment-amagat`; y doctest actualizado al HTML nuevo.

3. **CSS** de la interfaz, del informe de `gd.py --html` y de
   `visor_gd.html` (los mismos colores de ahora):

   ```css
   .paraula-valenciana {            /* fons verd + subratllat continu */
     background-color: var(--mk-occ-bg);   /* #d7f3d9; fosc #163a22 */
     color: var(--mk-occ-text);            /* #16652b; fosc #7fe39a */
     text-decoration: underline solid;
     text-decoration-thickness: 2px;
     text-underline-offset: 0.2em;
   }
   .paraula-catalana {              /* fons taronja + subratllat de punts */
     background-color: var(--mk-or-bg);    /* #ffe2c7; fosc #4a2f16 */
     color: var(--mk-or-text);             /* #9c4b0a; fosc #f0a35e */
     text-decoration: underline dotted;
     text-decoration-thickness: 2px;
     text-underline-offset: 0.2em;
   }
   .visualment-amagat {             /* només per a lectors de pantalla */
     position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
     overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
   }
   ```

   Subrayado **continuo** para el valenciano y **de puntos** para el
   catalán: se distinguen también en blanco y negro y con daltonismo.
   Grosor de 2 px para que el punteado se vea al 100 % de zoom.

**Comprobaciones:**

- Contraste: texto ≥ 4,5:1 sobre su fondo (los colores actuales: medir
  con axe en claro y oscuro) y el subrayado ≥ 3:1 sobre el fondo.
- **Que no parezcan enlaces**: en la interfaz, los enlaces llevan otro
  estilo (color propio y subrayado solo en enlaces, por ejemplo con
  icono o en negrita) y las palabras marcadas no cambian al pasar el
  ratón (`cursor: auto`, sin `:hover`).
- Leyenda visible junto al texto ("subratllat continu = valencià,
  de punts = català"): sin ella, el subrayado tampoco dice nada.
- Prueba en escala de grises (simulador de daltonismo de las
  herramientas del navegador) y con NVDA (que lea "xiquet (valencià)").

### 6.4 Idiomas de la interfaz

- Valenciano y castellano (cooficiales), con selector visible y la
  elección guardada en la URL o una cookie técnica (no hace falta aviso
  de cookies si es solo técnica).
- Textos en ficheros de traducción (JSON por idioma), no escritos en el
  HTML.

## 7. Docker

### 7.1 Imagen

- Base `python:3.12-slim`. **Construcción en dos fases** (*multi-stage*):
  una para instalar con las herramientas de compilación y otra final
  limpia.
- `pip install ".[ml]" --extra-index-url https://download.pytorch.org/whl/cpu`
  (torch **solo CPU**: ~200 MB frente a más de 2 GB con CUDA) + FastAPI y
  uvicorn.
- Usuario **sin privilegios** (no root), sistema de ficheros de solo
  lectura salvo `/tmp` y la caché de modelos.
- `HEALTHCHECK` contra `/api/salut`.
- Variables de entorno: definidas en el `Dockerfile` (`ENV`, con los
  valores por defecto) y repetidas en `docker-compose.yml`
  (`environment:`), para que se vean y se cambien sin reconstruir:

  ```yaml
  environment:
    AVLIZADOR_MODE: complet          # "complet" (amb FLOR) o "motor" (sense FLOR)
    MAX_CARACTERS: 20000             # límit de text per petició
    MAX_TRADUCCIONS_SIMULTANIES: 2   # semàfor de concurrència (vore main.py)
    OMP_NUM_THREADS: 2               # nuclis per a FLOR/PyTorch
    TORCH_NUM_THREADS: 2
    HF_HUB_OFFLINE: 1                # cap crida a Hugging Face en producció
    UVICORN_LOG_LEVEL: warning       # cap línia per petició
  ```

  | Variable | Por defecto | Qué hace | Cuándo cambiarla |
  |---|---|---|---|
  | `AVLIZADOR_MODE` | `complet` | `complet` = motor + FLOR; `motor` = solo reglas (sin cargar FLOR: ~1,5 GB menos de RAM y arranque más rápido) | `motor` en equipos con menos de 4 GB de RAM o si hace falta rapidez antes que acertar los homógrafos |
  | `MAX_CARACTERS` | 20000 | longitud máxima de texto por petición; si se pasa, HTTP 413 con un mensaje (D5) | subirla si se traducen documentos largos y el equipo lo aguanta; bajarla si las peticiones tardan demasiado |
  | `MAX_TRADUCCIONS_SIMULTANIES` | 2 | traducciones a la vez; si ya hay tantas, HTTP 429 (sección 4) | según los núcleos (regla de abajo); 1 en equipos de 2 núcleos |
  | `OMP_NUM_THREADS` | 2 | hilos de cálculo de PyTorch (y de otras librerías numéricas) | según los núcleos (regla de abajo) |
  | `TORCH_NUM_THREADS` | 2 | hilos que usa FLOR: **la lee nuestro código** y la pasa a `ModelLlengua(fils=...)` (`torch.set_num_threads`); PyTorch no la lee por sí solo | igual que `OMP_NUM_THREADS`; normalmente el mismo valor |
  | `HF_HUB_OFFLINE` | `1` | no intentar conectarse a Hugging Face; **solo con los modelos dentro de la imagen** (opción A de 7.2) | `0` con la opción B (volumen): el primer arranque descarga los modelos |
  | `UVICORN_LOG_LEVEL` | `warning` | nivel de los mensajes del servidor (arranque, avisos, errores). **No** vuelve a activar las líneas por petición: `main.py` fija `uvicorn.access` en `warning` siempre (privacidad, sección 4) | `info` o `debug` solo para depurar un problema de arranque |
  | `AVLIZADOR_DOCS` | `0` | `1` = documentación interactiva de la API en `/docs` (Swagger carga JavaScript de un CDN y queda fuera de la CSP) | solo en desarrollo; nunca en la imagen de la Conselleria |

  **Regla de los núcleos**: `MAX_TRADUCCIONS_SIMULTANIES` ×
  `TORCH_NUM_THREADS` ≤ núcleos del equipo (con los valores por defecto,
  4 núcleos). Si se pasa, las traducciones compiten por los mismos
  núcleos y todas van más lentas.
- Tamaño estimado: ~1,5 GB sin FLOR, ~3 GB con FLOR dentro.

**Tarea (fase 4): sección de variables en los README.** Una sección
"Variables d'entorn" en `README.md` y "Variables de entorno" en
`README.es.md`, con la tabla de arriba (variable, valor por defecto,
qué hace y cuándo cambiarla) y la regla de los núcleos, junto a las
instrucciones de `docker compose up`. Las dos tablas (README y
`docker-compose.yml`) tienen que coincidir: se comprueba al cerrar la
fase 4.

### 7.2 Dónde van los modelos (decisión D2)

| Opción | Ventaja | Inconveniente |
|---|---|---|
| **A. Dentro de la imagen** (se descargan al construirla) | funciona **sin internet**; una sola pieza que copiar (`docker save`) | imagen grande; redistribuye los modelos (licencias, 7.4) |
| B. En un volumen, descargados al primer arranque | imagen pequeña; no redistribuye nada | necesita internet la primera vez |

Recomendación: **A para la Conselleria** (equipos sin internet), con la
licencia resuelta; **B para desarrollo**.

### 7.3 Arranque

```bash
docker compose up            # http://localhost:8000
```

`docker-compose.yml` con el servicio, el puerto, el límite de memoria
(4 GB), el volumen de caché (opción B) y la política de reinicio. Para
equipos sin internet: `docker save avlizador:1.1.0 > avlizador.tar` y
`docker load < avlizador.tar`.

### 7.4 Licencias de una imagen pública (revisar antes de publicarla)

- **spaCy `ca_core_news_md` (GPL-3.0)**: hoy no lo distribuimos (lo
  instala pip). Si va dentro de una imagen que publicamos, **lo estamos
  redistribuyendo** y hay que cumplir la GPL-3.0 para ese componente
  (dar su licencia y el acceso a su fuente). No afecta a nuestro código
  Apache 2.0, pero hay que decirlo en `NOTICE` y en la documentación de
  la imagen. Alternativa: construir la imagen en local (cada uno se la
  hace), sin publicarla.
- **FLOR-760M**: Apache 2.0, pero derivado de BLOOM con la licencia RAIL,
  que tiene **restricciones de uso**; hay que incluirlas si se
  redistribuye.
- **XCOMET-XL** no va en la imagen (solo evaluación, CC BY-NC-SA).

### 7.5 Tarea: avisos de licencias para la imagen (con la fase 4)

Ya existen `NOTICE` (terceros: spaCy, FLOR, gplsi, BOE, AVL, salidas de
LLM, dependencias de Python) y la sección "Llicència" / "Licencia" de
los dos README. **Se amplían, no se sustituyen** (si se reemplazaran,
se perderían gplsi, BOE, AVL y las salidas de los LLM).

**1. `NOTICE`**: añadir al final un apartado para la imagen Docker y
completar las versiones reales al construirla. Texto propuesto (en
valenciano de la AVL, como el resto del fichero):

```text
Imatge Docker
=============

La imatge Docker d'AVLizador inclou, a més del codi i les dades del
projecte, estos components de tercers:

1. Model d'spaCy ca_core_news_md
   Versió: 3.8.0
   Llicència: GNU General Public License v3.0 (GPL-3.0)
   Codi font: https://github.com/explosion/spacy-models
   Qui redistribuïsca una imatge que el continga ha de complir la GPL-3.0
   per a este component (incloure'n la llicència i donar accés al codi
   font).

2. Model de llengua FLOR-760M (projecte-aina)
   Versió: [revisió de Hugging Face usada en la imatge]
   Llicència: Apache 2.0; és una adaptació de BLOOM, amb la llicència
   BigScience RAIL 1.0, que inclou restriccions d'ús:
   https://huggingface.co/spaces/bigscience/license
   Cal revisar estes restriccions abans de redistribuir la imatge o de
   canviar-ne l'ús previst.

3. Programari del servidor web
   FastAPI (MIT), Starlette (BSD-3-Clause), uvicorn (BSD-3-Clause),
   Pydantic (MIT). Vegeu els repositoris respectius.

El codi d'AVLizador es distribuïx amb la llicència Apache 2.0.
```

- Versiones: spaCy `ca_core_news_md` 3.8.0 (la de `pyproject.toml`);
  FLOR-760M, el *commit* de Hugging Face que se descargue al construir
  la imagen (fijarlo en el Dockerfile con `revision=`); FastAPI, uvicorn,
  Starlette y Pydantic, las de `pip freeze` dentro de la imagen.
- **No se incluye** (a propósito) una frase del tipo "el código de
  AVLizador no queda afectado por la GPL-3.0 por ser un programa
  independiente": AVLizador importa el modelo de spaCy en el mismo
  proceso, y si eso es o no una obra combinada es justo lo que se
  discute con la GPL. Tampoco se afirma que el uso institucional sea
  "compatible" con RAIL. **Las dos cuestiones las tiene que revisar el
  servicio jurídico de la Universidad** antes de publicar una imagen.

**2. README (valenciano y castellano)**: añadir a la sección "Llicència"
/ "Licencia" un párrafo con estas cuatro ideas:

- El código del proyecto es Apache 2.0.
- Incluye o usa componentes de terceros con otras licencias (ver
  `NOTICE`).
- Distribuir la imagen Docker con los modelos dentro obliga a cumplir la
  GPL-3.0 para `ca_core_news_md` (y a respetar las restricciones RAIL de
  FLOR).
- **Recomendación: construir la imagen en local** (`docker compose
  build`) y no distribuirla.

Texto propuesto (valenciano):

> **Imatge Docker.** El codi d'AVLizador és Apache 2.0, però la imatge
> Docker inclou components de tercers amb altres llicències (vegeu
> [`NOTICE`](NOTICE)), entre els quals el model d'spaCy
> `ca_core_news_md`, amb llicència GPL-3.0, i FLOR-760M, amb les
> restriccions d'ús de la llicència RAIL de BLOOM. Qui distribuïsca una
> imatge amb estos models dins ha de complir eixes llicències. Per això
> recomanem construir la imatge en local (`docker compose build`) en
> compte de distribuir-la.

Castellano:

> **Imagen Docker.** El código de AVLizador es Apache 2.0, pero la
> imagen Docker incluye componentes de terceros con otras licencias (ver
> [`NOTICE`](NOTICE)), entre ellos el modelo de spaCy `ca_core_news_md`,
> con licencia GPL-3.0, y FLOR-760M, con las restricciones de uso de la
> licencia RAIL de BLOOM. Quien distribuya una imagen con estos modelos
> dentro tiene que cumplir esas licencias. Por eso recomendamos construir
> la imagen en local (`docker compose build`) en lugar de distribuirla.

## 8. Seguridad y privacidad

- No registrar el contenido de los textos (solo métricas: longitud,
  tiempo, errores). Cómo se garantiza: sección 4, "Logs seguros".
- Sin llamadas externas en tiempo de ejecución.
- Límite de tamaño de petición (`MAX_CARACTERS`) y de traducciones
  simultáneas (`MAX_TRADUCCIONS_SIMULTANIES`, HTTP 429): un texto enorme
  o muchas peticiones a la vez no bloquean el servicio.
- Cabeceras de seguridad (Content-Security-Policy sin JavaScript en
  línea, `X-Content-Type-Options`), sin recursos de terceros (fuentes y
  scripts servidos desde el propio contenedor: también evita llamadas
  externas).
- Si se expone fuera del equipo: HTTPS con un proxy delante (fuera del
  alcance de la primera versión).

## 9. Pruebas

- **API**: `pytest` con el cliente de pruebas de FastAPI (traducción,
  GD, límites, errores), con el modo motor para que sean rápidas y una
  prueba con FLOR marcada como lenta. Dos pruebas fijas de los
  requisitos de la sección 4: (1) se traduce un texto con una marca
  reconocible y se comprueba que no aparece en los logs capturados
  (`caplog`), tampoco cuando la traducción falla; (2) con
  `MAX_TRADUCCIONS_SIMULTANIES=1` y una traducción en marcha, la
  siguiente petición recibe 429 con el JSON del mensaje.
- **Accesibilidad automática**: axe-core (con Playwright) y Lighthouse en
  la integración continua; cero errores de nivel A/AA.
- **Accesibilidad manual** (la automática solo detecta ~30-40 %): recorrido
  solo con teclado; NVDA en Windows y VoiceOver en macOS; zoom 200 % y
  400 %; alto contraste de Windows.
- **Docker**: construir la imagen, arrancarla sin red (`--network none`
  con la opción A) y comprobar `/api/salut` y una traducción.
- **Rendimiento**: tiempo y memoria con textos de 1, 10 y 100 frases en
  un equipo modesto (4 núcleos, 8 GB).

## 10. Fases

| Fase | Contenido | Hecho cuando |
|---|---|---|
| 0 | Decidir las preguntas de la sección 11 | tabla rellena (**hecho 04/11**, quedan D10 y D11) |
| 1 | API FastAPI (`/api/idiomes`, `/api/tradueix`, `/api/gd`, salud y versión) con el registro de pares de idiomas, y sus pruebas | `pytest` en verde (**hecho 04/11**, ver registro) |
| 2 | Página de traducir, accesible, valenciano/castellano | pasa axe y el recorrido con teclado y NVDA |
| 3 | Pantalla de GD y "Sobre"; `resalta_html` accesible (6.5) | ídem, y el resaltado se entiende sin color |
| 4 | Dockerfile + compose + healthcheck con las variables de entorno (7.1); prueba sin red; avisos de licencias en `NOTICE` y los README (7.5); sección de variables en los README | `docker compose up` funciona en un equipo limpio; las versiones de `NOTICE` y las variables de los README coinciden con la imagen |
| 5 | Subir ficheros (`.txt`, quizá `.docx`) | ídem |
| 6 | Documentación de instalación para la Conselleria + declaración de accesibilidad (plantilla) | revisado por el equipo |

## 11. Decisiones pendientes

| # | Pregunta | Propuesta |
|---|---|---|
| D1 | ~~¿FastAPI + HTML propio, o Gradio?~~ | **decidido (usuario, 04/11)**: FastAPI + HTML propio |
| D2 | ~~¿Modelos dentro de la imagen o en un volumen?~~ | **decidido (usuario, 04/11)**: dentro de la imagen (funciona sin internet) |
| D3 | ~~¿Se publica la imagen o cada uno la construye?~~ | **decidido (usuario, 04/11)**: se construye en local; no se publica hasta la revisión jurídica (D11) |
| D4 | ~~¿Interfaz en valenciano y castellano desde el principio?~~ | **decidido (usuario, 04/11)**: sí, las dos |
| D5 | Límite de texto por petición | 20.000 caracteres por defecto (`MAX_CARACTERS`; se toma la propuesta, a medir en la fase 4) |
| D6 | ¿Subir `.docx` (conservando el formato) o solo `.txt`? | `.txt` en la primera versión (se toma la propuesta); `.docx` se decide en la fase 5 |
| D7 | ~~¿Botón "Copiar" junto a la caja de salida?~~ | **decidido (usuario, 04/11)**: sí; anuncia "Copiat" en la región `aria-live` |
| D8 | ~~¿Modo rápido visible?~~ | **decidido (usuario, 03/11)**: no; solo `AVLIZADOR_MODE` al desplegar |
| D12 | ~~¿Mostrar palabras cambiadas, dudosas o GD al traducir?~~ | **decidido (usuario, 03/11)**: no; la pantalla de traducir solo da la traducción, el GD va en su pantalla |
| D9 | ~~¿Rama propia para todo esto?~~ | **hecho (04/11)**: rama `interfaz` desde `main`, con este documento |
| D10 | ¿Quién hace la prueba manual con lector de pantalla? | por decidir en el equipo |
| D11 | ¿Quién revisa las licencias de la imagen (GPL-3.0 de spaCy en el mismo proceso, RAIL de FLOR) antes de publicarla? | el servicio jurídico de la Universidad; mientras tanto, solo construcción en local (7.5) |

## Registro

- 03/11/2026: primera versión del plan (rama `comet`, se moverá a la
  rama de la interfaz).
- 03/11/2026: requisitos fijos del arranque de FastAPI (sección 4): logs
  sin los textos (`uvicorn.access` en `warning`, nada de cuerpos ni
  campos de entrada) y semáforo `MAX_TRADUCCIONS_SIMULTANIES` (2) con
  HTTP 429 si está lleno; añadidos a la API (5), las variables de entorno
  (7.1), la seguridad (8) y las pruebas (9).
- 03/11/2026: tarea de avisos de licencias de la imagen (7.5): ampliar
  `NOTICE` y la sección "Llicència" de los README (no sustituirlos),
  recomendación de construir la imagen en local; decisión D11 (revisión
  jurídica).
- 03/11/2026: tarea de `resalta_html` accesible (6.5, WCAG 1.4.1): clases
  `paraula-valenciana`/`paraula-catalana` junto a las de ahora, subrayado
  continuo/de puntos además del color, texto oculto para lectores de
  pantalla en lugar de `aria-label`/`title`, nota en el docstring.
- 03/11/2026: variables de entorno completas en 7.1 (Dockerfile +
  `docker-compose.yml`: `AVLIZADOR_MODE`, `MAX_CARACTERS`,
  `MAX_TRADUCCIONS_SIMULTANIES`, `OMP_NUM_THREADS`, `TORCH_NUM_THREADS`,
  `HF_HUB_OFFLINE`, `UVICORN_LOG_LEVEL`), con cuándo cambiar cada una y
  la regla de los núcleos; tarea de la sección "Variables d'entorn" en
  los README.
- 03/11/2026 (decisión del usuario): la pantalla de traducir es **solo
  la traducción**: selectores de idioma de origen y destino (hoy solo
  català → valencià, preparados para más pares con `GET /api/idiomes` y
  un registro de pares en el servidor), caja de entrada, botón y caja de
  salida. Fuera: lista de cambios, palabras dudosas, GD en la traducción
  y el interruptor de modo (D8 y D12 decididos; D7 pasa a ser el botón
  "Copiar"). `POST /api/tradueix` devuelve solo `{traduccio}`. El GD,
  en su pantalla.
- 04/11/2026: rama `interfaz` (desde `main`, con este documento).
  Decididos D1 (FastAPI + HTML propio), D2 (modelos dentro de la
  imagen), D3 (construir en local, no publicar), D4 (valenciano y
  castellano), D7 (botón "Copiar"); D5 y D6 con la propuesta. **Fase 1
  hecha**: subpaquete `src/avlizador/web/` (`main.py`, `idiomes.py`
  = registro de pares, `missatges.py` = mensajes en las dos lenguas,
  elegidas con `?idioma=` o `Accept-Language`), orden `avlizador web`
  (uvicorn sin log de acceso, un proceso), extra `[web]` (FastAPI +
  uvicorn; httpx en `dev`). Además de lo previsto: el error de
  validación (422) y el cuerpo no JSON (400) responden con nuestro
  mensaje y **sin repetir el texto** (la respuesta por defecto de
  FastAPI lo devuelve en `input`); `/api/gd` calcula GD, GDV y GDC con
  una sola pasada de spaCy (prueba de que coinciden con `calcula_gdv` y
  `calcula_gdc`); cabeceras de seguridad (CSP, `nosniff`,
  `no-referrer`); `/docs` apagado salvo `AVLIZADOR_DOCS=1` (Swagger
  carga JavaScript de un CDN). Pruebas: `tests/test_web.py` (13, modo
  motor, con las dos fijas de la sección 9); suite completa en verde.
  Probado en local con FLOR: arranca en ~13 s, "Un cop acabada…" →
  "Una vegada acabada…" en ~3 s, sin ninguna línea de log por petición.
  Aviso visto: sin `HF_HUB_OFFLINE=1`, transformers consulta Hugging Face
  al arrancar (en la imagen va a 1, sección 7.1).
