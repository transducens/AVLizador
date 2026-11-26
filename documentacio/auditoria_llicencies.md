# Licencias de AVLizador (02/11/2026)

Antes de publicar AVLizador con **Apache 2.0** (propuesta del grupo) se
revisó qué herramientas, modelos y datos de terceros usa o incluye, y si
alguno impone restricciones. La revisión se hizo con los metadatos de los
paquetes instalados, las fichas de los modelos en Hugging Face, los
avisos legales de las fuentes y la lista de ficheros de git. El
repositorio `transducens/AVLizador` es público en GitHub.

## Decisiones (02/11/2026)

| Elemento | Licencia o situación | Decisión |
|---|---|---|
| Código (`src/`, `scripts/`, `tests/`, `pipeline/`) | Propio | **Apache 2.0** (`LICENSE`) |
| Léxico (`dades/lexic/` y su copia en el paquete) | Propio: lo recopilamos y revisamos a mano en el equipo | **Apache 2.0** |
| Benchmarks y resultados propios | Propios | **Apache 2.0** |
| Textos de la web de la AVL (benchmark AVL, `pool_avl`, `dades/sintetic/`) | Textos públicos y disponibles | Se redistribuyen citando la fuente |
| Textos del BOE | Sin propiedad intelectual (art. 13 de la Ley de Propiedad Intelectual) y reutilización permitida (condiciones del BOE, 27/06/2024) | Se redistribuyen citando la fuente |
| Dataset gplsi | CC BY 4.0 | Se redistribuye con su licencia y su cita |
| Modelo de spaCy `ca_core_news_md` | **GPL 3.0** (heredada del corpus AnCora) | **Se mantiene con su licencia**: es una dependencia, no se incluye; documentado en `NOTICE` y en los README |
| FLOR-760M | Apache 2.0, adaptación de BLOOM-1.1B (BigScience RAIL 1.0) | Se mantiene; no se incluye (se descarga de Hugging Face); documentado en `NOTICE` |
| Salidas de LLM en los resultados | Qwen, Mistral y Salamandra: Apache 2.0; Gemma: Gemma Terms of Use; Llama 3.1: Llama 3.1 Community License | Se redistribuyen como resultados de evaluación; documentado en `NOTICE` |
| Dependencias de Python | MIT, Apache 2.0 y BSD | Sin restricciones |
| **Gramáticas GNV (AVL) y GEIEC (IEC) completas** | Obras protegidas, sin licencia que permita redistribuirlas | **Fuera de git** desde el 02/11 (`.gitignore`); se quedan solo en local |

## Qué supone la GPL del modelo de spaCy

- Nuestro código puede ser Apache 2.0: se puede combinar con GPL 3.0, y
  el paquete no incluye el modelo (lo declara como dependencia y pip lo
  descarga del repositorio de spaCy).
- Quien redistribuya el conjunto (una imagen o un instalador con todo
  dentro) tiene que cumplir la GPL 3.0 **para ese modelo**.
- Lo que produce el modelo (las etiquetas gramaticales) no queda bajo la
  GPL: no afecta a benchmarks, resultados ni traducciones.
- No hay ningún modelo catalán de spaCy con licencia permisiva, porque
  todos se entrenan con AnCora.

## Hecho

- `LICENSE` con el texto oficial de Apache 2.0 (descargado de apache.org).
- `NOTICE` con la autoría, los datos propios y cada pieza de terceros
  con su licencia.
- `pyproject.toml`: `license = "Apache-2.0"` y `license-files`.
- Sección de licencia de los README (raíz en valenciano y castellano, y
  `dades/benchmarks/`).
- GNV y GEIEC fuera de git (`git rm --cached`, en `.gitignore`); los
  ficheros siguen en local para `mesura_corpus.py` y la documentación,
  y el README de `docs_gramatica/` explica cómo generarlos.

## Historial y versiones

- **No se reescribe el historial de git** (decisión del usuario,
  02/11/2026): las dos gramáticas siguen en los commits anteriores al
  02/11 y en el zip de código fuente del release `v1.0.0`, pero dejan de
  estar en la versión actual.
- La licencia sale con la versión **1.0.1** (`pyproject.toml`,
  `avlizador.__version__`). El release `v1.0.0` no se modifica, porque una
  versión publicada no debe cambiar; el código del traductor y del GD es
  el mismo en las dos.

## Cambio a GPL-2.0-or-later (26/11/2026)

- **Motivo**: el diccionario morfológico catalán
  (`dades/lexic/catalan_sin_top_loc_prefijos_participios.txt`, que usa la
  regla de concordancia de género desde la 2.0.0) es la expansión del
  diccionario de Apertium ([`apertium-cat`](https://github.com/apertium/apertium-cat)),
  con licencia **GPL 2.0** (su `COPYING`). Va dentro del paquete y de la
  imagen Docker, así que AVLizador no puede seguir con Apache 2.0, que no
  es compatible con la GPL 2.0.
- **Decisión del usuario: GPL-2.0-or-later** («versión 2 o posterior»), no
  «solo la 2»: es compatible con Apertium y también con el modelo de spaCy
  `ca_core_news_md` (GPL-3.0) que va en la imagen Docker. La «solo 2» no
  lo es con la GPL-3.0.
- `apertium-cat` no dice en sus ficheros si es «solo la 2» o «2 o
  posterior» (Debian lo empaqueta como GPL-2+ en las versiones recientes);
  en los dos casos se puede usar en un proyecto GPL-2.0-or-later.
- Cambiado: `LICENSE` (texto de la GPL v2 de la FSF), `pyproject.toml`
  (`license = "GPL-2.0-or-later"`), `NOTICE` (cabecera, punto 8 de
  Apertium, final), los dos README, `dades/benchmarks/README.md` y la
  página «Sobre» de la web.
- Las versiones publicadas hasta la **2.0.1** siguen con Apache 2.0 (una
  versión publicada no cambia). Los datasets y el modelo de Hugging Face
  tienen su propia licencia (CC0 / CC BY 4.0) y no cambian.
- Pendiente: confirmar con el compañero el origen exacto del diccionario
  (versión de `apertium-cat`) y que el grupo está de acuerdo con el cambio.
