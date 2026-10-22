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

**22/10/2026 — el filtro POS ya no se aplica a todas las formas**: lo
decide el propio diccionario. Las formas de `conjugaciones_general.json`
que traen una lectura no verbal en `morfologia` ("estat" nombre, "través",
"obres", "moro"…) solo se traducen si spaCy dice verbo; las demás, siempre
salvo que spaCy diga nombre propio ("París", "Mano"). Las 900 formas de
`verbos_diferentes_conjugados.json` (raíz distinta: signar→firmar,
prémer→polsar) siempre exigen verbo, porque ese fichero no marca
homógrafos y un error cambia la palabra entera ("els premis" → "les
polses"). Sustituye la lista a mano `SEMPRE_VERB_INVERS = {"sigui"}`.
Benchmarks: 151 146, gplsi 1479, BOE estricto 8857/9453, amplio 1200
(con la lista: 147 / 1479 / 8844 / 1199; la única frase perdida es una
cita latina, "confinis"/"finis").

**22/10/2026 — Mayúsculas y nombres propios (decisión del usuario)**: en
cat→val se traducen TODAS las palabras, también las que van en
mayúscula. No hace falta protegerlas: el diccionario no contiene
traducciones de nombres propios (los topónimos `v:top_gva` no se aplican
nunca), así que un nombre solo cambia si coincide por casualidad con una
palabra común del léxico. Revisado contra el BOE catalán completo, gplsi
y el 151, y contra una lista de nombres, apellidos y topónimos catalanes
frecuentes, los únicos casos encontrados son:
- topónimos: "les Garrigues" → "coscollars" (15 veces en el BOE, siempre
  en mayúscula), "la Noguera" → "anouer" (7), "Maó" → "rajola", "la
  Riba" → "vora", "Toro" → "bou";
- nombres de persona: "Estrella" → "Estrela", "Nen" → "Xiquet";
- nombres de instituciones y títulos que contienen palabras comunes
  ("Cementiri Britànic", "Llei d'Ús i Ensenyament").
Ningún nombre coincide con una forma verbal que se traduzca sin spaCy (las
formas verbales que no son homógrafas se frenan si spaCy dice PROPN:
"París", "Mano"). Si se quiere arreglar, lo limpio es que el proveedor
marque esos topónimos en el léxico, como ya hace con los valencianos.

**22/10/2026 — Homógrafos de cat→val**: de las entradas
`homonimia_lexica` del léxico, las que afectan a esta dirección son las
que tienen la forma ambigua en el lado catalán. Las resuelve spaCy (las
lecturas tienen categorías distintas): deu, nou/nous, manca/manques,
panotxa(es), recuita(es), reeixida(es), fartanera(es), rentadora(es)
("sota" no se aplica: el valenciano tiene dos palabras). Solo tres tienen
lecturas de la misma categoría y necesitarían un LLM: "calces" (bragues
o calces de pantaló), "gandula" y "gandules" (hamaca o dona gandula). En
los tres corpus aparecen 3 veces ("calces", en listas de aranceles del
BOE) y "gandula(es)" ninguna: hoy el motor las traduce siempre.

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

**20/10/2026**: `incoatius.py` inverso REESCRITO sin lista de raíces a mano:
decide spaCy (VERB + lema en "-ir") validado contra los infinitivos de
`conjugacions_dialectals.json` (ver el docstring del módulo para el problema
completo). gplsi 1337->1505/1958. Colisiones del
léxico resueltas con el campo `canonica` del proveedor (regla fija: en caso
de duda, la canónica; los ordinales del usuario mantienen prioridad). Nueva
`corregeix_article_abans()` (`rules/__init__.py`): "el darrer"->"l'últim",
"el batlle"->"l'alcalde".

**Deliberadamente sin implementar todavía**:
- Fase 3 de verdad: desambiguación asistida por LLM de "aquest" por
  encima del 77% (candidatos cerrados "este"/"eixe", mismo patrón que
  `pipeline/08_traduccio_corpus/postprocessat_llm/` ya usa para indicativo/
  subjuntivo).
- Homógrafo "nou"/"anou" (nuevo/nuez en catalán, 3 casos) — sin señal de
  contexto comprobada todavía.

**21/10/2026 — reglas de la guía de traducción dialectal** (medidas en los
corpus oficiales AVL + BOE, ver `documentacio/hoja_de_ruta_traductor_invers.md`):
nuevo `per_a_infinitiu.py` (C2, "per" + infinitivo -> "per a", salvo "per
haver"); "aquí" -> "ací" (D1) es un par nuevo del diccionario (E1648, sin
código); `relatiu_on.py` RETIRADO (C3: el valenciano oficial usa "on" sin
"a"). BOE (muestra de 2.000 líneas) 360 -> 368 frases exactas.
