# Hoja de ruta: separar la web y el Docker de AVLizador

Estudio de viabilidad (26/11/2026). Describe qué hay, qué habría que mover,
cómo se conectarían los dos repositorios y qué hay que decidir.

## Estado

**Decisiones del usuario (26/11/2026)**:

- Este repositorio se queda con todo menos la web y el Docker:
  `pipeline/`, `dades/`, `documentacio/`, `scripts/` y las pruebas del
  paquete se quedan.
- El repo nuevo tiene el código de la web y el Docker, y su `Dockerfile`
  instala el paquete `avlizador`.
- **De momento no se saca release nueva**: se prueba con lo que hay.

**Fase 1 (rama `api-publica-model`)**:

- [x] Comentario de la licencia en `pyproject.toml` (decía «Apache 2.0»).
- [x] API pública:
  - `resalta_html` se exporta en `avlizador.grau_dialectal`;
  - `info_model`, `descarrega_model`, `comprova_model`, `ErrorModel` y
    `kenlm_disponible` se exportan en `avlizador.traductor_cat_val`, de forma
    perezosa (el `import` no tarda más);
  - las funciones principales, también desde `avlizador`;
  - documentada en los README (sección «API pública»);
  - `tests/test_api_publica.py` fija el contrato y comprueba que la web
    solo importa lo público.
- [x] La web importa solo de la API pública, con rutas absolutas
  (`from avlizador.… import …`): el código se puede mover tal cual.
- [x] Orden `avlizador model info | descarrega | comprova`
  (`model_llengua/descarrega.py`):
  - baja la revisión fijada en el paquete y **comprueba cada fichero** con
    el tamaño y la huella que tiene en Hugging Face;
  - una copia local de otra revisión se detecta y se vuelve a bajar;
  - `--origen` aprovecha copias locales, `--lemes` trae la opción con
    lemas y `--sense-comprovar` sirve para trabajar sin red;
  - escribe la carpeta en la salida estándar y sale con 1 si algo falla.

  Probado con Hugging Face real: copia de `docker/kenlm/`, segunda
  ejecución (no baja nada), tabla de frecuencias de otra revisión (la
  detecta y baja solo esa), descarga desde cero (12 s), caché de Hugging
  Face, sin red (error claro) y sin red con `--sense-comprovar`. 14 pruebas
  sin red.
- [x] El `Dockerfile` usa la orden nueva en lugar de
  `docker/prepara_kenlm.py`, que se borra. `KENLM_COMPROVA=0` sirve para
  probar un modelo no publicado desde `docker/kenlm/`.
- [x] **Construir la imagen** con el `Dockerfile` nuevo: hecho por el
  usuario el 27/11/2026, la web funciona. Fusionado en `main` (PR #45).
- 144 pruebas en verde (antes 124).

**Fase 2 (27/11/2026): repo de la web, HECHA.**
[`transducens/traductor-transducens-web`](https://github.com/transducens/traductor-transducens-web)
(privado de momento):

- Historial de la web y el Docker conservado con `git filter-repo` (44
  commits; los «#N» de los merges apuntan a `transducens/AVLizador#N`).
- Paquete `transducens_web` (antes `avlizador.web`) y orden
  `transducens-web` (antes `avlizador web`).
- AVLizador fijado **en un commit** (`5c42b9e`, no en la `v2.0.1`, que no
  tiene la API pública), siempre con `[kenlm]`: el modelo de lenguaje es
  obligatorio (decisión del usuario). Se instala desde el `.tar.gz` del
  commit en GitHub (sin `git` en la imagen) con `docker/instala.py`.
- Los modelos se descargan de internet al construir la imagen (decisión
  del usuario: no se copian de `docker/`).
- Imagen construida y probada por el usuario: mismas traducciones que la de
  AVLizador.
- Rama `traductors-extensibles` (1.1.0): cada traductor del registro lleva
  su frase de precarga y sus versiones; `documentacio/guia_traductors.md`
  explica cómo cambiar la versión de AVLizador y cómo añadir un traductor.
  El repo de `traductor-es-va-en` se hará público (decisión del usuario).

**Fase 3 (27/11/2026, rama `sense-web-docker`): AVLizador sin web ni
Docker.**

- Fuera `src/avlizador/web/`, `tests/test_web*.py`,
  `scripts/comprova_accessibilitat.py`, `Dockerfile`,
  `docker-compose.yml`, `.dockerignore` y `docker/LLEGIM.md`.
- Fuera la orden `avlizador web` (sin versión de aviso: decisión del
  usuario) y el extra `[web]`; `[dev]` sin las dependencias de la web.
- `tests/test_api_publica.py`: fuera la prueba de los imports de la web;
  nueva prueba de las claves de los resultados que lee la web.
- README, `NOTICE` (la sección de la imagen va al NOTICE del repo nuevo),
  guías de instalación y README del modelo: apuntan al repo de la web.
- `documentacio/hoja_de_ruta_interfaz_docker.md` se queda como histórico.
- **Versión**: el número no se cambia todavía (no hay release). Cuando se
  saque, tiene que ser **3.0.0**: desaparecen una orden y un extra.

**Ojo, «probar con la release actual»**: la `v2.0.1` no tiene la API
pública ni `avlizador model`. Mientras no haya release nueva, el repo de la
web tiene que instalar AVLizador desde una rama o un commit, no desde la
etiqueta:

```
pip install "avlizador[kenlm] @ git+https://github.com/transducens/AVLizador@main"
```

Lo más reproducible es un commit concreto: `@<hash>`.

## 0. La propuesta y el resumen

**Lo que se pide**:

- **AVLizador** se queda como **paquete de Python**: el adaptador catalán →
  valenciano, el Grau Dialectal (GD, GDV, GDC), la evaluación y la línea de
  órdenes. Sin web ni Docker.
- **Un repositorio nuevo** (nombre por decidir; aquí, «el repo de la web»)
  tiene la interfaz web, la API y el Docker. Instala AVLizador desde su
  última release y, más adelante, los demás traductores (por ejemplo, el de
  `transducens/traductor-es-va-en`).

**Resumen**: es viable y el corte es limpio.

- La web solo usa **6 funciones** de AVLizador (sección 2). No hay nada del
  paquete que dependa de la web.
- Hay tres cosas que preparar antes de separar:
  1. Una **API pública estable** en AVLizador, porque dos de esas funciones
     se importan hoy desde módulos internos.
  2. Decidir **cómo instala** el repo de la web una versión concreta de
     AVLizador. PyPI hoy no sirve: el paquete depende del modelo de spaCy
     por una URL directa, y PyPI no lo admite.
  3. Mover al paquete la **descarga del modelo KenLM**, que hoy hace un
     script del Docker.
- Los riesgos están en el futuro, no en el corte: el repo de los
  traductores es privado y todavía no tiene un traductor, y varios
  traductores en la misma imagen pueden tener dependencias que choquen.

Propuesta de orden (sección 7):

| Fase | Qué se hace | ¿Rompe algo? |
|---|---|---|
| 1 | AVLizador 2.1.0 con la API estable | no |
| 2 | Crear el repo de la web, que instala AVLizador 2.1.0 | no |
| 3 | AVLizador 3.0.0 sin web ni Docker | sí, por eso es versión mayor |

## 1. Qué hay hoy en el repositorio

| Pieza | Dónde | Va a… |
|---|---|---|
| Aplicación web y API (FastAPI): `main.py`, `idiomes.py` (registro de parejas), `missatges.py`, plantillas, CSS/JS, textos val/cas (~1.500 líneas) | `src/avlizador/web/` | repo de la web |
| Orden `avlizador web` | `src/avlizador/cli.py` | repo de la web (su propia orden o `uvicorn`) |
| Extra `[web]` y las dependencias web del extra `[dev]`; `package-data` de `avlizador.web` | `pyproject.toml` | repo de la web |
| Pruebas de la web | `tests/test_web.py`, `tests/test_web_pagina.py` | repo de la web |
| Comprobación de accesibilidad (Playwright + axe) | `scripts/comprova_accessibilitat.py` | repo de la web |
| `Dockerfile`, `docker-compose.yml`, `.dockerignore` | raíz | repo de la web |
| `docker/prepara_kenlm.py`, `docker/LLEGIM.md`, la rueda de spaCy (47 MB) y `docker/kenlm/` (163 MB, gitignorados) | `docker/` | repo de la web; la lógica de descarga, al paquete (sección 4) |
| Sección «Imatge Docker» del `NOTICE` | `NOTICE` | repo de la web |
| Secciones «Interfície web i Docker» de los README | `README.md`, `README.es.md` | repo de la web; aquí queda un enlace |
| Hoja de ruta de la interfaz | `documentacio/hoja_de_ruta_interfaz_docker.md` | se copia al repo de la web; aquí se queda como histórico |
| Traductor, GD, evaluación, órdenes `tradueix`, `gd`, `gdv`, `gdc` y `avalua`, léxico, benchmarks y `pipeline/` | — | **se quedan en AVLizador** |

## 2. Qué usa la web del paquete (el contrato)

| Lo usa para | Hoy lo importa de | ¿Público? |
|---|---|---|
| Traducir (modo completo y motor) | `avlizador.traductor_cat_val.translate_cat_val`, `translate_cat_val_motor` | sí |
| Pantalla del GD | `avlizador.grau_dialectal.calcula_gd` | sí |
| Resaltar marcadores en la pantalla del GD | `avlizador.grau_dialectal.gd.resalta_html` | **no** (módulo interno) |
| Saber si KenLM está disponible y su nombre, para la página «Sobre» | `avlizador.traductor_cat_val.model_llengua.kenlm.kenlm_disponible`, `NOM_MODEL` | **no** (módulo interno) |
| Versión | `avlizador.__version__` | sí |

**Propuesta**:

- Hacer públicas las dos piezas internas: `resalta_html` en
  `avlizador.grau_dialectal` y una función `info_model()` (disponible, nombre,
  revisión de HF) en `avlizador.traductor_cat_val`.
- Escribir el contrato en el README.
- Añadir en AVLizador una prueba que importe exactamente esas funciones, para
  que el contrato no se rompa sin darse cuenta.
- **Regla de versiones**: cambiar o quitar algo del contrato exige versión
  mayor (3.0.0, 4.0.0…). Añadir cosas, versión menor.

## 3. Cómo instala AVLizador el repo de la web

| Opción | Cómo | A favor | En contra |
|---|---|---|---|
| A. Etiqueta de git | `avlizador[kenlm] @ git+https://github.com/transducens/AVLizador@v2.1.0` | Funciona ya: el repo es público y cada release tiene etiqueta | Construye desde el código fuente; necesita `git` en la imagen |
| B. Rueda en la release de GitHub | `avlizador[kenlm] @ https://github.com/transducens/AVLizador/releases/download/v2.1.0/avlizador-2.1.0-py3-none-any.whl` | Instalación rápida y siempre idéntica; la rueda es la misma que se probó | Hay que subir la rueda en cada release (a mano o con GitHub Actions) |
| C. PyPI | `avlizador[kenlm]==2.1.0` | Lo más cómodo | **Hoy no es posible**: PyPI rechaza dependencias por URL, y `ca_core_news_md` solo se instala así. Habría que instalar el modelo de spaCy aparte. Además es una publicación abierta: decisión del grupo |

**Propuesta: B**, con A mientras no haya ruedas en las releases. El paquete
pesa poco: el léxico y las conjugaciones son unos 22 MB, y el modelo KenLM no
va dentro, se baja de Hugging Face.

**«La última release»**: conviene **fijar la versión exacta** (`==2.1.0`) y
subirla a propósito, en vez de instalar siempre la más nueva. Si no, la imagen
cambia sola cada vez que se construye y no se sabe qué versión hay en
producción. Para no olvidarse de actualizar, Dependabot o Renovate pueden
abrir un PR en el repo de la web con cada release nueva de AVLizador.

## 4. El Docker en el repo de la web

- La imagen instala `avlizador[kenlm]` en la versión fijada (sección 3) y la
  web con sus dependencias. Lo demás es como hoy: `build-essential` para
  compilar `kenlm`, el usuario sin privilegios y la comprobación de salud.
- **Modelo KenLM**: hoy lo prepara `docker/prepara_kenlm.py`, que lee de
  AVLizador el repositorio y la revisión de HF (`REPO_HF`, `REVISIO_HF`). Se
  propone pasar esa lógica al paquete, como orden
  `avlizador model descarrega --desti /opt/kenlm [--lemes]`. Así el repo de la
  web no toca constantes internas y **la revisión del modelo sigue atada a la
  versión del paquete**, que es como está pensado (tabla «Quina versió del
  model baixa cada versió del paquet» del README).
- La rueda de spaCy local (`docker/*.whl`) se mueve tal cual. Sirve para
  construir sin descargarla.
- `docker/kenlm/` (los ficheros del modelo, para no bajarlos) también se
  mueve. Sigue gitignorado.

## 5. Varios traductores en el mismo repo de la web

- El registro de parejas (`idiomes.py`, `Parell`: origen, destino, nombres,
  función `tradueix(text) -> str`, tipo `idioma`/`dialecte`) ya está pensado
  para esto. Con él, añadir un traductor es añadir una entrada.
- **Cada traductor, un paquete instalable** con una función de traducción. La
  web no sabe nada de cómo traduce cada uno.
- **Situación del repo de los traductores**:
  - `transducens/traductor-es-va-en` **no es público**: la API de GitHub da
    404 sin credenciales. Para instalarlo al construir la imagen hará falta
    un token con BuildKit (`--secret`) o hacerlo público.
  - Hoy solo tiene los scripts de descarga de los datos; todavía no hay
    traductor.
- **Riesgos cuando llegue**:
  - Un traductor neuronal es-va probablemente necesitará `torch` y un modelo
    de cientos de MB o más. Eso choca con «solo CPU, pocos recursos» y hace
    crecer la imagen (la 2.0.1 pesa 733 MB).
  - Puede pedir versiones de dependencias incompatibles con spaCy 3.8.
- **Propuesta**: empezar con una sola imagen y los traductores como paquetes.
  Si chocan en dependencias o en memoria, separar cada traductor en su
  contenedor y que la web les llame por HTTP con `docker compose`. El
  registro de parejas sirve igual en los dos casos: `tradueix` puede ser una
  llamada local o una petición.

## 6. Licencias

- AVLizador es **GPL-2.0-or-later** (PR #44). Si la web lo importa en el mismo
  proceso, el conjunto que se distribuya (por ejemplo, la imagen) queda bajo
  la GPL. El código del repo de la web tiene que ser compatible: lo más
  sencillo es ponerle también GPL-2.0-or-later. FastAPI, Starlette y Jinja2
  son MIT o BSD, compatibles.
- El `NOTICE` de la imagen (spaCy GPL-3.0, KenLM LGPL-2.1, modelo CC BY 4.0,
  imagen base) se va con el Docker. El `NOTICE` de AVLizador se queda con lo
  que lleva el paquete.
- Cada traductor que se añada trae su licencia. Hay que revisarla antes de
  meterlo en la imagen.
- Sigue pendiente la revisión jurídica de la imagen (D11 de la hoja de ruta
  de la interfaz).

## 7. Plan por fases

**Fase 0. Decisiones** (sección 10).

**Fase 1. AVLizador 2.1.0, sin romper nada**

- API pública de la sección 2 y prueba del contrato.
- Orden `avlizador model descarrega`. `docker/prepara_kenlm.py` pasa a usarla.
- Corregir el comentario de `pyproject.toml`, que todavía dice «Apache 2.0».
- Release 2.1.0 con la rueda adjunta (opción B).
- La web y el Docker siguen aquí y funcionan igual.

**Fase 2. Repo de la web**

- Crearlo en `transducens`. Copiar `src/avlizador/web/` (como paquete propio,
  por ejemplo `transducens_web`), las pruebas, la comprobación de
  accesibilidad, el Docker y su parte del `NOTICE`.
- **Conservar el historial** de esos ficheros con `git filter-repo`, para que
  no se pierda cómo se llegó a cada decisión (accesibilidad, privacidad de
  los registros, límite de traducciones simultáneas).
- Depende de `avlizador[kenlm]==2.1.0`.
- **Comprobar que es equivalente**:
  - las pruebas de la web en verde;
  - axe sin problemas;
  - la imagen nueva da las mismas traducciones que la `avlizador:2.0.1` en el
    manual y en los homógrafos;
  - la misma página «Sobre» y las mismas variables de entorno.

**Fase 3. AVLizador 3.0.0, solo paquete**

- Quitar todo lo de la sección 1 que va al repo de la web, y la orden
  `avlizador web` (o dejarla una versión que avise de dónde está ahora).
- README, `NOTICE` y guías: la web y el Docker, con un enlace al repo nuevo.
- Es versión mayor porque desaparecen el extra `[web]` y la orden.

**Fase 4. Segundo traductor**

- Cuando exista el traductor es-va: empaquetarlo, añadir su pareja al
  registro y resolver el acceso al repo privado y el tamaño (sección 5).

## 8. Qué cambia para cada uno

| Quién | Hoy | Después |
|---|---|---|
| **Conselleria** (solo CPU, Windows) | Imagen Docker construida desde AVLizador | Imagen construida desde el repo de la web, con las mismas pantallas y la misma API |
| Quien usa el paquete en Python o en la línea de órdenes | `pip install avlizador[kenlm]` | Igual. En Windows `kenlm` sigue sin instalarse: sin Docker, solo el motor |
| Desarrollo de AVLizador | Cada cambio del traductor sale en la web al reconstruir | Sale cuando el repo de la web sube de versión. Es más control, pero un paso más |

## 9. Riesgos

1. **Dos repositorios que mantener**, con una release de AVLizador antes de
   que la web vea cada cambio. Se mitiga con la versión fijada y un PR
   automático de actualización.
2. **Romper la API sin darse cuenta.** Se mitiga con la prueba del contrato
   (sección 2) y la regla de versiones.
3. **Repo de los traductores privado** al construir la imagen (sección 5).
4. **Choque de dependencias o de memoria** entre traductores (sección 5).
5. **La guía de instalación para la Conselleria** (fase 6 de la hoja de ruta
   de la interfaz, sin hacer) pasa a escribirse en el repo de la web.

## 10. Decisiones pendientes

| # | Decisión | Propuesta |
|---|---|---|
| D1 | Nombre y visibilidad del repo de la web | En `transducens`, público como AVLizador |
| D2 | Cómo se instala AVLizador | Rueda en la release (B); etiqueta de git (A) mientras tanto |
| D3 | ¿Versión fija o siempre la última? | Fija, con PR automático de actualización |
| D4 | API pública (sección 2) | Hacer públicas `resalta_html` e `info_model()` |
| D5 | ¿Conservar el historial de la web? | Sí, con `git filter-repo` |
| D6 | Licencia del repo de la web | GPL-2.0-or-later |
| D7 | `avlizador web` en la 3.0.0 | Quitarla, o dejarla una versión que avise |
| D8 | Varios traductores: ¿una imagen o un contenedor por traductor? | Una imagen al principio; separar si chocan |
| D9 | Acceso a `traductor-es-va-en` (privado) | Token en la construcción, o hacerlo público cuando tenga traductor |
| D10 | ¿PyPI en el futuro? | No por ahora (dependencia por URL de spaCy) |

## 11. Comprobaciones antes de decidir

- [ ] Construir la rueda de AVLizador **sin** `avlizador/web` y comprobar que
      se instala en un entorno limpio y que `tradueix`, `gd` y `avalua`
      funcionan.
- [ ] `pip install "avlizador[kenlm] @ git+https://github.com/transducens/AVLizador@v2.0.1"`
      en Linux (o en un contenedor): ¿instala bien, con el modelo de spaCy?
- [ ] Prueba de concepto del repo de la web en local: la web copiada, con
      AVLizador instalado desde la etiqueta, y las pruebas de la web en
      verde.
- [ ] Construir la imagen desde la prueba de concepto y comparar las
      traducciones con `avlizador:2.0.1`.
- [ ] Preguntar el estado y el plan de `traductor-es-va-en`: tipo de modelo,
      tamaño, si necesita GPU y si será público.
