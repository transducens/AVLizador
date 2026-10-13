*[Llegeix en català](README.md)*

# `cat_val/` — dirección inversa (català → valencià)

Dirección inversa del motor de reglas: catalán oriental (norma IEC) →
valenciano occidental (norma AVL/GVA). Compañera de `traductor/rules/val_cat/*.py`
(la dirección original, val→cat), que se queda exactamente igual, sin
tocar. Ver `documentacio/hoja_de_ruta_traductor_invers.md` (raíz del
repositorio) para el razonamiento completo, las cifras reales que
justifican cada decisión, y el estado de cada fase.

## Por qué existe como paquete aparte, no como un flag

Invertir la dirección NO es "la misma regla al revés" en la mayoría de
los casos — la lógica concreta cambia de verdad (ver la hoja de ruta
para los casos exactos: la colisión indicativo/subjuntivo de 3ª plural
desaparece en esta dirección, pero aparecen otras nuevas como
"aquest"→"este"/"eixe"). Mezclar las dos direcciones en el mismo fichero
con condicionales habría hecho el código menos legible, no más — cada
regla de aquí es un fichero propio, auditable de forma independiente.

## Qué se reutiliza y qué se copia

**Reutilizado directamente, sin duplicar**:
- `Token`, `tokenize`/`detokenize` y todos los helpers de
  `rules/__init__.py` (`separa_prefix_elidit`, `aplica_amb_prefix_elidit`,
  `corregeix_determinant_abans`...).
- `pos_tagger.py` (spaCy) — sin cambios, y con MÁS fiabilidad aquí que en
  val→cat, porque la entrada ya es catalán real (el idioma en el que
  `ca_core_news_sm` está entrenado).
- Los mismos ficheros de datos de `traductor/data/*.json` — cada entrada
  ya trae los dos campos (`valenciano`/`catalan`), así que no hace falta
  ningún fichero nuevo, solo cargadores nuevos que indexan por el otro
  campo.

**Nuevo, con estructura similar pero lógica propia** (cada fichero
explica en su docstring si "copia" el patrón del equivalente val→cat o
si la lógica es genuinamente distinta): `engine.py`, `lexic.py`,
`conjugacions_dict.py`, `possessius.py`, `numerals.py`, `demostratius.py`,
`accentuacio.py`, `concordanca_dos_dues.py`, `preposicions_locucions.py`.

## Estado actual (13/10/2026) — Fase 2 de la hoja de ruta

**113/151 (74,8%) frases exactas, BLEU 97,72, chrF 99,17**, midiendo
contra el mismo benchmark de 151 frases (campo `oriental` como entrada,
`occidental` como referencia; `evalua_models.py --model traductor
--direccio cat-val`). 485/485 doctests en verde.

**Un hallazgo importante corrigió la hoja de ruta sobre la marcha**: se
pensaba que el filtro POS (spaCy) casi no haría falta en esta dirección,
porque el problema "persones"/"personis" es asimétrico. Cierto para ESE
caso concreto, pero midiendo contra el benchmark aparecieron otras
colisiones con verbos normales (no raros): "moro" (catalán, "jo moro" de
"morir") colisionaba con "moro" dentro de "blat de moro"; "través" con
una forma de "travar"; "signes" con "tu signes" de "signar". El filtro
POS sí hace falta — implementado en `conjugacions_dict.py`.

**"aquest"→"este"/"eixe" (resuelto parcialmente, 13/10/2026)**: se probó
primero dejarlo sin tocar (preferir falso negativo) — el benchmark se
HUNDIÓ de 92 a 44/151 (107 apariciones, la mayoría del corpus). Medido
con `difflib` palabra a palabra sobre las 151 frases: 40/52 casos reales
quieren "este", 12/52 "eixe" (~77%/23%). Se implementó "aquest"→"este"
como DEFAULT MEDIDO, no una suposición — queda un 23% de error conocido
y aceptado, pendiente de la Fase 3 (LLM) para superarlo.

**Implementado el 13/10/2026** (antes "deliberadamente sin implementar",
ver hoja de ruta para el detalle completo de evidencia de cada uno):
`incoatius.py` inverso (lista cerrada de 7 raíces verbales evidenciadas:
establir/servir/aconseguir/requerir/oferir/exhaurir/coincidir),
`relatiu_on.py` inverso (8/8 casos reales quieren "on"→"a on", 2
excepciones de construcciones de énfasis temporal aceptadas), léxico
multi-palabra catalán ("blat de moro"→"dacsa" y 6 pares más, con
concordancia de género invertida), exclusión de "ensenyament" (5/6 casos
reales lo querían sin tocar), y la locución "per a acabar"→"per acabar".

**Deliberadamente sin implementar todavía**:
- Fase 3 de verdad: desambiguación asistida por LLM de "aquest" por
  encima del 77% (candidatos cerrados "este"/"eixe", mismo patrón que
  `08_traduccio_corpus/postprocessat_llm/` ya usa para indicativo/
  subjuntivo).
- Homógrafo "nou"/"anou" (nuevo/nuez en catalán, 3 casos) — sin señal de
  contexto comprobada todavía.
