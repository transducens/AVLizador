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
- **Qué tiene que poder hacer**: pegar o subir un texto, obtener la
  traducción, ver qué se ha cambiado y por qué, copiar o descargar el
  resultado, y comprobar el Grau Dialectal de un texto.
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
| `translate_cat_val(text)` | `avlizador.traductor_cat_val` | traducción final (motor + FLOR) |
| `translate_cat_val_motor(text)` | ídem | modo rápido sin FLOR |
| `tradueix_cat_val_ml(text, model)` | `…model_llengua` | traducción **y** las palabras ambiguas con sus candidatos y quién decidió (spaCy, FLOR, motor) |
| `calcula_gd`, `calcula_gdv`, `calcula_gdc` | `avlizador.grau_dialectal` | GD del texto de entrada y de la salida |
| `resalta_html(text)` | `grau_dialectal.gd` | marca las palabras valencianas/catalanas (hay que revisar su HTML para la accesibilidad) |
| CLI `avlizador tradueix / gd / avalua` | `avlizador.cli` | no se usa en la web; útil dentro del contenedor |

Lo que **falta** en el paquete para una buena interfaz:

- La lista de **cambios palabra a palabra** (qué palabra catalana pasó a
  qué valenciana y qué regla lo hizo). Hoy solo lo saca
  `pipeline/03_seleccio_de_model/traces/traca_traduccio.py`, fuera del
  paquete. Propuesta: una función pequeña en el paquete que devuelva los
  cambios (posición, original, traducción, capa), sin el detalle completo
  de las trazas.
- Partir un **texto largo** en frases/párrafos y traducirlo conservando
  saltos de línea (la CLI ya va línea a línea).

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
  servidor, y un límite de peticiones a la vez.

### Alternativas descartadas (de momento)

| Opción | Por qué no |
|---|---|
| Gradio / Streamlit | muy rápido de montar, pero poco control sobre el HTML y la accesibilidad; añade dependencias pesadas |
| React/Vue + API | más trabajo y una cadena de compilación de JavaScript que mantener, sin necesidad real para 2-3 pantallas |
| Varios contenedores (API + nginx + cola) | excesivo para un uso interno con pocos usuarios; se puede añadir nginx delante más adelante |

## 5. API (propuesta)

| Método y ruta | Entrada | Salida |
|---|---|---|
| `POST /api/tradueix` | `{text, mode: "complet"\|"motor", detall: bool}` | `{traduccio, canvis[], ambigues[], gd_entrada, gd_eixida, segons}` |
| `POST /api/gd` | `{text}` | `{gd, gdv, gdc, marcadors_occidentals, marcadors_orientals, total_paraules}` |
| `POST /api/tradueix-fitxer` | fichero `.txt` (y quizá `.docx`, decisión D6) | el fichero traducido |
| `GET /api/salut` | — | `{estat: "ok", models_carregats: bool}` (para el `HEALTHCHECK` de Docker) |
| `GET /api/versio` | — | versión del paquete, de FLOR y de spaCy |

- **Límite de longitud** por petición (p. ej. 20.000 caracteres; D5).
- `ambigues[]`: por cada palabra ambigua, los candidatos, cuál se ha
  elegido, quién ha decidido y si hay duda (margen pequeño), para que la
  interfaz pueda **avisar** y dejar elegir la otra opción.
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

1. **Traducir** (pantalla principal)
   - Área de texto de entrada (catalán) con su etiqueta visible,
     contador de caracteres y límite.
   - Botón "Traduir" (y atajo de teclado documentado, sin capturar teclas
     del lector de pantalla).
   - Interruptor "Modo ràpid (sense model de llengua)".
   - Resultado: área de texto de solo lectura + botones "Copiar" y
     "Descarregar".
   - **Cambios**: el texto traducido con las palabras cambiadas marcadas
     y, además, una **lista de cambios** ("aquest → este", "cop → vegada:
     decidit pel model de llengua"). La lista es lo que hace accesible la
     información para quien no ve el resaltado.
   - **Palabras dudosas**: aviso cuando una palabra ambigua se ha decidido
     con poca diferencia, con un botón para usar la otra opción.
   - GD de la entrada y de la salida (con una frase que lo explique, no
     solo el número).
2. **Grau Dialectal**: pegar un texto y ver GD, GDV, GDC y las palabras
   marcadas (como lista, además de resaltadas).
3. **Sobre**: qué hace el sistema, límites conocidos (homógrafos, "nou"
   como nuez…), versión, licencias y aviso de privacidad ("el texto no
   se guarda").

### 6.3 Requisitos de accesibilidad concretos

**Estructura y semántica**
- `<html lang="ca-valencia">` (o `es` en la versión castellana) y `lang`
  en los fragmentos en otro idioma: el texto de **entrada** en catalán
  (`lang="ca"`) y la **salida** en valenciano (`lang="ca-valencia"`), para
  que el lector de pantalla los pronuncie bien.
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
  feta: 3 canvis, 1 paraula dudosa".
- Errores con `role="alert"`, junto al campo, con texto que diga qué
  hacer.
- El botón se desactiva mientras traduce, pero sin quitarlo del orden de
  tabulación (`aria-disabled`), y con indicación de progreso.
- Sin límites de tiempo; si FLOR tarda, mensaje de espera.

**Color, contraste y visual**
- Contraste de texto ≥ 4,5:1 (≥ 3:1 en texto grande y en componentes de
  interfaz y gráficos).
- **El color nunca es la única señal**: los cambios se marcan con fondo
  **y** subrayado o `<mark>`/`<ins>`/`<del>`, y además van en la lista.
- Modo oscuro con `prefers-color-scheme` y contrastes revisados en los
  dos.
- Usable al 200 % de zoom y a 320 px de ancho sin desplazamiento
  horizontal (WCAG 1.4.10).
- `prefers-reduced-motion`: sin animaciones.
- Tamaño mínimo de los objetivos táctiles 24×24 px (WCAG 2.5.8).

**Contenido**
- Lenguaje claro; los términos técnicos (GD, homógrafo, model de
  llengua) explicados en la propia página.
- El resaltado de `resalta_html` se revisa: hoy usa colores; habrá que
  añadirle texto alternativo o etiquetas para que sea accesible.

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
- Variables de entorno: `AVLIZADOR_MODE` (complet/motor), `MAX_CARACTERS`,
  `OMP_NUM_THREADS` / `TORCH_NUM_THREADS` (núcleos para FLOR),
  `HF_HUB_OFFLINE=1` cuando los modelos ya estén dentro.
- Tamaño estimado: ~1,5 GB sin FLOR, ~3 GB con FLOR dentro.

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

## 8. Seguridad y privacidad

- No registrar el contenido de los textos (solo métricas: longitud,
  tiempo, errores).
- Sin llamadas externas en tiempo de ejecución.
- Límite de tamaño de petición y de peticiones simultáneas (evitar que
  un texto enorme bloquee el servicio).
- Cabeceras de seguridad (Content-Security-Policy sin JavaScript en
  línea, `X-Content-Type-Options`), sin recursos de terceros (fuentes y
  scripts servidos desde el propio contenedor: también evita llamadas
  externas).
- Si se expone fuera del equipo: HTTPS con un proxy delante (fuera del
  alcance de la primera versión).

## 9. Pruebas

- **API**: `pytest` con el cliente de pruebas de FastAPI (traducción,
  GD, límites, errores), con el modo motor para que sean rápidas y una
  prueba con FLOR marcada como lenta.
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
| 0 | Decidir las preguntas de la sección 11 | tabla rellena |
| 1 | Función de cambios palabra a palabra en el paquete + API FastAPI con pruebas | `pytest` en verde |
| 2 | Página de traducir, accesible, valenciano/castellano | pasa axe y el recorrido con teclado y NVDA |
| 3 | Pantalla de GD y "Sobre" | ídem |
| 4 | Dockerfile + compose + healthcheck; prueba sin red | `docker compose up` funciona en un equipo limpio |
| 5 | Subir ficheros (`.txt`, quizá `.docx`) | ídem |
| 6 | Documentación de instalación para la Conselleria + declaración de accesibilidad (plantilla) | revisado por el equipo |

## 11. Decisiones pendientes

| # | Pregunta | Propuesta |
|---|---|---|
| D1 | ¿FastAPI + HTML propio, o Gradio para ir más rápido? | FastAPI + HTML propio (accesibilidad) |
| D2 | ¿Modelos dentro de la imagen o en un volumen? | dentro para la Conselleria, volumen en desarrollo |
| D3 | ¿Se publica la imagen (GitHub Container Registry) o cada uno la construye? | primero construirla en local; publicar cuando esté resuelta la licencia (7.4) |
| D4 | ¿Interfaz en valenciano y castellano desde el principio? | sí |
| D5 | Límite de texto por petición | 20.000 caracteres (a medir) |
| D6 | ¿Subir `.docx` (conservando el formato) o solo `.txt`? | `.txt` en la primera versión; `.docx` después (más complejo) |
| D7 | ¿Dejar elegir la otra opción en las palabras dudosas? | sí: es donde el sistema falla y el usuario sabe el sentido |
| D8 | ¿Modo rápido (solo motor) visible para el usuario? | sí, como opción avanzada |
| D9 | ¿Rama propia para todo esto? | sí, `interfaz` desde `main` (este documento se mueve allí) |
| D10 | ¿Quién hace la prueba manual con lector de pantalla? | por decidir en el equipo |

## Registro

- 03/11/2026: primera versión del plan (rama `comet`, se moverá a la
  rama de la interfaz).
