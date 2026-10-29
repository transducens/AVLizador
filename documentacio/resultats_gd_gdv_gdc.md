# Grau Dialectal (GD, GDV, GDC): resultados por corpus

Documento vivo: se va completando a medida que se mide cada corpus.
Herramientas: `pipeline/09_grau_dialectal/` (`gd.py`, `gdv.py`, `gdc.py`).

Para medirlo todo de una vez (GD, GDV y GDC de cada documento; se puede
parar y continuar):

```
python pipeline/09_grau_dialectal/mesura_corpus.py
```

Resultados por documento en `dades/grau_dialectal/<corpus>.jsonl`;
resumen en `dades/grau_dialectal/resum.md`.

## Qué mide cada índice

Cada palabra del texto es de uno de tres tipos:

- **marcador occidental** (occ): forma valenciana del diccionario
  ("xiquet", "este", "tindre");
- **marcador oriental** (or): forma catalana del diccionario ("nen",
  "aquest", "tenir");
- **neutra**: todo lo demás ("casa", "amb", "el"); vale en los dos
  dialectos. Son el 95-99 % de las palabras.

Un *marcador* es una palabra que el diccionario del traductor (léxico +
conjugaciones) empareja con una forma distinta en el otro dialecto.

Hay dos tipos de métrica (decisión del 27/10/2026):

| Índice | Fórmula | Neutras | 1 significa | 0 significa |
|---|---|---|---|---|
| **GD** (`gd.py`) | occ / (occ + or) | no cuentan | todos los marcadores son valencianos | todos son catalanes |
| **GDV** (`gdv.py`) | (occ + neutras) / palabras = 1 − or / palabras | cuentan como válidas | ninguna palabra catalana | todas catalanas |
| **GDC** (`gdc.py`) | (or + neutras) / palabras = 1 − occ / palabras | cuentan como válidas | ninguna palabra valenciana | todas valencianas |

- **GD**: dice hacia qué dialecto se inclina el texto. Un texto
  valenciano debe dar cerca de 1 y uno catalán cerca de 0.
- **GDV / GDC**: dicen qué parte del texto es aceptable en cada
  dialecto. Pensados como recompensa para entrenar modelos: una frase sin
  marcadores también sigue el estándar. Por eso quedan siempre cerca de
  1 y no suman 1 entre ellos.
- **Global**: sobre todo el corpus (GD: suma de marcadores; GDV/GDC: por
  palabra). **Media**: media por frase.

**Limitaciones generales**:
- Todos usan el mismo diccionario que el traductor. Miden los
  marcadores *conocidos*; una palabra dialectal que no está en el
  diccionario no se ve.
- "Neutra" significa "no está en el diccionario", no "correcta": un
  castellanismo cuenta como válido en GDV/GDC.

## Resumen

**Medida vigente: 28/10/2026**, con el léxico y los verbos del compañero
ya fusionados (rama `lista-lexico`) y con `mesura_corpus.py`, línea a
línea. Qué ha cambiado y por qué, en la sección 5. Las secciones 1, 2 y 4
son la revisión detallada del 27/10, con el léxico anterior.

Valores de GDV/GDC con la fórmula del 27/10 (con neutras). Modelo de
spaCy: `ca_core_news_md` 3.8.0 (spaCy 3.8.16).

| Corpus | Lado | GD 28/10 | GD 27/10 | GDV | GDC | Palabras | occ / or |
|---|---|---|---|---|---|---|---|
| Benchmark 151 (154 entradas) | valenciano | **0,9854** | 0,9863 | **0,9991** (media 0,9989) | 0,9372 | 4.302 | 270 / 4 |
| Benchmark 151 (154 entradas) | catalán | **0,0727** | 0,1267 | 0,9407 | **0,9954** (media 0,9952) | 4.303 | 20 / 255 |
| BOE completo (267.962 líneas, 520 documentos) | valenciano | **0,9344** | 0,9424 | **0,9980** (media 0,9976) | 0,9717 | 6.698.334 | 189.858 / 13.333 |
| BOE completo (267.962 líneas, 520 documentos) | catalán | **0,0625** | 0,0684 | 0,9698 | **0,9980** (media 0,9984) | 6.731.637 | 13.552 / 203.375 |
| **Benchmark manual (453: 241 BOE + 212 AVL)** | valenciano | **0,9954** | (nuevo) | **0,9996** (media 0,9996) | 0,9181 | 13.216 | 1.083 / 5 |
| **Benchmark manual (453: 241 BOE + 212 AVL)** | catalán | **0,0330** | (nuevo) | 0,9201 | **0,9973** (media 0,9968) | 13.191 | 36 / 1.054 |
| BOE estricto (2.000) | valenciano / catalán | *pendiente* | | | | | |
| BOE amplio (2.000) | valenciano / catalán | *pendiente* | | | | | |
| GNV (AVL), por líneas | valenciano | **0,8595** | 0,8678 | **0,9982** | 0,9889 | 66.146 | 734 / 120 |
| GEIEC (IEC), por líneas | catalán | **0,2334** | 0,2453 | 0,9828 | **0,9948** | 92.719 | 486 / 1.596 |

Las gramáticas se miden aquí línea a línea, como hace `mesura_corpus.py`.
Medidas como texto entero (`--fitxer`, sección 4, 27/10) daban GNV 0,8696
(760 / 114) y GEIEC 0,2260 (456 / 1.562): spaCy ve otro contexto. El 151
da exactamente lo mismo por las dos vías.

Las revisiones marcador a marcador de cada sección se expresan con el GD
(es donde se ve el efecto de cada marcador; en GDV/GDC el efecto queda
diluido entre las neutras).

## 1. Benchmark de 151 frases

Fichero: `pipeline/03_seleccio_de_model/benchmark_corpus.json` (154
entradas; referencias editadas por el usuario el 21/10/2026). Medido el
27/10/2026. Los marcadores son los mismos que en la primera medida del
26/10, así que la herramienta es estable.

```
python pipeline/09_grau_dialectal/gd.py --corpus pipeline/03_seleccio_de_model/benchmark_corpus.json --camp occidental --camp-alt oriental --html pipeline/09_grau_dialectal/proves/gd_151.html
python pipeline/09_grau_dialectal/gdv.py --corpus pipeline/03_seleccio_de_model/benchmark_corpus.json --camp occidental
python pipeline/09_grau_dialectal/gdc.py --corpus pipeline/03_seleccio_de_model/benchmark_corpus.json --camp oriental
```

| Lado | GD global | GDV global / media | GDC global / media | Sin marcadores | Palabras | occ | or |
|---|---|---|---|---|---|---|---|
| valenciano (`occidental`) | 0,9863 | 0,9991 / 0,9989 | — | 14 | 4.302 | 287 | 4 |
| catalán (`oriental`) | 0,1267 | — | 0,9914 / 0,9909 | 15 | 4.303 | 37 | 255 |

### ¿Funciona bien? Revisión marcador a marcador

Se han revisado una a una las palabras que bajan cada índice (los 4
marcadores orientales del lado valenciano y los 37 occidentales del lado
catalán) y se han clasificado en tres tipos:

- **Error del GD**: el texto está bien y la palabra no debería contar.
- **Registro**: palabra que el diccionario empareja, pero que en el
  registro formal se usa en los dos dialectos.
- **Real**: el texto contiene de verdad una forma del otro dialecto.

**Lado valenciano (4 marcadores orientales)**

| Palabra | Frase | Tipo | Explicación |
|---|---|---|---|
| mentre | RC002 | Error del GD | El léxico tiene `E1647` "mentre"="mentre" como canónica valenciana, pero el GD sigue contando "mentre" como catalán por `E0040` ("mentres"/"mentre"). |
| rebuda | RC080 | Error del GD | Participio de "rebre" ("l'havia rebuda"); el par del léxico es el nombre ("rebuda"→"recepció"). Homógrafo sin marcar. |
| rentar | RC002 | Real (cita) | Frase metalingüística: compara "llavar" y "rentar". |
| civada | RC044 | Real | Enumeración con las dos palabras: "l'avena, la civada". |

**Lado catalán (37 marcadores occidentales)**

| Palabra | Veces | Tipo | Explicación |
|---|---|---|---|
| després | 17 | Error del GD | Adverbio compartido. El par `E0977` es el adjetivo ("desprès"/"després"). Ya identificado el 21/10; pendiente de marcarlo `homonimia_lexica` en origen. |
| consideren | 1 | Error del GD | "No es consideren dígrafs": indicativo, compartido. El par es el subjuntivo valenciano ("consideren"→"considerin"). |
| tancada | 1 | Error del GD | "e tancada" (adjetivo). El par es el nombre ("vallado"); dato `E0537` con categoría errónea, ya conocido. |
| he | 1 | Error del GD | Fila `LIMPIO_588` "he"→"haig": "he" es también la forma catalana estándar. |
| alcalde | 3 | Registro | Compartida en registro formal (par alcalde/batlle). |
| investigació, investigacions | 2 | Registro | Compartida (par investigació/recerca). |
| menció | 1 | Registro | Compartida en registro formal. |
| últims | 1 | Registro | Compartida (par últim/darrer). |
| tindre | 5 | Real | RC021 la cita como expresión valenciana; RC115 "pugui tindre" está en la referencia catalana. |
| deixes | 1 | Real | "No deixes…" (en catalán, "No deixis"). |
| ací | 1 | Real | "des d'ací" en la referencia catalana. |
| complisca | 1 | Real | En catalán, "compleixi". |
| fem | 1 | Real | "guals i fem": "fem" (basura) es valenciano; en catalán, "escombraries". |
| avena | 1 | Real | La misma enumeración de RC044. |

**Recuento**

| Lado | Error del GD | Registro | Real | Total |
|---|---|---|---|---|
| valenciano | 2 | 0 | 2 | 4 |
| catalán | 20 | 7 | 10 | 37 |

**Lectura**

- El lado valenciano sale casi puro, y la mitad de lo poco que lo baja es
  real.
- El lado catalán sale más bajo de lo que es en realidad: más de la mitad
  de lo que lo baja (20 de 37) son errores del GD, y 17 de ellos son una
  sola palabra, "després".
- Quitando solo los errores del GD, el GD del lado catalán pasaría de
  0,1267 a **0,0625** (17 / 272). Quitando también los de registro, a
  **0,0377** (10 / 265). El del lado valenciano pasaría de 0,9863 a
  0,9931. En GDC/GDV el cambio sería pequeño (de 0,9914 a 0,9960 en el
  lado catalán), porque las neutras lo diluyen. Son cifras orientativas:
  el GD no se ha cambiado.
- Los 10 marcadores reales del lado catalán muestran que la referencia
  catalana del 151 conserva algunos valencianismos (es una adaptación del
  texto valenciano). Es un hallazgo sobre el benchmark, no sobre la
  herramienta.

**Qué arreglaría los errores del GD** (27/10/2026: el léxico de origen lo
está corrigiendo el equipo; cuando llegue, se vuelve a medir):

1. `E0977` ("després"): marcarlo `homonimia_lexica` (lemas adj/adv).
   Arregla 17 de los 20 errores del lado catalán. **Hecho el 27/10 por el
   compañero; medido el 28/10: 0,1267 → 0,0727 (sección 5).**
2. "mentre": que el GD respete la canónica idéntica `E1647` como ya hace
   el traductor desde el 21/10 (cambio de código en `gd.py`, no de datos).
3. `E0537` ("tancada"), "rebuda" y `LIMPIO_588` ("he"): revisar los datos.
4. "consideren": colisión indicativo/subjuntivo de 3ª plural, límite
   conocido; no se resuelve sin contexto.

## 2. BOE completo

Medido el 27/10/2026 con `mesura_corpus.py` (salidas en
`dades/grau_dialectal/`: `boe_val.jsonl`, `boe_cat.jsonl`, por línea, y
`boe_*_per_document.jsonl`, agrupado por `documento_id`).

```
python pipeline/09_grau_dialectal/mesura_corpus.py --corpus boe_val boe_cat
```

| Lado | GD global | GDV global / media | GDC global / media | Líneas sin marcadores | Palabras | occ | or |
|---|---|---|---|---|---|---|---|
| valenciano | **0,9424** | **0,9983** / 0,9978 | 0,9714 / 0,9765 | 157.268 de 267.962 | 6.698.334 | 191.527 | 11.714 |
| catalán | **0,0684** | 0,9703 / 0,9744 | **0,9978** / 0,9983 | 153.236 de 267.962 | 6.731.637 | 14.705 | 200.163 |

Por documento (520 `documento_id`): GD medio 0,9528 en el lado valenciano
(mediana 0,9908; 39 de 498 documentos con marcadores por debajo de 0,8)
y 0,0811 en el catalán (mediana 0,0648; 21 de 489 por encima de 0,2). Los
extremos (GD 0 en un documento valenciano, 1 en uno catalán) son
documentos con muy pocos marcadores.

(El 15/10 el lado valenciano daba 0,9219, con otro diccionario y otro GD;
no es comparable.)

### ¿Funciona bien? Revisión de los marcadores cruzados

Mismos tipos que en el 151. Con estos volúmenes se ha revisado por
palabra (las 30 más frecuentes cubren el 96 % del lado valenciano y el
88 % del catalán), no frase a frase.

**Lado valenciano: 11.714 marcadores orientales (114 formas)**

| Tipo | Marcadores | % | Palabras |
|---|---|---|---|
| **Registro**: forma que el diccionario empareja pero que el valenciano oficial también usa | ~9.000 | 77 % | "aquest/a/s/es" (5.805; el BOE valenciano usa "aquest" un ~10 % de las veces frente a "este"), "servei/serveis" (1.706), "perjudici/s" (425), "desenvolupament/desenvolupar" (339), "ordre/s" (309), "despesa/es" (241), "remès/comprès" (173), "judici" (88), "habitatge", "feina" |
| **Error del GD** | 1.972 | 17 % | "afecte/afecta" (715; "afecte a un servei", verbo y adjetivo administrativo, par `E0251` "carinyo"), "rebuda/es" (385; participio de "rebre", par `E0434`), "estat" (298; participio/nombre), "recull" (244; verbo "recollir"), "deu" (227; "termini de deu dies": el numeral, par `E0528` "deu"→"brollador", marcado `homonimia_lexica` pero spaCy lo da como nombre), "mentre" (103; `E1647`) |

Quitando los errores del GD, el lado valenciano pasaría de 0,9424 a
**0,9516**. El resto es registro: el BOE valenciano no es "puro" en el
sentido del diccionario, y el GD lo refleja.

**Lado catalán: 14.705 marcadores occidentales (194 formas)**

| Tipo | Marcadores | % | Palabras |
|---|---|---|---|
| **Error del GD: colisión verbal** (§4.2) | 2.988 | 20 % | 3ª plural en "-en" (2.034: "consideren" 910, "exceptuen", "continuen", "efectuen", "enumeren", "actuen", "operen", "amplien", "declaren"…) y 1ª singular valenciana = 3ª catalana (954: "permet" 570, "admet", "pertany", "recau", "remet", "transmet") |
| **Error del GD: homógrafo o dato** | 3.409 | 23 % | "després" (1.456; `E0977`), "recepció" (913; el par `E0434` "rebuda"→"recepció" hace de "recepció" un marcador valenciano, pero es la palabra catalana normal), "construcció" (707; `E0087`), "tancat/s/da/des" (249), "eixos" (84; plural de "eix", par `E1625` demostrativo) |
| **Registro**: palabra emparejada pero común en el catalán culto | 6.737 | 46 % | "vegada/es" (2.740; par `E1656` "cop"), "últim/a/s/es" (2.714), "investigació/ns" (998; par `E0237` "recerca"), "menció/ns" (285; par `E0404` "esment") |
| Resto (sin revisar una a una) | ~1.570 | 11 % | "generar" (254), "plurianual" (117), "carència" (114), y una cola larga |

Quitando los errores del GD, el lado catalán pasaría de 0,0684 a
**0,0399**; quitando también el registro, a **~0,008**. Cifras
orientativas: el GD no se ha cambiado.

**Lectura**

- Los dos lados salen donde deben (0,94 frente a 0,07), y a escala de
  BOE la separación es aún más clara que en el 151.
- Los errores del GD son los mismos que en el 151 y las gramáticas
  ("després", "mentre", "rebuda", "tancat", "afecta", "construcció") más
  tres nuevos: "deu" (numeral), "recull" y "eixos".
- **La colisión verbal se confirma a gran escala**: es el 20 % de los
  marcadores valencianos del BOE catalán, y "consideren" sola es la 4ª
  palabra. Como en la GEIEC, castiga al texto catalán y casi no afecta
  al valenciano.
- El registro pesa mucho en los dos lados, en sentido contrario: el BOE
  valenciano usa "aquest", "servei", "desenvolupament"; el catalán usa
  "vegada", "últim", "investigació". Son formas válidas en los dos
  estándares que el diccionario trata como dialectales. Para el GD de
  un corpus oficial esto es lo esperable (mide cercanía al dialecto
  "marcado"), pero hay que tenerlo en cuenta si se usa como recompensa.

**Correcciones de datos que ayudarían** (el equipo ya trabaja en el
léxico; ninguna se ha tocado): `E0977` "després", `E0434` "rebuda"
(también arrastra "recepció"), `E0251` "afecte/afecta", `E0087`
"construcció", `E0537`/`E0538` "tancada", `E1625` "eixos" (homógrafo con
el nombre "eix"), y revisar por qué spaCy da "deu" como nombre en "deu
dies".

## 3. Benchmarks BOE estricto y amplio

*Pendiente.*

## 4. Gramáticas normativas: GNV (AVL) y GEIEC (IEC)

Ficheros: `pipeline/02_regles_dialectals/docs_gramatica/gnv_complet.txt`
y `geiec_complet.txt`. Cada gramática se mide como un solo texto
(`--fitxer`), así que solo hay cifra global (no media por frase).

Advertencia: son textos metalingüísticos que citan a propósito formas de
la otra variedad (y la GEIEC documenta formas valencianas). Un índice por
debajo de 1 aquí no indica impureza; sirve de contraste entre las dos
normas.

### 4.1 GNV (Gramàtica Normativa Valenciana, AVL)

Medido el 27/10/2026 (66.146 palabras).

```
python pipeline/09_grau_dialectal/gdv.py --fitxer pipeline/02_regles_dialectals/docs_gramatica/gnv_complet.txt
python pipeline/09_grau_dialectal/gdc.py --fitxer pipeline/02_regles_dialectals/docs_gramatica/gnv_complet.txt
```

| Índice | Valor | Occidentales | Orientales | Neutras |
|---|---|---|---|---|
| GD | **0,8696** | 760 | 114 | — |
| GDV | **0,9983** | 760 | 114 | 65.272 |
| GDC | 0,9885 | 760 | 114 | 65.272 |

(El GD sale de los marcadores de la salida de `gdv.py`/`gdc.py`; los
valores de GDV/GDC son los de la fórmula del 27/10, con neutras. La
primera ejecución, con la fórmula del 26/10, daba "GDV 0,8696", que es
el GD.)

La GNV sale claramente valenciana (87 % de sus marcadores son
occidentales). Los más frecuentes: "tindre" (48), "este/esta/estes/estos"
(106), "seua/seues" (36), "siga" (25), "vegada/vegades" (22), "ací"
(10), "haja" (8).

**Revisión de los marcadores orientales.** Se han clasificado uno a uno
pasando el GD línea a línea, que da 755 / 115 en vez de 760 / 114 (spaCy
ve menos contexto; la diferencia no cambia el análisis):

| Tipo | Marcadores | Palabras |
|---|---|---|
| **Cita metalingüística**: la GNV nombra la forma oriental para describirla o admitirla | 60 | Sistema de demostrativos ("aquí", "aquest/a/s", "aqueix": 12); imperfecto de subjuntivo en "-s" ("hagués", "anés", "vingués", "afegís", "aparegués", "portés": 11); listas de acentuación con "è" ("anglès", "francès", "cafè", "cinquè", "pèsol", "mossèn"…: 24); variantes admitidas ("serveixo", "meitat", "aviat", "sortir/surt", "néixer", "tenir", "clos", "trenqueu", "deus", "dinés": 13) |
| **Registro**: prosa propia de la GNV con palabras que el diccionario empareja pero que en registro culto son comunes | 23 | "desenvolupament/desenvolupa/desenvolupar" (6), "darrer/darrera" (5), "esment" (3), "durada" (2), "manca" (2), "buscar", "fes", "estat", "signatura", "gruix" |
| **Error del GD**: palabra compartida o homógrafo | 32 | "mentre" (14; el problema de `E1647` ya visto en el 151), "afecta/afecte" (9; el verbo "afectar", par `E0251` adjetivo, ya conocido), "us" (3; la terminación culta "-us"), "comprés" (2; aparece como forma valenciana con acento agudo), "fos", "nou" (numeral), "cercle", "tènia" |

**Errores que suben el GD.** El mismo tipo de error también infla los
marcadores occidentales: "tancada/tancades" (31; "vocal tancada"),
"després" (22; adverbio), "he" (9) y "consideren" (7) son los casos ya
vistos en el 151.

**Lectura.**

- El GD responde como se espera: la norma valenciana sale claramente
  occidental.
- La mitad de lo que la baja (60 de 115) son citas de formas orientales
  que la propia gramática describe; eso no es impureza, es el contenido
  de una gramática.
- Quitando los errores del GD de los dos lados (occidentales 755 − 69 =
  686; orientales 115 − 32 = 83), el GD quedaría en unos **0,89**. Si
  además se quitan las citas, unos **0,97**. Son cifras orientativas.
- Los errores coinciden con los del 151 ("mentre", "després", "tancada",
  "he", "consideren") más "afecta". Las correcciones del léxico en curso
  deberían mejorar las dos medidas a la vez.

### 4.2 GEIEC (Gramàtica essencial de la llengua catalana, IEC)

Medido el 27/10/2026 (92.719 palabras).

```
python pipeline/09_grau_dialectal/gdv.py --fitxer pipeline/02_regles_dialectals/docs_gramatica/geiec_complet.txt
```

| Índice | Valor | Occidentales | Orientales | Neutras |
|---|---|---|---|---|
| GD | **0,2260** | 456 | 1.562 | — |
| GDC | **0,9951** | 456 | 1.562 | 90.701 |
| GDV | 0,9832 | 456 | 1.562 | 90.701 |

(La primera ejecución, con la fórmula del 26/10, daba "GDV 0,2260", que
es el GD.)

La GEIEC sale claramente catalana (77 % de sus marcadores son
orientales, GD 0,23). Los más frecuentes: "aquest/a/s/es" (427), "tenir"
(86), "seva/seves/teva" (88), "aquí" (47), "hagi/sigui/vagi" (54).

A primera vista es menos "pura" que la GNV (el 77 % de sus marcadores
son catalanes, frente al 87 % de valencianos en la GNV), pero la
diferencia no es de la gramática, sino del GD (ver abajo).

**Revisión de los marcadores occidentales.** Pasando el GD línea a línea
salen 518 / 1.594 (la diferencia con la CLI es de contexto de spaCy):

| Tipo | Marcadores | Palabras |
|---|---|---|
| **Error del GD: verbo valenciano que coincide con una forma catalana normal** | 138 | 1ª singular valenciana = 3ª singular catalana: "permet" (24), "admet" (16), "recau" (10), "pertany" (5), "remet", "transmet", "omet", "contrau", "pateix" (62). Subjuntivo valenciano = indicativo catalán en 3ª plural: "pronuncien" (30), "situen" (14), "diferencien", "actuen", "associen", "consideren", "continuen", "creen"… y en 2ª singular: "arribes", "trobes", "parles" (76) |
| **Error del GD: homógrafo o palabra compartida** | 199 | "construcció" (57; par `E0087` "construcció"→"obra de paleta"), "he" (42), "després" (34), "tancada/tancat/tancades" (23; "vocal tancada"), "vora" (9; preposición), "xic" (6; "un xic de sal"), "ix" (6; dígrafo en la tabla de grafías), "fem" (5; verbo "fer"), "obrer", "tenis", "alça", "serien", "compostes", "roig", "bou", "xop", "patir", "pares" |
| **Registro**: palabra emparejada pero común en catalán culto | 94 | "vegada/vegades" (53; par `E1656` "vegada"→"cop"), "últim/última" (14), "bonic/bonica/boniques" (13), "alcalde", "telefonar", "entregar", "quasi", "duració"… |
| **Cita de formas valencianas**: la GEIEC es policéntrica y describe la variante valenciana | 87 | "ací" (11), "este/esta/eixe…" (7), pretérito en "-àrem" ("cantàrem", "dinàrem", "férem"…), subjuntivo en "-a" ("dorma", "servisca"), "haguera", "vos", "eixos", "prompte", "nàixer", "batle", "xiquet", "hui", "vesprada"… |

En el lado catalán hay también errores ya conocidos: "mentre" (42),
"afecta" (7), "nou" (1). En la GEIEC "us" (26) y "fos" (12) son el
pronombre y el subjuntivo, marcadores catalanes reales.

**Lectura.**

- Dos terceras partes de los marcadores valencianos (337 de 518) son
  errores del GD, y solo 87 son citas reales de formas valencianas.
- Quitando los errores de los dos lados (occidentales 518 − 337 = 181;
  orientales 1.594 − 50 = 1.544), el GD quedaría en unos **0,10** (90 %
  de marcadores catalanes), prácticamente simétrico a la GNV (0,89).
  Quitando también el registro, unos **0,06**. Cifras orientativas.
- **Hallazgo nuevo: el GD penaliza más los textos catalanes que los
  valencianos.** Muchas formas verbales valencianas del diccionario se
  escriben igual que una forma catalana normal de otra persona o modo:
  - "jo permet" (valenciano) = "ell permet" (catalán);
  - "que pronuncien" (subjuntivo valenciano) = "pronuncien" (indicativo
    catalán).

  En un texto catalán esas formas aparecen constantemente con el sentido
  catalán, y el GD las cuenta como valencianas. El GD descarta las formas
  que están en los dos lados del diccionario, pero "permet" (3ª) y
  "pronuncien" (indicativo) no están en el lado catalán porque no son
  pares dialectales (son iguales en los dos), así que la colisión no se
  detecta. En la GNV este error casi no se nota ("consideren" 7) porque un
  texto valenciano usa esas formas con el sentido valenciano.
- Este problema es del GD, no del léxico: no lo arregla la corrección de
  datos en curso. Posibles vías, sin probar todavía:
  1. 1ª singular: usar el rasgo `Person` de spaCy (solo contar "permet"
     si spaCy dice 1ª persona). `Mood` no sirve (medido el 20/10), pero
     `Person` no se ha medido.
  2. 3ª plural de subjuntivo: no hay forma de distinguirla del indicativo
     sin contexto. Opción: no contarla nunca como marcador (perdería
     también los subjuntivos valencianos reales).

  Cualquiera de las dos hay que medirla en todos los corpus antes de
  decidir.

## 5. Remedición del 28/10/2026 (léxico del compañero fusionado)

Qué se midió: todos los corpus, con `mesura_corpus.py --reinicia`, tras
fusionar `origin/lista-lexico` (commits `e0bace3` y `ea24adc` de
mga155-ua, 27/10) y sincronizar `traductor/data/` (`33e57de`). El código
del GD no ha cambiado; solo los datos.

```
python pipeline/09_grau_dialectal/mesura_corpus.py --reinicia
```

### Qué traía el léxico nuevo

- `lexico_general.json`:
  - `E0977` "després" marcado `homonimia_lexica` (lemas adj/adv);
  - seis entradas nuevas: `E1662`/`E1663` forqueta(es)→forquilla(es),
    `E1664` fi→finalitat, `E1665` fins→finalitats (las dos
    `homonimia_lexica`), `E1666`/`E1667` naixement(s)→naixença(es).
- `verbos_diferentes_conjugados.json`: 69 filas nuevas, como
  xuplar/xuclar, sobreeixir/sobresortir, tindre, obtindre, mantindre,
  llavar, entregar, generar y firmar. Además se recalcularon las marcas
  de ambigüedad de 70 filas.

Comparando el índice de marcadores del GD antes y después:
- solo entran 56 formas occidentales nuevas y 59 orientales nuevas
  (casi todas de xuplar/sobreeixir, y las de las entradas nuevas del
  léxico);
- salen 12 formas de cada lado: conjugaciones raras de sobreeixir/xuclar
  que ahora están en los dos lados;
- "fi" y "fins" pasan a no contar nunca, porque son homógrafos
  irresolubles;
- "després" pasa a contar solo si spaCy lo etiqueta como adjetivo.

Los verbos frecuentes (tindre, obtindre, generar…) ya estaban en el
índice por `conjugaciones_general.json`, así que no cambian nada en el
GD.

### Diferencias, explicadas marcador a marcador

Toda la diferencia entre el 27/10 y el 28/10 sale de tres cambios:

| Cambio | 151 val | 151 cat | GNV | GEIEC | BOE val | BOE cat | Valoración |
|---|---|---|---|---|---|---|---|
| "després" deja de contar (spaCy nunca lo da como adjetivo) | −17 occ | −17 occ | −22 occ | −34 occ | −1.972 occ | −1.456 occ | **Arreglo**: era el adverbio compartido |
| "finalitat/s" pasa a marcador catalán (`E1664`/`E1665`) | — | — | +5 or | +2 or | **+1.619 or** | +3.206 or | **Error de dato**: "finalitat" es la palabra normal también en valenciano (el BOE valenciano la usa 1.619 veces) |
| "naixement/s" pasa a marcador valenciano (`E1666`/`E1667`) | — | — | +1 occ | +2 occ | +301 occ | +303 occ | **Error de dato o registro**: el BOE catalán usa "naixement" igual que el valenciano (303 frente a 301) |
| Resto (forquetes, sobreeixir, xuclar…) | — | — | — | — | +2 occ | +6 or | Sin efecto |

Con eso cuadran exactamente todos los recuentos. Por ejemplo, en el BOE
valenciano: 191.527 + 303 − 1.972 = 189.858 marcadores occidentales, y
11.714 + 1.619 = 13.333 orientales.

### Lectura

- **"després" quedó resuelto**: el lado catalán del 151 baja de 0,1267 a
  **0,0727**, el BOE catalán de 0,0684 a 0,0625 y la GEIEC de 0,2453 a
  0,2334. Era el error más grande del GD (sección 1).
- **El BOE valenciano empeora (0,9424 → 0,9344) por un dato nuevo, no
  por el texto**:
  - "finalitat" entra como forma solo catalana, y es la palabra normal
    en los dos estándares;
  - sin ese par, el BOE valenciano daría **0,9419**, prácticamente
    igual que antes: el arreglo de "després" apenas le afecta
    (−0,0005), porque allí "després" hinchaba el lado bueno;
  - la GNV baja por lo mismo (0,8678 → 0,8595): pierde 22 "després" y
    gana 5 "finalitat".
- **"naixement/naixença"** tiene el mismo problema, más pequeño:
  "naixement" es normal en los dos BOE y ahora cuenta como valenciano en
  el catalán.
- GDV y GDC casi no se mueven (cuarta cifra), como siempre: las neutras
  lo diluyen.

### Efecto en el traductor (cat→val), visto de paso

Las entradas nuevas también cambian la traducción:
- "La finalitat d'aquesta llei" pasa a "La fi d'esta llei";
- "Amb les finalitats previstes" pasa a "Amb les fins previstes", con el
  género mal: "fi" en el sentido de finalidad es masculino.

El BOE catalán tiene 3.206 apariciones de "finalitat/s" y la referencia
valenciana usa "finalitat" (1.619). Es probable que esto baje los
benchmarks del BOE. Falta medirlo: hay que pasar los benchmarks cat→val
del 151, del BOE estricto y del BOE amplio.

"fins a" y "la fi del mes" no se tocan, porque son homógrafos
irresolubles. "després" sigue traduciéndose bien.

### Propuesta para el compañero (no se ha tocado nada)

- **`E1664`/`E1665` (fi/fins → finalitat/s)**: revisar. "Finalitat" es
  valenciano normativo y es la forma del BOE valenciano. Si el par se
  queda, en cat→val produce "les fins" (género mal).
- **`E1666`/`E1667` (naixement/naixença)**: revisar. "Naixement" es la
  forma habitual en los dos BOE.
- Siguen abiertos los otros errores de las secciones 1 y 2: `E0434`
  "rebuda"/"recepció", `E0087` "construcció", `E0537`/`E0538` "tancada",
  `E0251` "afecte/afecta", `E1625` "eixos", "deu" numeral, "mentre"
  (este último es código de `gd.py`) y la colisión verbal.

### BOE por documento (28/10)

GD medio 0,9439 en el lado valenciano (mediana 0,9808; 39 de 498
documentos con marcadores por debajo de 0,8) y 0,0746 en el catalán
(mediana 0,0578; 17 de 489 por encima de 0,2).

## 6. Benchmark manual cat→val (453 frases)

**Fichero**: `dades/benchmark_manual/benchmark_manual_cat_val.json`. Son
241 frases del BOE y 212 de la AVL, revisadas a mano por el equipo. Cómo
se generó: `documentacio/hoja_de_ruta_benchmark_manual.md`, sección 7.

**Medida**: 28/10/2026, con los datos recién sincronizados
(`sync_data --check` → "Tot sincronitzat"; incluye "eliminacion
cadascu" y los cambios en los verbos). Remedido a las 16:20 con la
versión regenerada por `construeix_benchmark.py` (que incluye las
últimas ediciones de la revisión): mismas cifras a cuatro decimales. El benchmark se ha añadido a
`mesura_corpus.py` como `manual_val` / `manual_cat`.

```
python pipeline/09_grau_dialectal/mesura_corpus.py --corpus manual_val manual_cat --reinicia
python pipeline/09_grau_dialectal/gd.py --corpus dades/benchmark_manual/benchmark_manual_cat_val.json --camp occidental --camp-alt oriental --html pipeline/09_grau_dialectal/proves/gd_benchmark_manual.html
```

Para ver las frases una a una, con los marcadores resaltados:
`pipeline/09_grau_dialectal/proves/gd_benchmark_manual.html`. Los
resultados por frase están en `dades/grau_dialectal/manual_val.jsonl` y
`manual_cat.jsonl`.

| Lado | Fuente | Frases | Palabras | occ | or | GD global / media | GDV | GDC | Sin marcadores |
|---|---|---|---|---|---|---|---|---|---|
| valenciano | BOE | 241 | 7.717 | 600 | 5 | 0,9917 / 0,9941 | **0,9994** | 0,9222 | 0 |
| valenciano | AVL | 212 | 5.499 | 483 | 0 | 1,0000 / 1,0000 | **1,0000** | 0,9122 | 1 |
| valenciano | **total** | 453 | 13.216 | 1.083 | 5 | **0,9954** / 0,9969 | **0,9996** | 0,9181 | 1 |
| catalán | BOE | 241 | 7.690 | 5 | 606 | 0,0082 / 0,0059 | 0,9212 | **0,9993** | 0 |
| catalán | AVL | 212 | 5.501 | 31 | 448 | 0,0647 / 0,0628 | 0,9186 | **0,9944** | 1 |
| catalán | **total** | 453 | 13.191 | 36 | 1.054 | **0,0330** / 0,0324 | 0,9201 | **0,9973** | 1 |

La única frase sin marcadores es BM-AVL-057 ("t'haig de dir" → "t'he de
dir"). "haig" no cuenta como marcador por la fila `LIMPIO_588`.

**Lectura**

- Es el corpus **más puro y mejor separado** de todos los medidos: GD
  0,9954 frente a 0,0330. El 151 da 0,9854 frente a 0,0727 y el BOE
  completo 0,9344 frente a 0,0625.
- Tiene mucha densidad de fenómenos: 2,4 marcadores por frase, frente a
  1,8 en el 151. Era el objetivo de la selección.
- **GDV del lado valenciano: 0,9996** y **GDC del lado catalán: 0,9973**.
  Es casi el máximo posible.

### Revisión de los marcadores cruzados

**Lado valenciano: 5 marcadores orientales**, ninguno real:

| Palabra | Frases | Tipo |
|---|---|---|
| finalitat/s | BM-BOE-087, 089, 103 y 167 | Error de dato: `E1664`/`E1665` (sección 5) |
| estat | BM-BOE-065 ("haja estat") | Registro: participio de "ser", aceptado en valenciano |

**Lado catalán: 36 marcadores occidentales** (5 en el BOE y 31 en la
AVL):

| Tipo | Marcadores | Frases |
|---|---|---|
| **Posible errata en el catalán** (para revisar) | 4 | BM-BOE-024 "que **calga** lliurar" (en catalán, "calgui"); BM-BOE-165 "que **siga establida**" (en catalán, "sigui establerta"; cuenta 2); BM-BOE-078 "hagi **sigut**" (en catalán estándar, "hagi estat") |
| **Error del GD: colisión verbal** (§4.2) | 25 | 3ª singular catalana = 1ª valenciana: permet ×3, transmet ×2, compromet ×2, admet, emet, sotmet, subjau, acull, pateix, abelleix. 3ª plural indicativo = subjuntivo valenciano: consideren, diferencien, estudien, varien, comparen, testimonien, guien, recuperen, serien. Además: escoltes, equipara |
| **Error del GD: homógrafo o dato** | 7 | "construcció" ×2 (`E0087`), "fem" ×2 (verbo "fer"), "naixement" (`E1666`), "bous" (plural de "bou", animal), "rosa" (*El nom de la rosa*) |

**Posible errata no detectada por el GD**: BM-AVL-161 "quatre anys
**desprès**" lleva acento grave; en catalán es "després". "desprès"
(adjetivo, "desprendido") ya no cuenta como marcador desde el 28/10.

Quitando los errores del GD, el lado catalán quedaría en unos **0,004**
(4 / 1.058) y el valenciano en **1,0000** (o 0,9991 si "estat" cuenta).
Son cifras orientativas. Casi todo lo que baja el catalán de la AVL es
la colisión verbal: son formas catalanas correctas ("permet", "consideren")
que el GD cuenta como valencianas.

**Para el equipo** (no se ha tocado nada del benchmark): revisar el
catalán de BM-BOE-024, BM-BOE-078, BM-BOE-165 y BM-AVL-161.

## 7. Los tres benchmarks manuales (30/10/2026, BOE revisado de nuevo)

El BOE del benchmark manual se ha vuelto a revisar desde el texto
original alineado; la revisión anterior está archivada (ver
`hoja_de_ruta_benchmark_manual.md`, sección 9). La sección 6 corresponde
a esa revisión anterior y no es comparable con esta.

Ahora hay tres benchmarks, que salen de `construeix_benchmark.py`:
el **BOE** (246 frases), la **AVL** (212, la misma revisión que en la
sección 6) y la **mezcla** de los dos (458). Medidos con
`mesura_corpus.py` (`manual_boe_*`, `manual_avl_*`, `manual_*`):

| Benchmark | Lado | Frases | Sin marcadores | occ | or | GD global | GDV global | GDC global | GD media | GDV media | GDC media |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BOE | val | 246 | 0 | 608 | 3 | 0,9951 | 0,9996 | 0,9226 | 0,9970 | 0,9996 | 0,9201 |
| BOE | cat | 246 | 0 | 0 | 618 | **0,0000** | 0,9214 | **1,0000** | 0,0000 | 0,9188 | 1,0000 |
| AVL | val | 212 | 1 | 481 | 0 | **1,0000** | **1,0000** | 0,9125 | 1,0000 | 1,0000 | 0,9017 |
| AVL | cat | 212 | 1 | 29 | 449 | 0,0607 | 0,9184 | 0,9947 | 0,0581 | 0,9079 | 0,9941 |
| Mezcla | val | 458 | 1 | 1.089 | 3 | 0,9973 | 0,9998 | 0,9184 | 0,9984 | 0,9998 | 0,9116 |
| Mezcla | cat | 458 | 1 | 29 | 1.067 | 0,0265 | 0,9202 | 0,9978 | 0,0268 | 0,9137 | 0,9973 |

Con la revisión anterior (453 frases, sección 6), la mezcla daba GD
0,9954 en el lado valenciano y 0,0330 en el catalán.

**Marcadores cruzados que quedan** (revisados uno a uno):

- **BOE valenciano, 3 orientales**: "finalitat" en BM-BOE-087, 089 y 167.
  Es el error de dato de `E1664`/`E1665` (sección 5), no de la revisión.
- **BOE catalán, 0 occidentales.** Las erratas que había en la revisión
  anterior ("calga", "sigut", "siga establida") ya no están.
- **AVL valenciano, 0 orientales.**
- **AVL catalán, 29 occidentales**, todos errores conocidos del GD y
  ninguno de la revisión:
  - **Colisión verbal** (sección 2, problema abierto 1): permet ×3,
    compromet ×2, transmet ×2, sotmet, emet, admet, acull, pateix,
    abelleix, subjau (3ª singular catalana = 1ª valenciana); consideren,
    diferencien, estudien, varien, comparen, testimonien, guien,
    recuperen, serien (3ª plural de indicativo = subjuntivo valenciano);
    también escoltes y equipara.
  - **Homógrafo o dato**: "fem" ×2 (verbo "fer"), "naixement" (`E1666`),
    "rosa" (BM-AVL-146).

Si se quitan estos errores del GD, los tres benchmarks quedan puros: GD
1 en el lado valenciano y 0 en el catalán.

Resultados por frase en `dades/grau_dialectal/manual_*.jsonl` (fuera de
git); resumen en `dades/grau_dialectal/resum.{json,md}`.
