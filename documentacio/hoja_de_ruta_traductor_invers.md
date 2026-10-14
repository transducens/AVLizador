> **⚠️ FICHERO RECONSTRUIDO el 14/10/2026** tras un borrado accidental
> del original. El fichero nunca estuvo en git (salía como `??` en
> `git status`, nunca se comiteó), así que no había ningún historial del
> que recuperarlo — no estaba tampoco en la papelera de reciclaje de
> Windows. Esta versión combina fragmentos literales leídos directamente
> de este mismo fichero más temprano en la sesión del 14/10/2026 (antes
> de que se borrara) con los resúmenes equivalentes de `CLAUDE.md`.
> **Es probable que falten secciones intermedias** que no se citaron en
> ningún sitio (en concreto: el detalle completo de la Fase 1 y buena
> parte del detalle fino de la categorización D/E/F/G). Si encuentras
> una inconsistencia entre esto y lo que recuerdes del original, confía
> en el código y el benchmark reales, no en este documento.

# Hoja de ruta: traductor invers (cat→val)

## Fases del plan original

**Fase 1 — Esqueleto**: estructura `traductor/rules/cat_val/` simétrica
a `val_cat/`, reutilizando los mismos ficheros de datos
(`conjugacions_dialectals.json`, `lexic_mauricio.json`, etc.) indexados
al revés.

**Fase 2 — Casos curados pequeños**: posesivos (fix de número),
numerales (excluir "vuitavat", igual que en la dirección original),
demostrativos (`aqueix`→`eixe` sin ambigüedad, el resto pendiente de
fase 3), preposiciones (reversar las 5 locuciones de
`preposicions_locucions.py` una a una, no con un flip automático — ya
se vio que la dirección no es simétrica ni siquiera dentro de la misma
frase — **nota 14/10/2026: ese módulo entero se eliminó después, ver
`CLAUDE.md`, no generalizaba fuera del benchmark**).

**Fase 3 — Desambiguación genuina**: "aquest"→"este"/"eixe" y cualquier
otro caso real que aparezca al medir contra el benchmark + BOE. Empezar
con un valor por defecto curado (el más frecuente) y medir cuánto se
equivoca antes de decidir si hace falta LLM — mismo criterio de
"no generalizar sin evidencia".

**Fase 4 — Validación cruzada con el corpus BOE**: el BOE ya es paralelo
en los dos idiomas — validación a gran escala equivalente a la hecha con
el benchmark de 151, pero con mucho más volumen.

## Estado tras la Fase 2 (13/10/2026)

+21 sobre el 92/151 con el que empezó la sesión, cero regresiones en
cada paso: corregido un bug real donde "aquest" se resolvía por una vía
accidental en vez de por `demostratius.py`; medido que dejarlo sin tocar
hunde el benchmark a 44/151, así que se implementó "aquest"→"este" como
DEFAULT MEDIDO (77% de aciertos reales, no una suposición);
`relatiu_on.py` inverso (8/8 casos reales); `incoatius.py` inverso
(lista cerrada de 7 raíces verbales evidenciadas: establir/servir/
aconseguir/requerir/oferir/exhaurir/coincidir); léxico multi-palabra
catalán ("blat de moro"→"dacsa" y 6 pares más); concordancia de género
invertida (reutilizando `corregeix_determinant_abans`); exclusión de
"ensenyament" del léxico general (5/6 casos reales lo querían sin
tocar); "per a acabar"→"per acabar" (6ª locución fija, **retirada
después el 14/10/2026 junto con el resto de `preposicions_locucions.py`**).

Más tarde el mismo día, +4 más (113→117): homógrafo "nou"/"anou"
resuelto (primer uso real del mecanismo de categoría gramatical, ver
abajo) — el filtro POS distingue bien el sentido ADJ ("new", 3/3 casos
reales), pero el sentido NOUN ("walnut") no se distingue fiablemente
("una nou" sale ADJ también), así que el filtro en la práctica bloquea
casi siempre la conversión a "anou". Aceptado conscientemente: no hay
ningún caso real en el benchmark que necesite el sentido walnut, así
que se prefiere el falso negativo. Mismo mecanismo de filtro POS que ya
usa `conjugacions_dict.py` (persones/moro/través/signes), ahora también
en `cat_val/lexic.py`. Bug real en `relatiu_on.py` corregido ("per a on"
doblaba la "a"). "qué"/"què" excluido del léxico general (+3 de +4, -1
regresión aceptada en RC055).

## Fase 3 (LLM para "aquest") — implementada, medida, descartada (13/10/2026)

Construido `08_traduccio_corpus/postprocessat_llm/compara_demostratius_invers.py`
(criterio + vía C, reutilizando `crida_ollama` de `compara_postprocessat.py`)
y `benchmark_demostratius_invers.py` (replica el motor `cat_val`, mismo
patrón que `benchmark_integrat.py`). Criterio escrito tras revisar a
mano 6 casos reales (RC021/RC047/RC066/RC079/RC086/RC090): el patrón NO
es proximidad física parlante/oyente (teoría clásica), es REFERENCIA
discursiva (si lo mencionado ya apareció antes en el discurso, tiende a
"eixe"; si es nuevo/inmediato, "este"). Un caso (RC086, 2ª aparición) es
genuinamente mixto, con "eixe" y "este" distintos en la misma frase. Un
caso (RC090, 1ª ocurrencia) no se puede juzgar bien porque es la primera
palabra de la frase y probablemente es anafórica a la frase ANTERIOR,
que el benchmark no incluye (limitación de evaluar frases sueltas, no un
fallo del criterio).

**Resultado del run completo (151 frases, 82 apariciones reales,
qwen2.5:14b local)**: **el LLM EMPEORA el resultado** — 113/151 (solo
default) → 98/151 (default+LLM), acierto real 44/73 (60,3%), peor que
el 77% del default. Error de método identificado: la validación con los
6 casos (los que ya se sabía que fallaban con el default) estaba sesgada
hacia el caso minoritario — sobre la distribución real, dominada por
"este", el criterio es demasiado permisivo y dispara "eixe" con
cualquier conexión remota a algo ya mencionado. **No se integra en
ningún sitio del motor** — se queda como script de prueba documentado,
no como parte de la Fase 3 activa. Si se retoma, el criterio necesita
rehacerse exigiendo señal mucho más explícita antes de desviarse de
"este" (y volver a medir contra el benchmark completo, no una muestra
sesgada, antes de sacar ninguna conclusión).

**Actualización 14/10/2026** (ver `CLAUDE.md` para el detalle completo):
se decidió aparcar esta fase por ahora en las dos direcciones del motor.
Cuando se retome, usar **qwen3** en vez de `qwen2.5:14b`, corrigiendo
los dos fallos metodológicos de arriba. Confirmado también que spaCy
(POS, `Mood`, género) NO puede resolver esta ambigüedad — es discursiva,
no gramatical.

## Mecanismo de categoría gramatical abierto (13/10/2026)

`traductor/data/categoria_gramatical_lexic.json` +
`carrega_categoria_gramatical()`/`pos_compatible()` en
`traductor/rules/__init__.py` — reemplaza listas de excepción sueltas
por palabra (tipo `_EXIGEIX_NOUN_CAT`) por un mecanismo único y
extensible, igual para las dos direcciones. De momento solo tiene
`"anou": "NOUN"` — el usuario clasificará la categoría gramatical de
`lexic_mauricio.json` a mano, a su ritmo. Confirmado que el problema
distinto de "spaCy se equivoca con esta grafía valenciana concreta"
(`SEMPRE_VERB` en `val_cat/conjugacions_dict.py`) NO aplica a cat→val —
la entrada siempre es catalán genuino (`EXCLUSIONS_HOMOGRAF_INVERS`/
`SEMPRE_VERB_INVERS` vacíos, cero fallos de spaCy encontrados en esta
dirección).

## Categorización completa de los 33 fallos restantes (13/10/2026)

**(A) Límite inherente del motor de reglas — 20 casos**, "aquest"
fundido en una sola grafía catalana que puede ser "este" (77%) o "eixe"
(23%) en valencià, sin señal léxica para distinguirlos: RC021, RC047,
RC066, RC067 (solo este diff), RC070, RC079, RC086, RC087, RC088, RC090,
RC093 (parcial), RC114, RC121 (variante: la referencia a veces deja
"aquesta" SIN TOCAR del todo, ni "esta" ni "eixa" — un tercer resultado
posible de la misma ambigüedad, no un bug nuevo), RC125 (x2), RC126,
RC130, RC138, RC139, más RC061/RC140 (excepción "on" temporal sin
heurística fiable). Fase 3 (LLM) ya se probó para "aquest" y empeoró —
no se puede arreglar sin entender el discurso real de la frase. No es un
problema del benchmark — la ambigüedad existe de verdad en el català de
entrada.

**(B) Trade-off de mayoría ya aceptado — 1 caso**: RC055 "qué"/"què"
(mayoría clara en el sentido contrario a RC055, recuento limpio: 3/4
casos reales).

**(C) Artefacto puro del corpus — 4 casos**: RC065 doble espacio,
RC119/RC120 texto arcaico, RC133 el català de origen tiene un error
gramatical que la referencia corrige en silencio.

**(D) Elección estilística del traductor humano — 2 casos**: RC064
"fos"/"fora", RC069 la referencia usa una raíz verbal totalmente
distinta "disfrutar" en vez de "gaudir".

**(E) Hallazgo: el diccionario no modela registro — 4 casos**: aplica
un sinónimo valenciano "popular" (cerquen, arreplega, desenrotllament,
mentres) que SÍ es un par dialectal real, pero este corpus de registro
formal/institucional prefiere la palabra compartida con el català
(RC002 "mentre", RC074, RC099, RC137) — mismo patrón que "qué"/
"ensenyament", de momento solo 1 caso cada uno, no generalizable sin
más evidencia (BOE/gplsi).

**(F) Imposible de resolver por diseño — 1 caso**: RC002 tiene la MISMA
palabra catalana "rentar" dos veces en la misma frase con DOS sentidos
distintos (metalingüístico) — ningún lookup palabra-a-palabra puede dar
dos salidas distintas para el mismo token.

**(G) Huecos reales de diccionario — 2 casos**: RC049 "galletes"/
"galetes", RC107 "ofertes"/"oferides" (participio irregular/regular).

## Por dónde seguir (tal como quedó el 13/10/2026)

Los pasos 2-4 originales (incoatius, léxico multi-palabra, relatiu_on)
ya estaban hechos tras la Fase 2. Quedaba:

1. **La Fase 3 de verdad (demostrativos "aquest" más allá del 77%)**: la
   más valiosa y la más cara, el hueco más grande conocido (~15-18 de
   las frases que fallan). Diseño recomendado, reutilizando el patrón ya
   validado de `postprocessat_llm/`: (a) detectar "aquest"/"aquesta"/
   "aquests"/"aquestes" en el texto catalán de entrada, (b) un LLM
   clasifica SOLO entre "este"/"eixe" (nunca genera la forma, igual que
   vía C ya hace con indicatiu/subjuntiu), (c) la forma final sale de la
   tabla ya conocida. Prácticamente el mismo mecanismo que
   `benchmark_integrat.py` aplicado a una ambigüedad distinta.
2. Esperar a que el usuario termine de clasificar la categoría
   gramatical del léxico (`categoria_gramatical_lexic.json`) para poder
   resolver más homógrafos como "nou"/"anou" sin listas sueltas por
   palabra.
3. De menor a mayor esfuerzo mientras tanto: RC133 ("com a", 1 caso),
   repasar los sinónimos léxicos de una sola aparición.
4. Validar todo contra un corpus mucho más grande (BOE, y después gplsi)
   para separar trade-offs de mayoría reales de ruido de una sola
   muestra pequeña.

> **Nota 14/10/2026**: los puntos 2-4 se ejecutaron parcialmente ese
> día (validación con gplsi, auditoría de reglas, medición completa del
> BLOC C de preposiciones de la guía gramatical) — ver `CLAUDE.md` para
> el detalle completo y actualizado, que es la fuente más fiable a
> partir de esa fecha.
