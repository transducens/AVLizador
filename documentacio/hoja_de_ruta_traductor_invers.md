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
(`conjugacions_dialectals.json`, `lexic_general.json`, etc.) indexados
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

Construido `pipeline/08_traduccio_corpus/postprocessat_llm/compara_demostratius_invers.py`
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
`lexic_general.json` a mano, a su ritmo. Confirmado que el problema
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

## 20/10/2026 — Incoativos sin lista a mano, artículo apostrofado y canónica

### El problema de los incoativos

Los verbos incoativos de la 3ª conjugación (servir, oferir, produir...)
llevan un incremento en el presente: "-eix-" en catalán central (serveix,
serveixes, serveixen) y "-ix-" en valenciano (servix, servixes, servixen).

**Por qué fallaba el lookup**: la AVL acepta las dos formas en valenciano,
así que el proveedor no las trata como par dialectal.
`conjugacions_dialectals.json` trae de "servir" la 1ª persona
("serveixo"→"servisc") y todo el subjuntivo ("serveixi"→"servisca"), pero
**no** "serveix"/"serveixes"/"serveixen". Ningún JSON tiene esas formas, y
son las más frecuentes: en el corpus (151 + gplsi), el valenciano de
referencia usa "-ix" en 198 de 198 casos reales.

**Por qué no basta una regla de sufijo**: en catalán "-eix" no identifica
un incoativo. Acaban igual los incoativos en "-ir" (serveix, cambia), los
verbos en "-èixer" (apareix, coneix, creix, nunca cambian) y palabras que
no son verbos (mateix, peix, aqueix). El valenciano separa las dos clases
de verbos por escrito; el catalán las funde. La diferencia es léxica, y por
eso la versión del 13/10/2026 usaba una lista cerrada de 7 raíces a mano.

### La solución (sin listas a mano)

`cat_val/incoatius.py` cambia "-eix"→"-ix" solo si:

1. spaCy etiqueta el token como VERB/AUX;
2. el lema de spaCy acaba en "-ir";
3. ese lema existe como infinitivo en `conjugacions_dialectals.json`
   (campos `verbo`, `infinitiu_cat`, `infinitiu_val`);

y además la palabra es exactamente raíz del lema + "eix" + ("", "es", "en").
La condición 3 es la clave: spaCy se inventa lemas para los verbos que no
conoce ("apareix"→*aparir*, "coneix"→*conir*, "neix"→*nir*), y esos
"infinitivos" no están en nuestros datos. Diéresis cuando la raíz acaba en
vocal sonora ("produeix"→"produïx", "posseeix"→"posseïx"), no tras "gu"/"qu"
("aconsegueix"→"aconseguix"). Nuevo campo `Token.lemma`, rellenado por
`pos_tagger.etiqueta()`.

Limitaciones conocidas (se prefiere falso negativo): verbo etiquetado
PROPN a principio de frase ("Floreix..."), verbo con enclítico pegado
("Serveix-li", spaCy lo parte en dos tokens), y sin spaCy instalado la
regla no hace nada.

### Resultados (cat→val)

| | Benchmark 151 | gplsi (1.958) | BLEU gplsi |
|---|---|---|---|
| Mañana (lista de 7 raíces) | 136/154 | 1337 | 90,14 |
| Sin incoativos (paso intermedio) | 128/154 | 1321 | 90,02 |
| **Incoativos spaCy + JSON** | **136/154** | **1505** | **93,05** |

Frente a no tener la regla: +185 frases en gplsi y 1 pérdida
("conquereix", la referencia lo deja igual). Dos referencias escriben
"conduixen"/"fluixen" sin diéresis (no normativo); el motor da
"conduïxen"/"fluïxen".

### Otros cambios del mismo día

- **Artículo delante de vocal** (`corregeix_article_abans()`,
  `rules/__init__.py`): tras una sustitución que deja la palabra empezando
  por vocal, "el"/"la" se apostrofan ("el darrer"→"l'últim",
  "el batlle"→"l'alcalde"). "la" no se apostrofa ante i/u átonas. +15 en
  gplsi; −3 referencias que escriben "La última" (no normativo, sin
  excepción).
- **Regla fija: en caso de duda, `canonica: true`**
  (`cat_val/lexic.py::_invertix_sense_ambiguitat`). Las listas de
  ordinales del usuario sobrescriben la canónica. +3 en gplsi (llimona→llima).
- **spaCy `Mood` descartado también en catalán** (sm 10/35, md 8/35): el
  modo verbal ambiguo irá al LLM.

## 21/10/2026 — Guía de traducción dialectal: qué reglas tienen evidencia en cat→val

Objetivo del usuario: usar `pipeline/02_regles_dialectals/docs_gramatica/guia_traduccio_dialectal.md`
(BLOC B pronombres débiles, BLOC C preposiciones, BLOC D adverbios de
lugar) para una posible capa de postprocesado con LLM (qwen3) en
cat→val, preferiblemente con reglas fijas cuando no haga falta un LLM.
Antes de construir nada se midió cada regla contra traducciones humanas
reales, nunca contra la salida del motor.

### Primera medición: benchmark 151 + gplsi, y por qué no basta

Sobre los 2.112 pares de 151 + gplsi casi ninguna regla aparece: los
pronombres débiles (BLOC B) salen 21 veces y no cambian nunca; "quan"
21 veces y no cambia nunca; "aquí" una vez ("vet aquí", expresión fija).
Además, **los tres corpus tienen estilos distintos**: "on"→"a on" se da
10 de 14 veces en el 151, 0 de 8 en gplsi y 0 de 558 en el BOE; "per" +
infinitivo pasa a "per a" en el BOE, pero gplsi lo deja en "per" (0 de
64). Medir solo con el 151 había llevado a una regla (`relatiu_on.py`)
que reproduce el estilo de ese corpus, no la norma.

### Medición sobre los corpus oficiales (AVL y BOE)

Decisión del usuario: tomar como referencia los dos corpus oficiales y
dar **porcentajes**, no recuentos. Script y salida completa en
`pipeline/02_regles_dialectals/docs_gramatica/mesura_guia_corpus_oficials.py`
y `..._resultats_20261021.txt`. Dos medidas:

- **Cumplimiento** en valencià oficial: de cada vez que aparece el
  contexto de la regla, porcentaje de veces que el texto usa la forma
  que dice la guía. AVL entera (`dades/avl/final/unified.jsonl`, 2.233
  documentos, solo valenciano) y 80.000 líneas aleatorias del BOE
  valenciano.
- **Conversión** en el BOE alineado: cuando la línea catalana tiene el
  patrón, porcentaje de veces que la valenciana lo cambia (sin contar
  las frases reformuladas).

| Regla de la guía | Cumplimiento AVL | Cumplimiento BOE | Conversión BOE cat→val | Veredicto |
|---|---|---|---|---|
| B1 "el" → "lo" (proclítico ante consonante) | 2,0% | 0,0% | 0% | **No**: el valenciano oficial escribe "el" |
| B1/B2 "els" → "los" (proclítico) | 0,4–0,7% | 0,0–0,2% | 0% | **No** |
| B3 "en" → "ne" (partitivo proclítico) | 1,4% | 0,0% | 0% | **No** |
| B1/B3 enclíticos "-lo/-los/-ne" tras consonante | 99,6% / 98,9% | 99,8% / 100% | — | **Nada que hacer**: el catalán escrito ya usa las mismas formas ("fer-lo", "fer-ne") |
| B4 "l'hi/la hi…" → "li'l/li la…" | ~~83,3%~~ (medida inflada, ver B4 abajo) | 100% (n=13) | 62,5% (n=8) | Real, pero **muy poco frecuente** y ambiguo (cuatro lecturas): solo LLM |
| C1 "a" + artículo → "en" (lugar) | 61,4%* | 58,9%* | 13,9% | **No como regla fija**: depende del significado; candidata a LLM |
| C2 "per" + infinitivo → "per a" | 91,8% | 94,7% | **96,7%** | **Sí, regla fija** (excepción: "per haver", causal, 100% "per") |
| C3 relativo "on" sin "a" | 79,7% | 99,6% | **100%** se queda "on" | **Sí: quitar el "a on"** que añade `relatiu_on.py` |
| C4 "quan" → "en" + infinitivo | 10,8% | 1,1% | 0,4% | **No** |
| D1 "aquí" → "ací" | 82,7% (aquí 11,8%, ahí 5,5%) | 100% | **100%** (n=25) | **Sí, regla fija** "ací" por defecto ("ahí" es contextual y poco frecuente) |

\* C1 cuenta todos los usos de preposición + artículo, no solo los de
lugar, así que no mide la regla directamente; la medida fiable es la
conversión alineada (13,9%).

### Conclusiones

1. **Regla fija, sin LLM, con evidencia en los dos corpus oficiales:**
   - **C2**: "per" + infinitivo → "per a" + infinitivo, salvo "per haver".
   - **D1**: "aquí" → "ací".
   - **C3**: "on" se queda sin "a". Eso significa **retirar** el "a on"
     de `cat_val/relatiu_on.py`: solo lo respalda el benchmark de 151
     (estilo propio de esos textos); la AVL lo usa un 20% y el BOE un 0,4%.
2. **La guía no se corresponde con el valenciano escrito oficial en el
   BLOC B (B1, B2, B3) ni en C4.** El valenciano formal de la AVL y del
   BOE escribe "el", "els", "en" y "quan", igual que el catalán. Las
   formas "lo", "los", "ne" y "en + infinitivo" de la guía son de la
   lengua oral o de registros menos formales.
3. **Candidatas a LLM, pero con poco volumen o poca evidencia:** C1 (lugar
   abstracto, "a la llei" → "en la llei", 13,9% en el BOE) y B4 ("l'hi" →
   "li'l", muy raro). Lo que de verdad justificaría una capa de LLM en
   cat→val sigue siendo lo que ya se sabía: "aquest" → "este"/"eixe" y el
   modo verbal ambiguo.
4. **Consecuencia práctica para los benchmarks:** C2 y C3 harán bajar el
   benchmark de 151 o gplsi en algunos casos, porque esos corpus tienen un
   estilo distinto del oficial. Habrá que decidir si se prioriza la
   norma oficial (AVL/BOE) sobre esos benchmarks.

Estado: **medido y documentado, nada implementado todavía**.

### Reglas definidas a partir de la evidencia (21/10/2026)

Decisión del usuario: implementar en cat→val las tres reglas con
evidencia fuerte en los corpus oficiales (C2, D1, C3), dejarlas pensadas
para val→cat aunque de momento no se apliquen allí, y razonar aparte B4.

#### D1 — "aquí" → "ací" (dato, no código)

Se resuelve **en el diccionario**, no con una regla Python: una entrada
nueva en `pipeline/02_regles_dialectals/lexic/diccionarios/lexico_general.json`
(fuente oficial, añadida con permiso explícito del usuario):

```json
{"espanol": "aquí", "catalan": "aquí", "valenciano": "ací", "tipo": "v:lexic_val",
 "fuente": "corpus_oficial", "id": "E1648", "categoria": "adv"}
```

**Justificación (medida el 21/10/2026, `mesura_guia_corpus_oficials.py`):**

- En la AVL, cuando aparece un adverbio de 1r/2º grado, el 82,7% es
  "ací", el 5,5% "ahí" y solo el 11,8% "aquí".
- En el BOE valenciano, el 100% es "ací" (n=38): ni "aquí" ni "ahí".
- En el BOE alineado, cada vez que el catalán dice "aquí", el valenciano
  dice "ací" (100% de los casos no reformulados, n=25).
- La guía (D1 y E4) indica "ací" como forma por defecto cuando el
  contexto no permite distinguir el grado.
- `fuente: "corpus_oficial"` (nueva) marca que la entrada viene de la
  medición en corpus y no del proveedor; se evita `avl_equip`, que
  `possessius.py` usa como filtro de posesivos.

Al ser un par del diccionario, sirve **en las dos direcciones sin código
nuevo**: cat→val "aquí" → "ací" y val→cat "ací" → "aquí". "ahí" (2º
grado, 5,5% en la AVL, dependiente del contexto) queda fuera: añadirlo
como segundo candidato exigiría marcar "ací" como `canonica: true` para
cat→val y solo aportaría val→cat "ahí" → "aquí". Pendiente de decisión.

#### C2 — "per" + infinitivo → "per a" + infinitivo (regla nueva)

Módulo nuevo `traductor/rules/cat_val/per_a_infinitiu.py`. Se convierte
"per" en "per a" cuando la palabra siguiente es un **infinitivo según
spaCy** (`VerbForm=Inf`; el catalán de entrada es la lengua que spaCy
conoce bien) y no es "haver". No usa listas de verbos.

**Justificación:** cumplimiento de "per a" + infinitivo de 91,8% en la
AVL y 94,7% en el BOE; en el BOE alineado, el catalán "per" + infinitivo
pasa a "per a" en el 96,7% de los casos. La excepción "per haver"
(infinitivo compuesto, valor causal: "per haver estat condemnat") se
mantiene "per" en el 100% (n=29). Coincide con la guía (C2, "regla
d'or": finalidad o destino → "per a").

**Límites conocidos:** el ~3% restante son verbos que rigen "per"
("optar per mantenir", "caracteritzar-se per ser") o causales sin
"haver"; distinguirlos exige entender la frase (candidato a LLM si algún
día compensa). "per no" + infinitivo ("per a no incórrer") no se toca.

**val→cat:** la dirección inversa ("per a" + infinitivo → "per") **no es
una regla dialectal sino de estilo**: el catalán del BOE escribe "per",
el del benchmark de 151 escribe "per a" (27 casos), y la norma catalana
admite las dos. Si se activa algún día en val→cat, debe ser una opción de
registro, no un cambio por defecto.

#### C3 — retirar el "a on" (se borra `cat_val/relatiu_on.py`)

La regla añadía "a" delante de "on" relativo/interrogativo siempre.
Solo la respaldaba el benchmark de 151 (10 de 14 casos, estilo propio de
esos textos). En los corpus oficiales:

- AVL: "on" sin "a" en el 79,7% (n=1.465).
- BOE valenciano: 99,6% (n=512).
- BOE alineado: el "on" catalán se queda "on" el 100% de las veces (n=431).
- La guía (C3) dice explícitamente que en registro formal los dos
  estándares prefieren "on" sin "a".

Se elimina el módulo de cat→val. **val→cat:** `val_cat/relatiu_on.py`
hace lo contrario (quita la "a" de "a on") y **es coherente con esta
evidencia** (el catalán nunca escribe "a on"), así que se mantiene.

#### B4 — análisis (no implementado)

**Corrección de la medida de la AVL:** el 83,3% de la primera tabla
estaba inflado. La expresión regular contaba como "li la" / "li les"
casos donde "la"/"les" son artículos ("facilitar-li les coses",
"donar-li la resposta"), no combinaciones de pronombres. Los casos reales
de la AVL son casi todos explicaciones normativas de la GNV ("L'hi he
donat (per Li l'he donat)", "li'l posaré, li la duré"), que confirman la
norma pero no dan un porcentaje de uso.

**Los 25 casos del BOE, leídos uno a uno.** El catalán "l'hi", "la hi",
"les hi", "els hi" (y sus enclíticos "-l'hi", "-la-hi", "-los-hi") no es
una sola cosa, sino cuatro:

| Lectura | Ejemplo (catalán → valenciano BOE) | Valenciano |
|---|---|---|
| "li" + acusativo masc./fem. | "una altra persona l'hi causi" → "li'l cause"; "la hi ha transmès" → "li l'haja transmés"; "lliurar-la-hi" → "entregar-li-la"; "a qui les hi va donar" → "a qui li les va donar" | li'l / li la / li les |
| "li" + "ho" (neutro) | "comunicar-l'hi" → "comunicar-li-ho"; "l'hi ha de notificar" → "notificar-li-ho" | li ho |
| acusativo + "hi" de lugar | "transportar-los-hi" → "transportar-los per esta xarxa"; "les hi hagin posat" → "haver-les posades" | igual que en catalán |
| dativo plural + acusativo | "sense enviar-l'hi" → "sense enviar-los-el" | los el |

Además, casi la mitad de los casos vienen reformulados en pasiva
("les hi ha d'abonar" → "li seran abonades"), así que no sirven para
medir.

**Conclusión:** no hay ninguna forma de B4 que se pueda convertir con una
regla fija. Ni siquiera "la hi" o "-la-hi" son seguras (pueden llevar "hi"
de lugar). spaCy no ayuda: las cuatro lecturas tienen las mismas
categorías gramaticales; lo que cambia es el significado (a quién se da
algo, o dónde se pone). Es un caso de **LLM con candidatos cerrados**: el
motor detecta la forma y ofrece las 3-4 salidas posibles, y el modelo
solo elige una. Pero el volumen es mínimo: unos 25 casos en 268.000
líneas del BOE (1 por cada ~10.000 líneas). Prioridad baja frente a
"aquest" → "este"/"eixe" y el modo verbal.

**val→cat (para el futuro):** la dirección contraria sí es casi
determinista. "li'l", "li'ls", "li l'" son inequívocos ("li" + el/els) →
catalán central "l'hi"/"els hi". "li la"/"li les" exigen comprobar con
spaCy que "la"/"les" son pronombre y no artículo ("donar-li la resposta"
no se toca); en catalán spaCy lo distingue bien. Aun así, el catalán
normativo actual admite también "li la" como variante, así que sería
otra opción de registro.

#### Pensando en val→cat

| Regla | ¿Sirve en val→cat? |
|---|---|
| D1 | Sí, automáticamente: es un par del diccionario ("ací" → "aquí") |
| C2 | No por defecto: el catalán admite "per" y "per a" + infinitivo; solo como opción de registro |
| C3 | Ya existe y es correcta (`val_cat/relatiu_on.py`, "a on" → "on") |
| B4 | Inverso determinista ("li'l" → "l'hi" en catalán central); a decidir con B4 |

### Implementación y resultados (21/10/2026)

Hecho, con permiso del usuario:

- **D1:** entrada `E1648` en `diccionarios/lexico_general.json`
  ("aquí" → "ací", `fuente: "corpus_oficial"`), sincronizada. Sin código.
- **C2:** módulo nuevo `cat_val/per_a_infinitiu.py`. Para reconocer el
  infinitivo se añadió `Token.verb_form` (rasgo `VerbForm` de spaCy). De
  paso, `pos_tagger.etiqueta()` ahora encuentra los verbos con pronombre
  enclítico pegado ("fer-ho"), que spaCy parte en dos y antes quedaban sin
  etiqueta.
- **C3:** borrado `cat_val/relatiu_on.py` (el de val→cat se mantiene).

595/595 doctests (los 6 que faltan respecto a antes eran de
`relatiu_on.py`).

| Benchmark cat→val | Antes | Después | Por qué |
|---|---|---|---|
| **BOE, muestra de 2.000 líneas** (oficial) | 360 | **368** | C2: 97 frases más cerca de la referencia, 8 más lejos. C3: 15 más cerca, 0 más lejos |
| Benchmark 151 | 137 | 130 | C3: −9 / +3 (sus textos usan "a on"); C2: −2 ("per fer", "per parlar") |
| gplsi | 1.524 | 1.486 | C2: ~−42 (su traductor escribe "per" + infinitivo); C3: +7; D1: −2 ("vet aquí", "d'aquí") |

Las bajadas en 151 y gplsi son de estilo, no errores: esos corpus no
siguen la norma oficial en estos tres puntos. La muestra del BOE quedó
guardada como benchmark nuevo en `dades/boe/benchmark_boe_mostra_2000.json`
(mismo formato `id`/`occidental`/`oriental`; `dades/` no está en git).
Nota: el número de frases exactas en el BOE es bajo (~18%) en parte porque
la referencia usa el apóstrofo tipográfico (’) y el motor el recto (');
no afecta a la comparación antes/después.

## 21/10/2026 (tarde) — "ahí", B4 en val→cat y las dos capas de LLM

### "ahí" como segundo candidato

Con permiso del usuario, entrada nueva `E1649` en `lexico_general.json`
("aquí" → "ahí", `canonica: false`), en colisión con `E1648` ("aquí" →
"ací", ahora `canonica: true`). cat→val no cambia ("aquí" → "ací" por la
regla de la canónica); val→cat gana "ahí" → "aquí" además de "ací" → "aquí".

### B4 en val→cat: regla fija (`val_cat/combinacio_li.py`)

"li'l" → "l'hi", "li'ls" → "els hi", "li l'he" → "l'hi he", "li la" → "la
hi", "li les" → "les hi", y enclíticos "-li'l" → "-l'hi", "-li-la" →
"-la-hi", "-li-les" → "-les-hi", "-li'ls" → "'ls-hi"/"-los-hi". "li ho" y
"li'n" no cambian.

**Cambio respecto al plan:** se pensó comprobar con spaCy que "la"/"les"
fueran pronombre y no artículo ("donar-li la resposta"). Probado: **spaCy
no sirve** (en "Ja li la donaré" etiqueta "la" como artículo y "donaré"
como nombre; no conoce la construcción). Lo resuelve la gramática: el
artículo solo puede ir detrás de un "li" **enclítico** ("exposar-li la
meua queixa"), que el tokenizador ya une al verbo y la regla no toca; un
"li" **suelto** siempre es proclítico y detrás solo puede venir otro
pronombre o el verbo. Comprobado en la AVL y el BOE: todos los "li la"/"li
les" con "li" suelto son pronombre + pronombre. La regla no cambia ninguna
frase de los tres benchmarks (la construcción no aparece) y no rompe nada.

### Las dos capas de LLM (`traductor/llm/`)

Decisión del usuario: dos capas distintas, una por dirección, preparadas
ya para B4 y "aquest" (cat→val) y para el modo verbal (val→cat).

- El motor marca **puntos ambiguos** con opciones cerradas; el LLM solo
  elige una etiqueta (`client.py`, Ollama, temperatura 0); si falla, se
  queda la opción del motor. `traductor.translate*()` no cambian.
- **cat→val** (`cat_val.py`): `demostratiu` ("este"/"eixe", por defecto
  "este", criterio conservador: "eixe" solo si es claro) y `b4`
  (`datiu`/`neutre`/`plural`/`lloc`, por defecto `lloc` = no tocar; el
  prompt usa los casos reales del BOE como ejemplos).
- **val→cat** (`val_cat.py`): `mode_verbal` (`indicatiu`/`subjuntiu`/`cap`),
  la "vía C" que dio 129/151 con `qwen3:8b`, traída dentro de `traductor/`.
  **La versión de `pipeline/08` estaba rota**: `identifica_ambigues.py`
  leía cuatro ficheros de conjugaciones retirados el 19/10/2026 y una
  lista (`EXCLUSIONS_HOMOGRAF`) retirada el mismo día. Ahora las
  ambigüedades salen de `traductor/data/conjugacions_dialectals.json`:
  12.224 formas (3.003 de 1ª singular, 9.221 de 3ª plural).
- Los dos motores exponen `tradueix_tokens()`.
- Evaluación: `pipeline/08_traduccio_corpus/postprocessat_llm/avalua_capa_llm.py`
  y `slurm/avalua_capa_llm.sh` (Abaco, `qwen3:8b`, las dos direcciones
  sobre 151 y BOE).

**Puntos detectados sin llamar al modelo** (`--sense-llm`):

| Capa | Benchmark | Puntos | Con verdad en la referencia | Acierta el motor por defecto |
|---|---|---|---|---|
| cat→val `demostratiu` | 151 | 102 | 100 | 100 (100%) |
| cat→val `demostratiu` | BOE 2.000 | 521 | 256 | 242 (94,5%) |
| cat→val `b4` | 151 y BOE | 0 | — | — |
| val→cat `mode_verbal` | 151 | 47 | 44 | 27 (61%) |
| val→cat `mode_verbal` | BOE 2.000 | 508 | 416 | 82 (20%) |

Lectura: en cat→val, "este" por defecto ya acierta casi siempre en estos
corpus (el LLM solo puede ganar los ~14 "eixe" del BOE y puede estropear
más); en val→cat, el 80% de las formas ambiguas del BOE son subjuntivo
(textos legales), así que ahí está el mayor margen del LLM.

**Prueba rápida en local** (`qwen2.5:7b`, sin GPU): B4 "l'hi presenta" →
"li'l presenta" (datiu) y "comunicar-l'hi" → "comunicar-li-ho" (neutre),
correctos; modo verbal "Vull que… creuen" → "creuin" y "Els experts
creuen" → igual, correctos; "Aquest llibre que tens a les mans" → "este"
(debería ser "eixe"). La evaluación real queda para Abaco con `qwen3:8b`.

621/621 doctests (incluidos los nuevos de `traductor/llm/`).

### Primera prueba en Abaco (qwen3:8b, 20 frases, 21/10/2026)

Abaco ya trabaja con un clon del repositorio (`~/scrapeo/AVLizador`,
`git pull` para actualizar; el script SLURM detecta el modo repo y guarda en
`dades/abaco/`). La antigua carpeta plana se archivó como
`~/scrapeo/postprocesado_llm_arxiu_20261021`.

| Capa | Benchmark 151 (20 frases) | Lectura |
|---|---|---|
| cat→val `demostratiu` | motor 5/5, LLM 1/5 (cambia 4 a "eixe") | El modelo toma la anáfora ("d'aquestes estades", "aquests que hem comentat") por 2º grado |
| val→cat `mode_verbal` | motor 5/6, LLM 3/6 | Sesgo al subjuntivo: "poden quedar", "creuen que", "per la qual es regulen" |

Dos decisiones a partir de esto:

1. **`demostratiu` desactivado por defecto** (`cat_val.py::TIPUS_PER_DEFECTE`
   = solo `b4`). En el BOE el "eixe" también es anafórico ("en eixe cas",
   "dins d'eixe termini", "eixe apartat": 19 frases de la muestra), igual
   que el "este" del 151 ("d'estes estades"). Es una elección de estilo sin
   señal en la frase, y "este" por defecto ya acierta el 94,5% (BOE) y el
   100% (151). Se puede probar a mano con `--tipus demostratiu`.
2. **Prompt de modo verbal restaurado literalmente** desde
   `compara_postprocessat.py` (criterio + system + formato de consulta de
   la vía C, verificado idéntico por código). La primera versión de
   `val_cat.py` lo había acortado y ponía la palabra entre corchetes dentro
   de la frase; así no era comparable con el récord de 129/151.

También se corrigió la métrica "canviats pel LLM" de `avalua_capa_llm.py`:
contaba como cambio elegir "indicatiu" en 3ª plural, que da el mismo texto.

### Evaluación completa en Abaco y retirada de la capa de LLM de cat→val (21/10/2026)

Ejecución completa de `slurm/avalua_capa_llm.sh` (`qwen3:8b`, commit
`9b6180b`), con los dos ajustes ya aplicados ("aquest" desactivado, prompt
de modo verbal restaurado literal):

| Dirección | Benchmark | Frases exactas | Acierto en los puntos |
|---|---|---|---|
| cat→val | 151 | 130 → 130 | sin puntos |
| cat→val | BOE 2.000 | 453 → 453 | sin puntos |
| val→cat | 151 | 100 → 109 | motor 27/44 → LLM 37/44 |
| val→cat | BOE 2.000 | 396 → 406 | motor 82/416 → LLM 294/416 |

**Decisión del usuario:**

- **cat→val: capa de LLM RETIRADA** (`traductor/llm/cat_val.py` borrado).
  No cambiaba ninguna de las 2.154 frases. La herramienta cat→val que se
  entrega va sin LLM. El análisis de B4 y de "aquest" sigue arriba como
  registro.
- **val→cat: capa CONGELADA.** Se queda tal cual (mejora al motor), pero
  no se sigue mejorando. Su catálogo de errores, con ejemplos y el tipo de
  solución posible de cada uno, está en `traductor/llm/README.es.md`:
  relativos normativos/reales confundidos (81 de 122 errores del BOE), 1ª
  persona con "indicatiu" sin sujeto "jo" que genera formas agramaticales
  (18), "quan" de condición futura (6), "si" + subjuntivo (2), frases
  largas (17).
- El trabajo vuelve a centrarse solo en cat→val.

