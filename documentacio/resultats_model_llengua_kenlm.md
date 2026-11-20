# Modelo de lengua para las palabras ambiguas: FLOR frente a KenLM y fastText

Documento vivo (desde el 10/11/2026). Recoge **todas** las pruebas para
sustituir o complementar a FLOR-760M en la decisión de las palabras ambiguas
de cat→val: qué se probó, cómo funciona cada cosa, los resultados y las
decisiones. Cada resultado o decisión nueva se añade aquí, con su fecha, y al
**registro de decisiones** (sección 8).

Código: `pipeline/03_seleccio_de_model/model_llengua/` (`compara_models.py`,
`simula_marges.py`, `visor_compara_models.html`) y
`pipeline/08_traduccio_corpus/macocu/` (filtros de MaCoCu, `kenlm/`,
`fasttext/`). Resultados en `pipeline/03_seleccio_de_model/resultats/`
(fuera de git).

## Estado actual (13/11/2026)

**El modelo por defecto es KenLM + clasificador de sentido** (decisión del
usuario, 13/11/2026). FLOR-760M queda como opción (`model="flor"`, extra
`[ml]`) y sale de la imagen Docker.

| Benchmark (exactas) | Motor solo | FLOR-760M | **KenLM + clasificador** |
|---|---|---|---|
| Homógrafos v1 (253) | 181 | 217 | **227** |
| Homógrafos v2 (160) | 82 | 96 | **111** |
| Manual mezcla BOE + AVL (458) | 218 | 231 | **232** |
| 151 (154) | 142 | **145** | 144 |
| BOE estricto (2.000) | 1.800 | 1.894 | 1.894 |
| gplsi (1.958) | 1.533 | **1.551** | 1.550 |

(KenLM: `avalua_sistema_20261113_1308`, con la tabla de frecuencias
corregida, el clasificador general y la regla de «una nou»; FLOR y motor:
`_1016`.) En las 257 decisiones de los homógrafos: 193 aciertos, 1 error
grave (HG2-028 «Si en falta algun», valenciano correcto) y 63 sin traducir; «manques» no se traduce nunca (33 apariciones
en el corpus frente a 420 de «faltes»). Coste: 0,1 ms por frase candidata y
~74 MB, frente a 833 ms y ~1,5 GB de FLOR; sin `torch`.

**El sistema, pieza a pieza** (con la sección donde se decidió):
1. Motor de reglas → frases valencianas completas por cada candidata de
   cada palabra ambigua del léxico (como con FLOR).
2. spaCy descarta lecturas imposibles (categoría distinta de la dialectal,
   concordancia con el determinante y, desde el 13/11, pronombre personal
   delante: sección 8).
3. KenLM `valencia_net_dogv_o5`: MaCoCu valenciano limpio + DOGV
   2025-2026, orden 5, poda de singletons, 77 MB (secciones 3, 4.4, 4.9).
4. Prior de frecuencia contado del texto de entrenamiento y λ (1,5 en los
   homógrafos, 0,75 en las colisiones) contra el sesgo de las palabras
   frecuentes (secciones 2.3, 2.4, 4.5).
5. Margen 3 con la catalana por defecto: si KenLM duda, se queda la
   palabra catalana (un error leve en vez de uno grave; sección 4.10).
6. Si KenLM gana por menos de 2, decide el clasificador de sentido de la
   palabra, si tiene uno que haya demostrado acertar (≥ 0,7 en frases
   apartadas; hoy cop, cops y deu): Naive Bayes entrenado con MaCoCu + DOGV,
   sin la AVL (secciones 4.11, 4.15 y tabla de decisiones del 13/11).

**Descartado** (con su sección): KenLM catalán «menos probable» y fastText
(4.1), diferencia val − cat (4.1), KenLM sin poda y + AVL + UA (4.9),
KenLM en dos sentidos (4.12), veto del clasificador (4.13), híbrido FLOR
para «cop» (el usuario no quiere FLOR en la imagen; 4.8), KenLM de lemas y
mezcla formas + lemas (4.16), KenLM de orden 6, 7 u 8 (4.18).

**Siguiente**: más datos para que más palabras pasen el umbral del
clasificador (DOGV nuevo; «nou», «manca»...). Pendiente aparte: publicar los ficheros de KenLM en
Hugging Face (revisar antes las condiciones de reutilización del DOGV).

---

## 1. El problema y cómo se mide

En cat→val, algunas palabras catalanas tienen varias traducciones posibles o
ninguna:

- **Colisiones**: «cop» → «colp» (golpe) o «vegada» (vez); «cops» → «colps» o
  «vegades». La palabra catalana no es candidata: siempre hay que elegir.
- **Homógrafos irresolubles**: «gandula» → «hamaca» (tumbona) o «gandula»
  (vaga); también «manca», «nou», «calces», «recuita», «fartanera»,
  «panotxa», «rentadora». spaCy decide si la categoría lo permite; si no,
  decide el modelo.
- **Homógrafos resolubles**: «deu», «reeixida».

El motor construye la **frase valenciana completa** con cada candidato y un
modelo de lengua puntúa cada frase. Gana la mejor según el **criterio**
(`Criteri`):

- **Margen** (`marge`): la opción por defecto solo se cambia si la otra gana
  por más de `marge` puntos (logaritmo natural).
- **Por defecto** (`per_defecte`): la palabra catalana (decisión del usuario,
  05/11) o la elección del motor.
- **λ** (`lam`): puntuación = log P(frase) − λ · log P(candidato solo). Ver la
  sección 2.4.

Sistema actual (desde el 05/11): FLOR-760M, margen 2, la catalana por
defecto, λ 0,5.

**Medida principal**: las 257 decisiones de los homógrafos v1 (99) y v2 (158)
con candidato esperado, clasificadas así:

- **acierto**;
- **error grave**: cambia el sentido, porque traduce sin hacer falta
  («calces» de época → «bragues») o elige el otro candidato («colp» por
  «vegada»);
- **error leve**: se queda la palabra catalana sin traducir.

Objetivo: **≤ 3 errores graves** (los de FLOR) y más aciertos. También se
miran el manual (458 frases: exactas, chrF, TER, WER, GD), el coste en CPU y
la memoria.

---

## 2. Cómo funciona cada modelo

### 2.1 FLOR-760M (sistema actual)
Modelo neuronal (transformer, BLOOM) entrenado por Projecte AINA con catalán.
Lleva delante un párrafo valenciano fijo (P1) para que «piense» en
valenciano. Ve **la frase entera**. Coste: ~0,8 s por frase candidata en CPU,
1,5 GB de memoria y necesita torch.

### 2.2 KenLM (modelo de n-gramas)
Cuenta secuencias de hasta 5 palabras en un texto y estima P(palabra | las 4
anteriores). Si no ha visto ese contexto, **retrocede** (*backoff*) a uno más
corto: 3, 2 o 1 palabra. Es muy rápido (~0,05 ms) y ocupa poco (60-130 MB),
pero:

- cada palabra se puntúa con **las 4 anteriores** como mucho. El candidato se
  puntúa solo con su izquierda («molts colps» frente a «moltes vegades»), y
  ahí manda la frecuencia. La derecha cuenta a través de las palabras
  siguientes, P(cara | colps a la), pero solo si están a ≤ 4 palabras y la
  secuencia exacta se vio al entrenar; si no, retrocede a «a la cara», que ya
  no incluye el candidato. En «molts cops a la cara» la derecha sí ayuda a
  «colps» (+3,24), pero no basta (corregido el 11/11);
- lo que aprende depende de la **frecuencia** en el texto de entrenamiento.

Entrenamiento: `lmplz` con orden 5 y **poda de los n-gramas que aparecen una
sola vez** desde los bigramas (`PODA="0 1 1 1 1"`). El binario es un trie
cuantizado a 8 bits.

### 2.3 Los unigramas de KenLM (por qué no sirven de frecuencia)
KenLM suaviza con **Kneser-Ney modificado**:

- En el orden más alto (5-gramas), la probabilidad sale de cuántas veces se
  vio la secuencia, con un descuento.
- En los órdenes bajos, y en particular en el **unigrama**, Kneser-Ney **no
  usa cuántas veces aparece la palabra**, sino **en cuántos contextos
  distintos aparece** (*continuation count*: cuántas palabras distintas la
  preceden).

El motivo: el unigrama solo se usa al retroceder, cuando el contexto es
nuevo. Entonces lo útil es saber si la palabra suele aparecer en contextos
nuevos. Ejemplo clásico: «Francisco» es frecuente, pero casi siempre va
detrás de «San».

En nuestros datos:

| | apariciones en el texto | log P unigrama de KenLM |
|---|---|---|
| vegada | 87.697 | −9,89 |
| colp | 2.382 | −10,66 |

«vegada» sale 35 veces más, pero en pocos contextos («una», «altra», «cada»,
«primera» vegada...). «colp» sale en contextos más variados. Por eso el
unigrama de KenLM los deja casi iguales (×2 en vez de ×35).

Además, hasta el 11/11 el comparador calculaba el prior como log P(«<s> colp
</s>»), es decir, la palabra sola como **frase entera**. Esto daba a «colp»
(−20,95) **más** probabilidad que a «vegada» (−22,27), y por eso λ no hacía
nada con KenLM.

**Solución (11/11)**: prior = ln((n + 1) / tokens), con n = apariciones en el
texto de entrenamiento (`freq_unigrames.py` → `<modelo>_freq.json`).

### 2.4 λ (corrección de la frecuencia)
puntuación = log P(frase) − λ · log P(candidato).

- **λ = 0**: la frase más probable sin más. Favorece la palabra frecuente
  («vegada»).
- **λ = 1**: equivale a la **información mutua** (PMI). Mide cuánto encaja el
  contexto con la palabra más allá de su frecuencia.
- **λ demasiado alto**: favorece la palabra rara aunque no encaje. Con FLOR,
  a partir de λ 1,25, «cop» empieza a fallar.

El mejor λ de las colisiones no es el mismo que el de los homógrafos. Desde
el 11/11, `Criteri` tiene `lam_colisio` (`None` = el mismo `lam`).

### 2.5 `diff` y `diff_net` (diferencia valenciano − catalán)
puntuación = log P_valenciano(frase) − log P_catalán(frase). Se usan dos
KenLM: el valenciano (`valencia` o `valencia_net`) y el catalán (MaCoCu
entero).

- **Idea**: las dos probabilidades castigan igual una frase rara o
  agramatical, así que la resta anula la «fluidez general» y deja la señal
  dialectal (lo que es más típico del valenciano que del catalán).
- **Problema**: premia **lo más valenciano**, no **lo correcto**. «colp» solo
  existe en valenciano y «vegada» en los dos, así que `diff` elige «colp»
  casi siempre.
- **Resultado**: bien en v2 (93/132, el mejor), donde abundan los «colp»
  correctos, y mal en v1 (30/57), donde hace falta «vegada».
- **Coste**: necesita también el modelo catalán (~3 GB).

### 2.6 `kenlm_cat` (menos probable en catalán)
Idea del usuario: puntuación = −log P_catalán(frase); gana la frase que menos
se parece al catalán.

Traduce casi siempre, porque cualquier forma valenciana es improbable en
catalán, y no distingue sentidos. El tamaño no influye: con el 30 % de
MaCoCu sale lo mismo.

### 2.7 fastText (clasificador valenciano/catalán)
- **Entrenamiento**: valenciano = frases de MaCoCu con GD 1,0 y ≥ 2
  marcadores (335.530); catalán = muestra del mismo tamaño de `catala_pur`.
- **Puntuación**: logit(val) − logit(cat), es decir, la salida lineal antes
  del softmax, porque las probabilidades salen saturadas (1 / 0,00001).
- **Validación**: 99,95 %, pero poco informativa, porque las clases salen de
  los mismos marcadores del GD.
- **Problema**: clasifica el dialecto, no el sentido. «una altra vegada» le
  parece valenciano porque «vegada» es marcador del GD, así que no puede
  elegir entre «vegada» y «colp».

### 2.8 Híbrido (propuesta del 11/11)
FLOR decide solo las colisiones (cop/cops) y KenLM el resto. Así FLOR solo
trabaja en las frases con «cop», pero tiene que estar cargado.

---

## 3. Datos de entrenamiento de los KenLM

| Modelo | Texto | Tamaño `.binary` |
|---|---|---|
| `macocu_tot_o5` (`kenlm_cat`) | MaCoCu-ca entero (11 GB de texto) | 3,0 GB |
| `macocu_30pc_o5` (`kenlm_cat30`) | el 30 % | 945 MB |
| `valencia_o5` (`kenlm_val`) | 2,86 M frases valencianas de MaCoCu (GD > 0,5, ≥ 1 marcador) | 136 MB |
| `valencia_net_o5` (`kenlm_val_net`) | 1,21 M frases: ≥ 2 marcadores, o de un documento con alguna así (36 M tokens) | 63 MB |
| `valencia_net_dogv_o5` (`kenlm_val_net_dogv`) | lo anterior + DOGV 2025-2026 filtrado (163.558 frases, 9,6 M tokens) | 77 MB |
| `valencia_net_dogv_np_o5` (`kenlm_val_net_dogv_np`) | igual, **sin poda** | 444 MB |
| `valencia_tot_np_o5` (`kenlm_val_tot_np`) | net + DOGV + AVL (sin evaluación) + UA (GD ≥ 0,8), sin poda | 472 MB |

Fuentes estudiadas y descartadas:

- **BOE valenciano**: 0 «colp» y 2.709 «vegada».
- **Noticias de la UA** (`ua_noticias_va.jsonl`): no son de À Punt. Usan el
  estándar de la UA (aquest, avui, servei; GD 0,46). Solo serviría el 15 % de
  frases con GD ≥ 0,8.

---

## 4. Resultados

### 4.1 Comparación de todos los modelos (10/11)
Fichero: `compara_models_20261110_1354`. Criterio del sistema (margen 2, la
catalana por defecto, λ 0,5). «Sentido» = candidato esperado en colisiones e
irresolubles (v1 /57, v2 /132).

| Modelo | Sentido v1 | Sentido v2 | Total /189 | Exactas v1 / v2 / manual | ms por llamada | Memoria |
|---|---|---|---|---|---|---|
| motor solo | 12 | 56 | 68 | 176 / 77 / 215 | — | — |
| flor | **47** | 77 | 124 | 219 / 95 / 228 | 833 | 1.544 MB |
| kenlm_val_net | 43 | **90** | **133** | **220 / 108 / 228** | **0,065** | **59 MB** |
| kenlm_val | 43 | 85 | 128 | 219 / 106 / 228 | 0,087 | 130 MB |
| diff_net / diff | 30 / 31 | 93 / 89 | 123 / 120 | 200 / 105 / 217 | 0,13 | ~3 GB |
| fasttext | 29 | 75 | 104 | 196 / 91 / 218 | 0,086 | 71 MB |
| kenlm_cat30 / kenlm_cat | 21 / 19 | 84 / 79 | 105 / 98 | 188 / 92 / 217 | 0,065 | 924 MB / 3 GB |

En el manual, FLOR y los KenLM valencianos son idénticos: TER 5,59, WER 5,98,
GD 0,9936, GDV 0,9995.

### 4.2 Desglose de errores (10/11)
Fichero: `compara_models_20261110_1421_detall`. 257 decisiones, criterio del
sistema.

| Modelo | Aciertos | Graves | Leves (sin traducir) |
|---|---|---|---|
| flor | 168 | **3** | 86 |
| kenlm_val | 179 | 18 | 60 |
| kenlm_val_net | **182** | 19 | 56 |

- Los errores graves de KenLM se concentran en **cop/cops → vegada** (6) y
  **reeixida(es) → exitosa(es)** (9, «La exitosa del projecte»).
- KenLM gana a FLOR en gandula (16 frente a 8), nou/nous, fartanera y
  panotxa.

### 4.3 Margen de KenLM (10/11, simulado)
- `kenlm_val_net` con **margen 6**: 169 aciertos, 9 graves, 79 leves.
- Los 9 de «reeixida» bajan a 1.
- **«cop» no mejora con ningún margen**: en las colisiones la catalana no es
  candidata y el motor no elige, así que siempre decide el modelo.

### 4.4 DOGV (10-11/11)
`kenlm_val_net_dogv`: 184 aciertos (+2, en v2: 92/132) y **los mismos 19
graves**. El DOGV no tiene «colp» (6 frente a 7.337 «vegada») ni «reeixida».

### 4.5 Prior corregido y λ (11/11, simulado)
Ficheros: `compara_models_20261111_0931_detall` y `simula_marges.py`.

| Configuración (`valencia_net_dogv`) | Aciertos | Graves | Leves |
|---|---|---|---|
| FLOR actual | 168 | 3 | 86 |
| KenLM, prior antiguo («<s> w </s>») | 184 | 19 | 54 |
| KenLM, prior = unigrama de KenLM; margen 4, λ 2 en colisiones / 1,5 en homógrafos | 189 | 5 | 63 |
| KenLM, prior = **frecuencia**; margen 3, λ 0,75-1,25 / 1,5 | 189 | 4 | 64 |
| **Híbrido**: FLOR en cop/cops + KenLM (frecuencia) en el resto; margen 3, λ 1,5 | **191** | **2** | 64 |

- Con el prior de frecuencia, los graves de «reeixida» desaparecen y los de
  «cop» bajan de 6 a 2.
- Con el unigrama de KenLM, ninguna combinación baja de 5 graves.
- Los 2 graves del híbrido son de «manca»: HG069 «una manca greu de personal»
  y HG2-028 «Si en manca algun», donde es verbo. FLOR también falla HG2-028.

### 4.6 Trazas: dónde pierde cada modelo (11/11)
`compara_models.py --traces` guarda la log P de cada token y
`visor_compara_models.html` las enseña.

Se separa la diferencia entre el candidato esperado y el otro en dos partes:
la de **la propia palabra** y la del **resto de la frase**. En los errores
graves de KenLM casi todo se pierde **en la palabra**:

| Frase | Esperado | Pierde en la palabra | Resto de la frase |
|---|---|---|---|
| A cops de destral van obrir la porta | colps | −7,66 | +4,53 |
| El boxejador va rebre molts cops a la cara | colps | −7,86 | +3,24 |
| Els lladres van preparar un últim cop al banc | colp | −4,26 | +0,21 |
| La reeixida del projecte depèn de tots | reeixida | −5,88 | −0,61 |

Es decir: KenLM sí ve algo del contexto bueno, pero la **frecuencia de la
palabra** lo tapa. Esto es lo que corrige el prior.

FLOR, además, usa el **contexto de la derecha**: castiga «cara» detrás de
«vegades» (−6,4 frente a −1,9). Por eso acierta 33/33 en «cop».

### 4.7 ¿Faltan datos de las palabras raras? (11/11)
Script: `pipeline/08_traduccio_corpus/macocu/kenlm/termes_ambigus.py`;
resultados en `dades/macocu/kenlm/termes/termes.md`. La AVL va sin nada de la
evaluación: se quitaron 233 documentos y 88 frases parecidas.

| | MaCoCu limpio + DOGV (45 M tokens) | AVL (1,5 M) | UA, GD ≥ 0,8 (1,4 M) |
|---|---|---|---|
| colp / vegada | 2.382 / 87.697 | 22 / 321 | 35 / 1.118 |
| colps / vegades | 882 / 61.256 | 10 / 316 | 5 / 243 |
| reeixida / exitosa | 51 / 621 | 3 / 3 | 0 / 5 |
| gandula / hamaca | 8 / 174 | 0 / 0 | 0 / 0 |
| recuita / fartanera / panotxa | 0 / 2 / 4 | 0 | 0 |

- En todas las fuentes «vegada» es 15-35 veces más frecuente que «colp»: es
  **cómo se usa la lengua**, no falta de datos. La AVL y la UA solo añaden un
  6 % de texto.
- En la UA, 14 de los 35 «colp» son «colp d'estat». En la AVL, parte salen de
  listas de palabras del glosario.
- recuita, fartanera, panotxa y gandula casi no existen en ningún corpus:
  ningún modelo de n-gramas puede aprenderlas. Se quedan con la palabra
  catalana por defecto.

### 4.8 Coste en CPU (10-11/11)

| | Tiempo dentro del modelo | Memoria |
|---|---|---|
| FLOR | 361 ms por frase (manual); 1,6 s (frases con palabra ambigua) | 1,5 GB, torch |
| KenLM | 0,02-0,09 ms por frase (~13.000 veces más rápido) | 60-77 MB |
| Híbrido | FLOR solo en las frases con cop/cops | FLOR cargado |

Frecuencia de «cop/cops» en texto real (11/11), es decir, la parte de
frases que pasarían por FLOR en el híbrido:

| Texto | Frases con cop/cops |
|---|---|
| BOE estricto (2.000) | 0 (0 %) |
| BOE muestra (2.000) | 4 (0,2 %) |
| gplsi (1.958) | 16 (0,8 %) |
| manual (458; la AVL está enriquecida con «cop») | 19 (4,1 %) |
| MaCoCu-ca | 596.367 «cop» en 1.772 M palabras (≈ 1 de cada 3.000 palabras, ~0,7 % de las frases) |

En media, el híbrido añade unos 10-15 ms por frase: 1,6 s en el ~1 % de
frases con «cop». El coste real no es el tiempo, sino **tener FLOR en la
imagen**: torch, 1,5 GB de memoria y ~5 s de carga, que se podría hacer
perezosa, solo cuando aparece el primer «cop».

### 4.9 Sin poda, AVL + UA y regresiones (11/11, ejecución `compara_models_20261111_1232`)
Modelos: FLOR, `kenlm_val_net_dogv`, `kenlm_val_net_dogv_np` (sin poda) y
`kenlm_val_tot_np` (sin poda, + AVL + UA). Benchmarks: homógrafos v1 y v2,
manual, 151 y BOE estricto (muestra de 2.000).

**Fallo en esta ejecución (y en la de las 09:31): el prior de frecuencia no
se aplicó.** El comparador envuelve cada modelo en un `Cronometre` (para
medir el tiempo) que solo pasaba `logprob`, así que el sistema no veía el
`prior` de KenLM y usaba el cálculo antiguo. Arreglado (`Cronometre.__getattr__`).

Las log P de las frases sí son buenas, así que las cifras de abajo se
**simulan** con el prior de frecuencia correcto (frecuencias del texto de
cada modelo, de `termes_ambigus.py`).

| Modelo | Mejor con ≤ 4 graves | Colisiones (33): mejor λ | Híbrido (FLOR en cop) | `.binary` |
|---|---|---|---|---|
| FLOR actual | 168 / 3 (criterio del sistema) | 33 / 0 | — | — |
| `kenlm_val_net_dogv` (con poda) | **189 / 4** (margen 3, λ 0,75-1,25 / 1,5) | 31 / 2 (λ 0,75 o 1,25) | **191 / 2** | 77 MB |
| `kenlm_val_net_dogv_np` (sin poda) | 185 / 4 (margen 3, λ 0,75-1,5 / 1,5) | 31 / 2 (λ 0,75-1,5, más estable) | 187 / 2 | 444 MB |
| `kenlm_val_tot_np` (+ AVL + UA, sin poda) | 186 / 4 (margen 2, λ 0,75-1,5 / 2) | 31 / 2 (λ 0,75-1,5) | 188 / 2 | 472 MB |

(aciertos / errores graves, sobre 257 decisiones)

- **Quitar la poda no mejora**: 185 frente a 189, y el modelo ocupa 6 veces
  más. Solo hace las colisiones algo más estables ante λ.
- **AVL + UA no aportan**: 186, en línea con la sección 4.7.

**Regresiones fuera de los homógrafos.** Para `kenlm_val_net_dogv` con margen
3, λ 1 en colisiones y 1,5 en homógrafos, se comparan sus decisiones
simuladas con las de FLOR en las frases con palabra ambigua:

- **BOE estricto**: 103 frases con palabra ambigua, **0 decisiones
  distintas** de FLOR (1.887/2.000 los dos).
- **151**: 4 frases; 1 distinta. RC025 «La rentadora és una màquina...»:
  KenLM deja «rentadora» y la referencia dice «llavadora» (error leve, −1
  exacta).
- **Manual**: 31 frases; 3 distintas:
  - **2 errores graves en texto real de la AVL**: BM-AVL-121 «detecten a cops
    errades» y BM-AVL-139 «mastegar dues cops», donde «cops» = «vegades».
    KenLM pone «colps» a partir de λ 1 (la 139, ya desde λ 0,5).
  - 1 acierto nuevo: BM-AVL-191 «anous».

**Lectura**: el λ alto que arregla los «colp» de los homógrafos (frases
inventadas, con muchos «colp» de golpe) estropea los «cop» = «vez» del texto
real («a cops», «dues cops»). Es la cautela de la sección 5 hecha realidad:
el λ de colisiones ajustado sobre los homógrafos **no generaliza**. Con el
**híbrido**, «cop» lo decide FLOR (acierta las dos frases) y KenLM solo
decide los homógrafos. En el texto real queda: manual +1 (anous), 151 −1
(rentadora, leve), BOE igual.

### 4.10 Base de KenLM y análisis de sus errores (11/11)
**Base elegida por el usuario: KenLM solo** (opción A, sin FLOR):
`valencia_net_dogv` con poda, prior de frecuencia, margen 3, λ 0,75 en
colisiones y λ 1,5 en homógrafos. Sobre las mejoras siguientes se medirá
contra esta base.

- Resultado: 189 aciertos y 4 graves (simulado).
- Se usa λ 0,75 en colisiones y no 1: en los homógrafos dan lo mismo, pero
  en el texto real λ 1 falla 2 frases de «cop» y λ 0,75 solo 1 (BM-AVL-139).

Errores graves de la base:

| Frase | Va | KenLM | Diferencia | Causa |
|---|---|---|---|---|
| HG009 Els lladres van preparar un últim **cop** al banc | colp | vegada | 0,45 | «una última vegada» muy frecuente; «al banc» solo con bigrama |
| HG022 El boxejador va rebre molts **cops** a la cara | colps | vegades | 0,38 | pierde 7 puntos en la palabra; «a la cara» devuelve ~3; «boxejador» casi desconocido |
| BM-AVL-139 mastegar **dues cops** els aliments (texto real) | vegades | colps | ~0 | empate; no aprovecha el femenino «dues» |
| HG069 Hi ha una **manca** greu de personal | carència | falta | — | ver abajo |
| HG2-028 Si en **manca** algun, avisa'm | manca | falta | — | ver abajo |

- **Los errores de «cop» son empates virtuales** (< 1 punto): KenLM no ve
  de qué trata la frase.
- **Los dos de «manca» son dudosos como errores**:
  - En HG069 se espera «carència», pero los candidatos del léxico para
    «manca» son «falta» y «manca»: el sistema nunca la puede producir. «Una
    falta greu de personal» es correcto.
  - En HG2-028 es el verbo «mancar»: «Si en falta algun» también es
    correcto, y FLOR hace lo mismo.
  - Pendiente de revisión del usuario; no se toca el benchmark. Si se acepta,
    la base tiene **2 graves reales** (los de «cop»).

### 4.11 Camino C1: clasificador de sentido para «cop» (11/11, local)
Script: `pipeline/03_seleccio_de_model/model_llengua/sentit_cop.py`. Modelos
en `dades/macocu/kenlm/sentit_cop/`: `nb.json` (259 KB) y `nb_genere.json`
(493 KB).

**Cómo funciona:**
- Naive Bayes en Python puro, entrenado con frases valencianas reales: net +
  DOGV + AVL, sin nada parecido a la evaluación. Son 3.123 usos de
  «colp(s)» y una muestra de 40.000 de «vegada(es)».
- La palabra se sustituye por un hueco.
- Rasgos: lemas de spaCy de las 2 palabras de cada lado, los bigramas de al
  lado y la bolsa de palabras a ±8.
- **Se ocultan las palabras que concuerdan** (determinantes, numerales,
  adjetivos y pronombres con género → `<DET>`, `<NUM>`, `<ADJ>`, `<PRON>`):
  en valenciano la concordancia delata el sentido («dues vegades»), pero en
  la entrada catalana «cop» es siempre masculino. spaCy no lematiza «una» ni
  «dues», así que el lema no basta. Los sustantivos no se ocultan («banc»,
  «cara» son pistas).

**Esquema (ejemplo real, HG009):**

```
ENTRENAMIENTO (una vez)
  texto valenciano (net + DOGV + AVL, sin la evaluación)
    → frases con colp(s) [3.123] o vegada(es) [muestra de 40.000]
    → la palabra → hueco __X__; etiqueta = colp | vegada
    → spaCy: lemas; las palabras que concuerdan → su categoría
    → rasgos: 2 palabras a cada lado (con posición), bigramas de al lado,
      palabras a ±8
    → cuántas veces sale cada rasgo con colp y con vegada → nb.json (~420 KB)
    (10 % de las frases apartado para medir: 83 % de acierto equilibrado)

USO (cada «cop/cops» del texto catalán)
  «Els lladres van preparar un últim cop al banc.»
  1. El motor genera las dos frases candidatas:
       A «...un últim colp al banc.»     B «...una última vegada al banc.»
  2. KenLM (base) las puntúa: log P(frase) − 0,75 · log P(palabra)
       gana B por 1,35 puntos
  3. ¿Gana por 2 puntos o más?  → sí: decide KenLM (la mayoría de casos)
                                 → no: lo decide el clasificador (paso 4)
  4. Clasificador sobre «<DET> lladre anar preparar <DET> <ADJ> __X__ <DET> banc .»
       cada rasgo suma log(frecuencia con colp / frecuencia con vegada):
         L1=<ADJ> −0,78   R1=<DET> −0,82   W=lladre +1,92   W=preparar +0,99
         W=banc +0,31   W=anar +0,28   ...   (los rasgos nunca vistos se ignoran)
       total +1,53 > 0 → colp
  5. «Els lladres van preparar un últim colp al banc.»  ✓
```

**Lo que aprende:**
- colp ← «d'estat», «d'ull», «de puny», «pegar un», «fort», «dur», «amb»,
  «rebre un», «militar».
- vegada ← «hi ha», «més», «cada», «tal», «altre», «per primera», «mil».

**Dos fallos encontrados y corregidos por el camino:**
1. **Rasgos desconocidos.** Con el suavizado y 13 veces menos datos de
   «colp», cada palabra que no salía en el entrenamiento empujaba +2,5 hacia
   «colp». Ahora se ignoran.
2. **La concordancia** se colaba (ver arriba).
3. **Se ocultaban también los sustantivos** («banc» → `<NOUN>`), porque
   tienen género. Ahora solo se ocultan las categorías que concuerdan. El
   acierto en los usos apartados no cambia (83,1 %); la regla sigue en
   33/33 + 19/19.

Integración (11/11): `Criteri.desempat` en el paquete (por defecto `None`,
no cambia nada) y `Punt.sentit`. En el comparador, el modelo
`kenlm_val_net_dogv_c1` (KenLM de la base + clasificador) con
`--desempats` y `--model-sentit`, y el benchmark opcional `gplsi` (16
frases reales con «cop»).

**Usos reales apartados del corpus** (4.739, 10 %), clasificador solo:
83,1 % equilibrado ocultando el género (colp 69 %, vegada 97 %) y 87,2 %
sin ocultarlo. Esta última cifra está inflada por la concordancia.

**Colisiones de los benchmarks**: 33 de homógrafos (inventadas) y 19 de texto
real del manual, sobre las trazas de `compara_models_20261111_1232`:

| Regla | Homógrafos | Texto real | Errores |
|---|---|---|---|
| FLOR | 33/33 | 19/19 | — |
| Base KenLM (λ 0,75) | 31/33 | 18/19 | HG009, HG022, BM-AVL-139 |
| Clasificador solo | 32/33 | 17/19 | HG025, BM-AVL-141, BM-AVL-190 |
| KenLM + 0,5 · clasificador | 32/33 | 19/19 | HG009 |
| **KenLM; si gana por < 2 puntos, decide el clasificador** | **33/33** | **19/19** | — |
| ídem con < 3 puntos | 32/33 | 19/19 | HG025 |

- La regla «KenLM decide; si gana por menos de 2 puntos, decide el
  clasificador» **iguala a FLOR en los 52 casos de «cop»**, en las dos
  variantes (con y sin ocultar el género).
- Arregla «últim cop al banc», «boxejador... molts cops» y «mastegar dues
  cops».
- Aplicada a la base (189 / 4), las colisiones pasarían a 33/33: en total
  **191 aciertos / 2 graves**, lo mismo que el híbrido, **sin FLOR**. Los 2
  graves que quedan son los dudosos de «manca».

**Cautelas:**
- El umbral (2) y los pesos se eligen sobre estos mismos 52 casos.
- Muestra pequeña: falta validar en más texto real (gplsi, BOE, usos del
  corpus con KenLM).
- En el sistema necesitaría spaCy (ya está en el traductor) y una tabla de
  ~420 KB.

### 4.12 Ejecución real: base, C1 y C2 (11/11, `compara_models_20261111_1430`)
Modelos: FLOR, `kenlm_val_net_dogv` (base), `kenlm_val_net_dogv_bi` (C2) y
`kenlm_val_net_dogv_c1` (C1). Benchmarks: homógrafos v1 y v2, manual, 151,
BOE estricto y gplsi. **Primera ejecución con el prior de frecuencia
aplicado de verdad** («colp» −9,86, «vegada» −6,25) y con el clasificador
cargado.

**257 decisiones de los homógrafos** con el criterio de la base (margen 3,
λ 1,5 en homógrafos, λ 0,75 en colisiones). Ya no es simulado:

| Modelo | Aciertos | Graves | Leves | Graves por palabra |
|---|---|---|---|---|
| FLOR (sistema) | 168 | 3 | 86 | manca, rentadores, recuita |
| Base KenLM | 189 | 4 | 64 | cop, cops, manca ×2 |
| C2 (dos sentidos) | 188 | 5 | 64 | cop, cops ×2, manca ×2 |
| **C1, desempate < 2** | **191** | **2** | 64 | manca ×2 (los dudosos) |
| C1, desempate < 1 / < 3 | 189 / 190 | 4 / 3 | 64 | |

**Frases exactas** (medida real; FLOR con este mismo criterio / FLOR con
el del sistema):

| | Homógrafos v1 | v2 | Manual | 151 | BOE estricto | gplsi |
|---|---|---|---|---|---|---|
| FLOR | 219 / 219 | 102 / 95 | 229 / 228 | 146 | 1.887 | 1.554 |
| Base KenLM | 225 | 110 | 228 | 145 | 1.887 | 1.552 |
| C2 | 224 | 110 | 228 | 145 | 1.887 | 1.552 |
| **C1 (< 2)** | **227** | **110** | **229** | 145 | 1.887 | 1.553 |

**«cop» en texto real, por sentido** (manual 19 + gplsi 16):

| | Aciertos | Fallos |
|---|---|---|
| FLOR | 35 / 35 | — |
| **C1 (< 2)** | **33 / 35** | gplsi «planejar un últim cop» (Δ 2,63), «Un tercer cop destrueix la nau» (Δ 5,77) |
| Base KenLM | 31 / 35 | los dos anteriores, «no es recuperaria d'aquest cop», BM-AVL-139 «dues cops» |

**gplsi usa «colp» con el sentido de «vez»** en su referencia («cada colp
més», «tres colps per setmana», «per primer colp», «un colp acabat el
torneig»; 8 de sus 16 «cop»). Es un uso coloquial valenciano; nuestro
criterio para «cop» = vez es «vegada». Por eso:

- en la tabla de arriba gplsi se cuenta **por sentido**;
- con la etiqueta literal de la referencia, FLOR se queda en 8/16;
- de ahí también que las exactas de gplsi bajen igual para todos.

**Lectura:**

- **El prior de frecuencia funciona en la ejecución real**: la base da
  189 / 4, igual que la simulación.
- **C2 no aporta**: 188 / 5, con el doble de memoria (147 MB). Descartado.
- **C1 es la mejor opción sin FLOR**:
  - 191 aciertos y 2 graves (los dos dudosos de «manca») en los homógrafos;
  - más exactas que FLOR en los homógrafos (v1 +8, v2 +15 frente al sistema
    actual) y en el manual (+1);
  - BOE igual; −1 en el 151 (RC025, «rentadora», leve) y −1 en gplsi.
  - En «cop» real falla 2 de 35, donde FLOR no falla ninguno. Los dos son
    golpes con KenLM seguro de lo contrario por más de 2 puntos: el
    clasificador no llega a intervenir.
- Coste: el de KenLM (0,02-0,1 ms por frase, 74 MB) más el clasificador
  (~420 KB). Sin torch.

### 4.13 Veto del clasificador y revisión de «manca» (11/11)
**Veto (simulado).** Idea: dejar que el clasificador contradiga a KenLM
cuando esté muy seguro, aunque KenLM gane por más de 2 puntos. **No ayuda.**

- En los dos «cop» reales que fallan, el clasificador tampoco está seguro:
  «planejar un últim cop» +1,26 y «Un tercer cop destrueix la nau» +0,85.
- Un veto bajo (|voto| ≥ 3) añade un error (BM-AVL-190); uno alto no cambia
  nada.
- La regla se queda en «desempate < 2».

Etiqueta por sentido usada para gplsi (asignada leyendo cada frase): colp =
46635, 42260, 25379, 62509, 33288; el resto, vegada.

**Revisión de «manca» (34 decisiones).** El léxico es incoherente entre el
singular y el plural:

| Entrada | Catalán | Valenciano |
|---|---|---|
| E0247 | manca | **falta** |
| E0248 | manques | **carències** |

El benchmark (y la referencia BM-BOE-219) espera «carència» en singular, que
el sistema no puede producir: para el sustantivo «manca» solo hay «falta» o
dejar «manca».

- **Verbo y adjetivo**: todos los modelos aciertan (casi siempre spaCy).
- **Sustantivo singular** (7, esperan «carència»): imposible. Todos dejan
  «manca» (leve), salvo C1 en HG069: «una falta greu de personal», que es la
  traducción del léxico y cuenta como grave.
- **Sustantivo plural** (6, esperan «carències»): C1 1/6 (HG075), FLOR 0/6.
- **HG2-028** «Si en manca algun» (verbo): C1 y FLOR ponen «Si en falta
  algun», correcto y con el mismo sentido; cuenta como grave para los dos.

| | Graves ahora | Contando HG069 y HG2-028 como correctos |
|---|---|---|
| FLOR | 3 (HG2-028, rentadores, recuita) | 2 |
| C1 | 2 (HG069, HG2-028) | 0 |

Propuesta, pendiente del usuario (no se ha tocado nada):

1. **Léxico (compañero)**: E0247 «manca» → «carència», coherente con E0248,
   el benchmark y el BOE.
2. **Benchmark**: aceptar «falta» en HG2-028 (y en HG069 si el léxico se
   queda en «falta»). Hoy el benchmark no admite más de una respuesta
   correcta.

---

### 4.14 Integración en el paquete (12/11, rama `kenlm`)
KenLM + C1 entra en el paquete como **opción complementaria**; FLOR sigue
por defecto.

- **Uso**: `translate_cat_val(text, model="kenlm")`, `avlizador tradueix
  --model kenlm` y `avlizador avalua --model kenlm` (o `--model flor kenlm`
  para medir los dos en la misma ejecución).
- **Código** (`src/avlizador/traductor_cat_val/model_llengua/`):
  - `kenlm.py`: `normalitza` y `ModelKenLM` (log P natural; prior de
    frecuencia).
  - `sentit.py`: interfaz `candidat(punt) -> str | None`, con
    `ClassificadorCop` (Naive Bayes + lemas). Usa el spaCy del motor, sin
    cargar otro.
  - `CRITERI_KENLM`: margen 3, la catalana por defecto, λ 1,5 / 0,75 y
    desempate 2.
- **Una sola fuente**: `exporta_text.py` reexporta `normalitza` del
  paquete. `sentit_cop.py` y `compara_models.py` (su `KenLM` hereda de
  `ModelKenLM`; `afig_sentit` usa `ClassificadorCop`) importan el núcleo
  de ahí.
- **Ficheros** (fuera de git) en `AVLIZADOR_KENLM_DIR`:
  `valencia_net_dogv_o5.binary`, `valencia_net_dogv_freq.json` y `nb.json`
  (o `sentit_cop/nb.json`). En Abaco basta con
  `AVLIZADOR_KENLM_DIR=~/scrapeo/AVLizador/dades/macocu/kenlm`. Si falta
  `kenlm` o algún fichero, error claro (`FaltaKenLM`), sin volver al motor
  solo en silencio. Extra `[kenlm]` en `pyproject.toml`.
- **Comprobado en local** (Windows, sin `kenlm`):
  - 99 tests en verde, 11 nuevos en `tests/test_kenlm.py`, con un modelo
    falso.
  - El clasificador del paquete da la misma elección que la ejecución
    `1430` en las 33 colisiones de los homógrafos (con el `nb.json` local
    y las frases de las trazas).
- **Reproducido en Abaco (12/11)** con el commit `733a8e2`:
  `avlizador avalua --model kenlm --benchmarks homografs homografs_v2 manual 151 boe_estricte gplsi`.
  Da exactamente las cifras del comparador, con 0 errores:

  | Benchmark | Exactas | BLEU | chrF | TER | WER |
  |---|---|---|---|---|---|
  | Homógrafos v1 + 151 (253) | 227 (89,7 %) | 96,57 | 98,20 | 0,62 | 0,62 |
  | Homógrafos v2 (160) | 110 (68,8 %) | 87,97 | 93,55 | 4,32 | 4,32 |
  | Manual mezcla (458) | 229 (50,0 %) | 90,94 | 96,33 | 5,59 | 5,97 |
  | 151 (154) | 145 (94,2 %) | 99,23 | 99,59 | 0,30 | 0,30 |
  | BOE estricto (2.000) | 1.887 (94,3 %) | 99,03 | 99,65 | 0,30 | 0,57 |
  | gplsi (1.958) | 1.553 (79,3 %) | 93,66 | 97,05 | 2,73 | 2,75 |

  Frente a FLOR (sistema 1.2.0): v1 +8, v2 +15, manual +1, 151 −1, BOE
  igual y gplsi −1. El manual iguala las métricas de la release 1.2.0
  (TER 5,59; WER 5,98 → 5,97).

### 4.15 Clasificador de «cop» sin la AVL (12/11)
Para distribuir KenLM hay que distribuir el `nb.json`, que se entrenó
también con frases de la AVL. El aviso legal de la AVL prohíbe reproducir
sus textos sin autorización (por eso quedó fuera de Hugging Face). El
`nb.json` solo guarda recuentos de lemas, pero es un derivado. El KenLM
(`valencia_net_dogv`) y su tabla de frecuencias no llevan AVL.

Se ha reentrenado con `sentit_cop.py entrena --fonts net dogv` (opción
nueva; desde la decisión del usuario del 12/11, es lo que hace por defecto,
y `--fonts net dogv avl` vuelve a meter la AVL).

- **Reproducción**: con las tres fuentes (`nb_amb_avl.json`) sale idéntico
  byte a byte al `nb.json` en uso. El código movido al paquete entrena
  igual.
- **Lo que aporta la AVL**: 32 frases con colp de 3.123 (1 %) y 626 con
  vegada de 137.765 (0,5 %).
- **Frases apartadas (dev)**: con AVL, colp 223/329 y vegada 4.342/4.410
  (0,831); sin AVL, 221/327 y 4.382/4.449 (0,830). Los rasgos más fuertes
  son los mismos.
- **Colisiones de los benchmarks** (trazas de la `1430`: homógrafos 33,
  manual 19, gplsi 16). Con la regla del sistema («KenLM; si gana por < 2,
  clasificador») el resultado es **idéntico**: homógrafos 33/33, texto real
  25/35, los mismos fallos (todos de gplsi, que usa «colp» = «vez» en su
  referencia).
  - De los 9 casos en la zona de desempate, ninguno cambia de decisión. El
    voto se mueve poco (mediana 0,52 de log-odds) y nunca cambia de signo.
  - Solo cambia de signo un caso fuera de esa zona (BM-AVL-141, −1,57 →
    +0,52), donde KenLM gana por 7,2 y el clasificador no se consulta.
  - El clasificador solo pierde un acierto (25 → 24 en texto real), pero
    no se usa así en el sistema.

**Conclusión**: el clasificador sin AVL da las mismas decisiones en el
sistema. Se puede distribuir `nb_sense_avl.json` en lugar del `nb.json`
actual.

**Decisión del usuario (12/11)**: se quita la AVL. `nb.json` es ahora el
de sin AVL (el anterior, en `nb_amb_avl.json`), en local y en Abaco, y
`sentit_cop.py` entrena sin la AVL por defecto (commit `9b7c2fc`).

### 4.16 KenLM de lemas (12/11, propuesta del supervisor; lanzado en Abaco)
Idea: entrenar un KenLM con el texto pasado a **lemas**, para ver si así
resuelve los casos en que KenLM no se decide. Tras la fusión de `main`
(concordancia de género), lo que queda en los homógrafos (257 decisiones)
son sobre todo palabras **sin traducir** (`calces`, `recuita/es`,
`rentadora/es`, `gandules`, `nou/nous`, `manques`, `panotxes`,
`fartaneres`): KenLM no ve una candidata lo bastante mejor.

**A favor**: las formas raras (sobre todo en plural) suman los datos de su
lema y los contextos también («va pegar» / «pegà» → «pegar»); es barato
(lematizar ~1,4 M frases + entrenar) y se mide igual que lo demás.

**En contra**: con lemas se pierde la concordancia («les nous» / «els
nous», «una vegada» / «un colp»); spaCy es catalán y lematiza mal algunas
formas valencianas («juguen» → «juguar»), aunque igual al entrenar y al
puntuar; la proporción colp/vegada no cambia (eso lo arreglan el prior y
λ); la ventana del n-grama sigue siendo de 4 palabras; «manca» y las
referencias de gplsi no son del modelo.

**Cómo se lematiza** (`src/avlizador/traductor_cat_val/model_llengua/lemes.py`,
`LematitzadorLM`; la MISMA función para el texto de entrenamiento y para las
frases que puntúa el comparador):
- se quedan en su forma las palabras candidatas de los puntos ambiguos (las
  catalanas y sus traducciones: «cop», «colp», «vegades», «nous»,
  «anous»...): son lo que se compara, y así el prior (frecuencia del
  candidato) es el de siempre;
- se quedan en su forma las palabras con género que concuerdan (DET, NUM,
  ADJ, PRON con `Gender`), para no perder «les nous» / «els nous»;
- la puntuación y los números, igual; el resto, al lema de spaCy.
- Prueba local con 5.000 frases valencianas de MaCoCu: cambia el 22 % de
  los tokens; 240 frases/s por proceso; la línea de salida ya es la que lee
  KenLM (`normalitza` no la cambia); en paralelo sale idéntico que en serie.
  Coste al puntuar: ~4 ms por frase candidata (spaCy), frente a 0,065 ms
  del KenLM de formas (FLOR: 833 ms).

**Modelos nuevos en el comparador**: `kenlm_lemes` (solo),
`kenlm_lemes_c1` (+ clasificador de «cop») y `kenlm_mescla_c1` (log P del
KenLM de formas + log P del de lemas, + clasificador). Los modelos `*_c1`
se comparan ahora con el criterio del sistema KenLM (`CRITERI_KENLM`) y no
con `Criteri()`.

**Lanzado todo con `pipeline/03_seleccio_de_model/model_llengua/prova_lemes.sh`**
(en el nodo de login; encola los jobs con dependencias):
1. `avalua_sistema.sh`: la foto del sistema tras la fusión, `avlizador
   avalua --motor --model flor kenlm` en homógrafos v1/v2, manual, 151, BOE
   estricto y gplsi (la concordancia de género de `main` y E0248 cambian el
   motor: las cifras de la 4.14 ya no valen).
2. `lematitza_text.sh`: `valencia_net_dogv.txt` → `valencia_net_dogv_lemes.txt`.
3. `entrena_kenlm.sh`: KenLM de lemas, orden 5, poda de singletons, y su
   tabla de frecuencias.
4. `compara_models.sh`: motor, `kenlm_val_net_dogv_c1` (el sistema),
   `kenlm_lemes`, `kenlm_lemes_c1` y `kenlm_mescla_c1` en los mismos
   benchmarks; rejilla de márgenes 1/2/3/5, λ 0,5-2, λ de colisiones
   0,5/0,75/1, desempate 2; con el detalle de cada decisión.

**Criterio para darlo por bueno**: más aciertos que el sistema actual en
las 257 decisiones de los homógrafos con ≤ 2 errores graves, sin perder en
el manual ni en las regresiones (151, BOE estricto, gplsi).

**Resultados (comparador, job 3035, `compara_models_20261112_1459`)**, con
el criterio del sistema KenLM (`CRITERI_KENLM`); `sentit` = decisiones del
modelo (v1 /57, v2 /132):

| Modelo | sentit v1 | exactas v1 /253 | sentit v2 | exactas v2 /160 | manual /458 | 151 | BOE estr. | gplsi | ms/llamada |
|---|---|---|---|---|---|---|---|---|---|
| motor | 12 | 176 | 52 | 74 | 218 | 142 | 1.800 | 1.533 | — |
| **KenLM + C1 (sistema)** | **49** | **224** | 85 | 106 | **232** | 144 | 1.894 | **1.550** | **0,096** |
| KenLM de lemas | 46 | 220 | **93** | **111** | 231 | 144 | 1.894 | 1.549 | 3,86 |
| KenLM de lemas + C1 | 48 | **224** | 88 | 109 | **232** | 144 | 1.894 | **1.550** | 3,82 |
| Mezcla formas + lemas + C1 | 46 | 219 | 90 | 108 | **232** | 144 | 1.894 | 1.549 | 3,89 |

Con el mejor criterio de cada uno (margen 1, λ 1, elegido sobre los mismos
homógrafos): sistema 52 + 90 = 142 (exactas 225 / 108), lemas + C1 51 + 94
= 145 (225 / 112), lemas solo 49 + 94 = 143, mezcla 51 + 91 = 142.

**Errores graves** (`compara_models_20261112_1459_detall`, 257 decisiones de
v1 + v2; grave = traducida sin hacer falta o candidata equivocada):

| Modelo | Criterio | Aciertos | Graves | Sin traducir | Graves por palabra |
|---|---|---|---|---|---|
| KenLM + C1 (sistema) | sistema | 186 | 10 | 61 | manques 8, manca 2 |
| Lemas + C1 | sistema | **189** | **5** | 63 | manca 3, calces 1, reeixides 1 |
| Lemas solo | fijo | 187 | 19 | 51 | manca 6, reeixida(es) 7, cop(s) 3… |
| Mezcla + C1 | sistema | 183 | 21 | 53 | manques 8, reeixida(es) 5, manca 4… |
| KenLM + C1 / lemas + C1 | margen 1, λ 1 | 189 / 193 | 19 / 15 | 49 / 49 | reeixida(es) 7 en los dos |

Antes de la fusión el sistema daba 191 / 2. Los 8 graves nuevos de
«manques» son todos del cambio de E0248 (sección 4.17).

Decisión a decisión, lemas + C1 frente al sistema (mismo criterio), solo
cambian 14:
- **«manques» (8)**: el modelo de lemas no se queda la «faltes» del motor y
  deja «manques». Gana los 4 verbos/adjetivos (HG077, HG2-038, HG2-040,
  HG2-043) y en los 4 nombres pasa de candidata equivocada a sin traducir.
  Toda la ventaja en graves sale de aquí.
- Gana: HG2-058 «rentadora» → «llavadora», HG2-154 «reeixides» → «exitoses».
- Pierde: HG041 «El sastre cosia calces» → «bragues» (grave), HG2-157 «Les
  reeixides de l'equip» → «exitoses» (grave), HG2-024 «per manca de diners»
  → «falta» (grave), HG2-123 «panotxes» sin traducir.

**Conclusión**: sin contar «manca/manques» (que dependen de E0248 y de
referencias anteriores al cambio), los lemas dan 169 aciertos y 2 graves
frente a 170 y 0 del sistema: **no mejoran**, y cuestan ~40 veces más por
llamada. La mezcla y los criterios de margen 1 añaden graves. No se adopta
el KenLM de lemas; se queda como experimento documentado. Lo que sí queda
claro es que hay que resolver «manques» (sección 4.17).

**Repetición del 13/11** (job de `NOMES_COMPARA=1 prova_lemes.sh`,
`compara_models_20261113_1016`), con las referencias corregidas
(«manca/manques» nombre → «falta/faltes») y la regla del pronombre
personal; mismo criterio que arriba:

| Modelo | Aciertos /257 | Graves | Sin traducir | exactas v1 / v2 / manual / 151 / BOE estr. / gplsi | ms/llamada |
|---|---|---|---|---|---|
| **KenLM + C1 (sistema)** | **194** | **2** | 61 | **228** / 111 / **232** / 144 / 1.894 / **1.550** | **0,10** |
| Lemas + C1 | 191 | 3 | 63 | 225 / 111 / **232** / 144 / 1.894 / **1.550** | 5,0 |
| Lemas solo | 193 | 13 | 51 | 223 / **115** / 231 / 144 / 1.894 / 1.549 | 6,2 |
| Mezcla + C1 | 193 | 11 | 53 | 223 / **115** / **232** / 144 / 1.894 / 1.549 | 4,8 |

- Graves del sistema: HG2-028 «Si en falta algun» (valenciano correcto, la
  referencia pide «manca») y HG2-043 «dos velles faltes» (adjetivo).
- Lemas + C1 frente al sistema cambia 11 decisiones: gana 4 (HG2-024
  «falta», HG2-043, HG2-058 «llavadora», HG2-154 «exitoses») y pierde 7
  (4 «manques» nombre que deja sin traducir, HG2-123 «panotxes», y dos
  graves nuevos: HG041 «calces» → «bragues», HG2-157 «reeixides» →
  «exitoses»).
- Lemas solo y la mezcla ganan 4 exactas en v2, pero con 11-13 graves
  («reeixida» → «exitosa» y «cop» → «vegada» sobre todo).
- Con el mejor criterio de cada uno (margen 1, ajustado sobre los mismos
  homógrafos), todos suben aciertos a costa de graves (sistema 199 / 9).
- Coste: los lemas pasan de ~4 a 5-6 ms por llamada (spaCy en cada frase
  candidata); el sistema, 0,1 ms.

**Conclusión**: se confirma que el KenLM de lemas no mejora al sistema ni
en aciertos ni en graves, y es ~50 veces más lento por llamada.

**Cierre (16/11, decisión del usuario: se queda la estructura actual,
KenLM de formas de orden 5 + clasificador)**. Se probó en **todas** las
palabras ambiguas de los benchmarks (las 20 formas de los homógrafos v1 y
v2, 257 decisiones, y las del manual, el 151, el BOE estricto y gplsi).
Aciertos por palabra (`compara_models_20261113_1016_detall`, criterio del
sistema), lemas solo frente al sistema:

| Gana el KenLM de lemas | Pierde el KenLM de lemas |
|---|---|
| manca 15 / 11, gandules 10 / 8, panotxa 7 / 5, gandula 16 / 15, rentadora 5 / 4 | reeixida 6 / 10, manques 11 / 13, cops 10 / 12, cop 20 / 21, calces 8 / 9 |

No se usa ni siquiera por palabra:
- cada palabra tiene 8-18 casos: elegir el modelo palabra a palabra sería
  ajustarse al benchmark (como las reglas de preposiciones del 14/10);
- donde gana es porque traduce más, y así suma graves (lemas solo: 13
  frente a 1);
- necesita spaCy en cada frase candidata (~50× más lento) y spaCy, que es
  catalán, lematiza mal formas valencianas («juguen» → «juguar»).

**spaCy en el sistema** (`compara_models_20261116_0916_detall`, 257
decisiones): decide 68 y acierta 61. Los 7 fallos son **todos leves** (se
queda la catalana), porque la regla deja la palabra catalana cuando spaCy
da otra categoría que la de la lectura dialectal: «nou» / «nous» fruto
como ADJ o NUM (HG058 «El pastís porta nou i panses», HG066, HG2-013,
HG2-015), «manques» nombre como ADJ (HG2-033, HG2-036) y HG2-081
«recuites». Otros fallos de spaCy ya vistos: la etiqueta de «nou» cambiaba
con el punto final (arreglado el 13/11), «Necessito» inicial como PROPN,
«una mica gandules» como NOUN.

**De dónde salen los 63 «sin traducir» del sistema**: KenLM prefiere la
catalana 41, KenLM gana por menos del margen 3 14, spaCy 7, clasificador
1. Lo que pesa es la falta de datos de la otra forma en el corpus
(recuita, calces, panotxa...), que los lemas no arreglan; la vía con más
recorrido es tener más ejemplos de cada sentido (p. ej., etiquetar los
sentidos con el castellano en un corpus paralelo catalán–castellano;
propuesta del 16/11, sin hacer).

### 4.17 El sistema tras la fusión de `main` (12/11, job 3032, `avalua_sistema_20261112_1437`)
`avlizador avalua --motor --model flor kenlm`, 0 errores en todo:

| Benchmark | Motor | FLOR (antes → ahora) | KenLM + C1 (antes → ahora) |
|---|---|---|---|
| Homógrafos v1 (253) | 176 | 219 → 217 | 227 → **224** |
| Homógrafos v2 (160) | 74 | 95 → 95 | 110 → **106** |
| Manual (458) | 218 | 228 → **231** | 229 → **232** |
| 151 (154) | 142 | 146 → 145 | 145 → 144 |
| BOE estricto (2.000) | 1.800 | 1.887 → **1.894** | 1.887 → **1.894** |
| gplsi (1.958) | 1.533 | 1.554 → 1.551 | 1.553 → 1.550 |

El comparador (job 3035) da exactamente lo mismo para KenLM + C1. FLOR y
KenLM solo difieren en una frase del manual (BM-AVL-191, «les anous»:
acierta KenLM). De dónde vienen las bajadas de los homógrafos:

- **E0248 «manques» → «faltes»** (cambio del léxico del 12/11, `fd697f9`):
  el motor traduce ahora «manques» por «faltes» y KenLM se lo queda.
  - Nombre (carencia): HG075, HG076, HG2-034 dan «faltes», pero el
    benchmark espera «carències» (sus referencias son de antes del cambio).
  - Verbo y adjetivo: HG077 «Tu faltes de paciència», HG2-038 «Si tu faltes
    a la reunió», HG2-040, HG2-043 «dos velles faltes» (manca = sin un
    brazo). El benchmark espera «manques»; FLOR acierta porque deja la
    catalana. «dos velles faltes» es un error grave; «si tu faltes a la
    reunió» es valenciano correcto, pero no es lo que pide la referencia.
- **Concordancia de género nueva** (`concordanca_genere_sn.py`, de `main`):
  HG2-045 «un brollador d'aigua molt freda» → «molt fred» (concuerda el
  adjetivo con «brollador» en vez de con «aigua»: bug, pasa también con
  FLOR y con el motor solo). En cambio HG2-048 sale ahora «d'un brollador»,
  que es lo correcto: la referencia del benchmark («d'una brollador») está
  mal.
- La subida del manual (+3) y del BOE estricto (+7) es de la concordancia
  de género, igual en FLOR y en KenLM.

Pendiente del usuario (no tocar datos ni benchmarks sin permiso): decidir
qué hacer con las referencias de «manques» (HG075, HG076, HG2-034) y con
HG2-048, y si «manques» verbo/adjetivo debe seguir pasando a «faltes»; el
bug de «molt freda», para quien lleve la concordancia de género.

**13/11, con las referencias corregidas y la regla del pronombre**
(`avalua_sistema_20261113_1016`, 0 errores; el comparador da lo mismo para
KenLM + C1):

| Benchmark | Motor (12/11 → 13/11) | FLOR | KenLM + C1 |
|---|---|---|---|
| Homógrafos v1 (253) | 176 → 181 | 217 → 217 | 224 → **228** |
| Homógrafos v2 (160) | 74 → 82 | 95 → 96 | 106 → **111** |
| Manual (458) | 218 | 231 | **232** |
| 151 (154) | 142 | **145** | 144 |
| BOE estricto (2.000) | 1.800 | 1.894 | 1.894 |
| gplsi (1.958) | 1.533 | **1.551** | 1.550 |

Las subidas de los homógrafos son de las referencias de «manca/manques» y
de HG2-048; en KenLM, además, de la regla del pronombre (HG077, HG2-038,
HG2-040). El resto no cambia. KenLM + C1 gana a FLOR en homógrafos (+11 en
v1, +15 en v2) y en el manual (+1), y pierde 1 en el 151 y 1 en gplsi.

### 4.18 KenLM de orden 6, 7 y 8 (16/11, petición del usuario; Abaco)
Pregunta: si KenLM mira más palabras hacia atrás (orden 6, 7 u 8 = 5, 6 o
7 palabras en lugar de 4), ¿decide mejor las palabras ambiguas?

**Cómo se hizo** (`pipeline/03_seleccio_de_model/model_llengua/prova_ordres.sh`,
rama `kenlm-ordres`):
- Mismo texto que el sistema (`valencia_net_dogv.txt`, 44,2 M tokens),
  misma poda (n-gramas de una sola aparición desde los bigramas) y misma
  tabla de frecuencias (`SENSE_FREQ=1`); solo cambia `ORDRE`. ~1 minuto de
  entrenamiento cada uno.
- Comparador: `kenlm_val_net_dogv_c1` (orden 5, el sistema) frente a
  `kenlm_o6_c1`, `kenlm_o7_c1` y `kenlm_o8_c1`, todos con el clasificador
  general (`sentit.json`); solo homógrafos v1, v2 y manual, sin FLOR ni
  motor (decisión del usuario). Criterio del sistema y el mejor de una
  rejilla de 48 (márgenes 1-5, λ 0,5-2, λ de colisiones 0,5-1).
- Ejecuciones: `compara_models_20261116_0916` (5 frente a 6) y `_0922` (5
  frente a 7 y 8).
- **Incidencia**: KenLM se compila por defecto con orden máximo 6
  (`KENLM_MAX_ORDER=6`): `lmplz` escribió los `.arpa` de orden 7 y 8, pero
  `build_binary` los rechazó. Arreglo en Abaco: recompilar con `cmake
  -DKENLM_MAX_ORDER=10 ..` (en `~/kenlm/build`), `build_binary` sobre los
  `.arpa` ya escritos, y el módulo de Python del venv reinstalado con
  `MAX_ORDER=10 pip install --no-cache-dir --force-reinstall --no-deps
  https://github.com/kpu/kenlm/archive/master.zip` (el de pip también
  venía con 6). Un modelo de orden > 6 en el paquete o en Docker exigiría
  lo mismo.

**Resultados**, criterio del sistema (`CRITERI_KENLM`):

| Orden | Aciertos /257 | Graves | Sin traducir | Exactas v1 /253 | Exactas v2 /160 | Manual /458 | chrF manual | TER / WER manual | GD / GDV manual | Fichero | Memoria |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **5 (sistema)** | **193** | **1** | 63 | **227** | **111** | **232** | 96,34 | 5,58 / 5,96 | 0,9936 / 0,9995 | **77 MB** | **74 MB** |
| 6 | 193 | 1 | 63 | 227 | 111 | 232 | 96,34 | 5,58 / 5,96 | 0,9936 / 0,9995 | 91 MB | 88 MB |
| 7 | 193 | 1 | 63 | 227 | 111 | 232 | 96,34 | 5,58 / 5,96 | 0,9936 / 0,9995 | 102 MB | 99 MB |
| 8 | 193 | 1 | 63 | 227 | 111 | 232 | 96,34 | 5,58 / 5,96 | 0,9936 / 0,9995 | 112 MB | 108 MB |

Las 257 decisiones son **idénticas** en los cuatro órdenes. Tiempo igual
(0,099 ms por frase candidata).

Con el mejor criterio de cada uno (margen 1, λ 1, λ de colisiones 0,75;
ajustado sobre los mismos homógrafos): orden 5 198 aciertos / 8 graves /
51 sin traducir (exactas v1 228, v2 115); orden 6, 7 y 8 199 / 8 / 50
(228, 116). La única diferencia es HG2-034 «Les manques de l'escola són
evidents» → «faltes» (acierto), que el orden 5 deja sin traducir.

**Por qué no cambia nada** (puntuaciones en bruto del `_detall.json`):
- La log P de la frase cambia en 117 de las 257 decisiones, pero cambia
  casi igual para las dos candidatas: la diferencia entre ellas, que es lo
  que decide, varía 0 de mediana y ≤ 0,06 en el 90 % de los casos (máximo
  1,06; > 0,5 solo en 4-6 decisiones). Los márgenes del sistema son 2 y 3.
- Con la poda, los n-gramas largos casi desaparecen (orden 8: 1,3 M
  8-gramas frente a 2,5 M 5-gramas) y los que quedan casi nunca contienen
  la palabra ambigua con su contexto: KenLM retrocede al orden 4-5 igual
  que antes.
- Lo que decide estas palabras es la frecuencia (corregida con λ) y el
  clasificador, no la distancia que ve KenLM.

**Conclusión: descartado.** Se queda el orden 5: mismas decisiones, menos
memoria y no exige recompilar `kenlm`. La mejora de 1 frase con el mejor
criterio es de margen 1, que en el sistema añade graves (8 frente a 1).

### 4.19 Más texto: DOGV nuevo, AVL y UA, en KenLM y en el clasificador (16-17/11)

**Petición del usuario** (versión 2.0.0): ver si KenLM y el clasificador de
sentido mejoran, o al menos no empeoran, con más texto valenciano: el DOGV
nuevo entero, la AVL y las noticias de la UA. Se decide con los resultados.

**Textos** (generados en local el 16/11 y subidos a Abaco):

| Texto | Script | Frases | Palabras |
|---|---|---|---|
| MaCoCu net (`valencia_net.txt`) | `exporta_text.py` (ya estaba) | 1.211.204 | — |
| DOGV del sistema (`dogv_apunt/dogv_net.txt`) | `prepara_dogv.py` | 163.558 | 9,5 M |
| **DOGV nuevo** (`dogv_apunt/nova/dogv_net.txt`) | `prepara_dogv.py --entrada dades/dogv_apunt/nova/dogv_documents.tsv` | 233.946 | 13,7 M |
| **AVL** (`termes/avl_net.txt`) | `termes_ambigus.py --sense-net` | 88.243 | 1,5 M |
| **UA** (`termes/ua_net.txt`, frases de GD ≥ 0,8) | `termes_ambigus.py --sense-net` | 31.212 de 204.781 | — |

El DOGV nuevo incluye el del sistema (15.702 documentos: los 10.289 de antes
y 5.413 más); se quedan los 10.843 documentos con GD ≥ 0,8.

**Nada de la evaluación en el texto**: `prepara_dogv.py` quita del DOGV las
frases de los benchmarks; `termes_ambigus.py` quita de la AVL los 233
documentos del 151 y del manual y las frases parecidas (Jaccard ≥ 0,6) a una
de las 7.360 del manual, del 151 o de los homógrafos. Importa porque el
manual AVL y el 151 salen de textos de la AVL.

**Arreglo de paso**: `prepara_dogv.py` (y el filtro valenciano de MaCoCu)
fallaban desde el 13/11: el sustituto de spaCy de `filtra_valencia.py`
(`_DocsPrecalculats`) no tenía `pipe_names`, que `pos_tagger` usa desde
entonces. Arreglado (delega en el spaCy de verdad).

**Variantes** (`prova_corpus.sh`; mismo orden 5 y poda que el sistema, cada
KenLM con su tabla de frecuencias):

| KenLM | Texto | Clave del comparador |
|---|---|---|
| `valencia_net_dogv` (el sistema) | MaCoCu net + DOGV del sistema | `kenlm_val_net_dogv_c1` |
| `valencia_net_dogv2` | MaCoCu net + DOGV nuevo | `kenlm_dogv2_c1` |
| `valencia_net_dogv2_avl` | ídem + AVL | `kenlm_dogv2_avl_c1` |
| `valencia_net_dogv2_avl_ua` | ídem + UA | `kenlm_dogv2_avl_ua_c1` |

| Clasificador (`sentit_general.py entrena`) | Fuentes |
|---|---|
| `sentit` (el sistema) | MaCoCu net + DOGV del sistema |
| `sentit_dogv2` | MaCoCu net + DOGV nuevo (`--fonts net dogv2`) |
| `sentit_dogv2_avl` | ídem + AVL (`--fonts net dogv2 avl`) |

Recuento de las fuentes nuevas solas (`recompte --fonts dogv2 avl`): «cop»
colp 25 / vegada 4.738 y «manca» faltes 1.569 / manques 101 pasan el mínimo;
el resto de grupos sigue con pocos datos de un sentido (anous 12, colps 14,
brollador 5). El grueso de los ejemplos sigue viniendo de MaCoCu.

**Comparación**: un `compara_models.sh` por clasificador, cada uno con los
cuatro KenLM (3 × 4), en homógrafos v1 y v2, manual y 151, con la rejilla de
criterios de la 4.18 (márgenes 1-5, λ 0,5-2, λ de colisión 0,5-1, desempate
2). La salida lleva el nombre del clasificador
(`compara_models_<fecha>_<clasificador>`, opción nueva `--etiqueta`).

**Resultados** (Abaco, jobs 3129-3142; `resultats/compara_models_20261116_1608_sentit*`,
`_1608_sentit_dogv2*` y `_1619_sentit_dogv2_avl*`). Criterio C1 (margen 3, la
catalana por defecto, λ 1,5 / 0,75, desempate < 2); aciertos / errores graves
en las 257 decisiones de homógrafos v1 + v2:

| KenLM \ clasificador | `sentit` (sistema) | `sentit_dogv2` | `sentit_dogv2_avl` |
|---|---|---|---|
| `valencia_net_dogv` (sistema) | 193 / 1 | 193 / 1 (+1 candidato erróneo) | 194 / 1 |
| `valencia_net_dogv2` | 193 / 1 | 193 / 1 | **194 / 1** |
| `valencia_net_dogv2_avl` | 192 / 2 | 192 / 2 | 193 / 2 |
| `valencia_net_dogv2_avl_ua` | 192 / 2 | 192 / 2 | 193 / 2 |

Exactas con `valencia_net_dogv2` + `sentit_dogv2_avl`: v1 227/253, v2 112/160,
manual 232/458, 151 144/154 (sistema: 227, 111, 232, 144). Manual: TER 5,58,
WER 5,96, GD 0,9936, GDV 0,9995, iguales en las 12 combinaciones.

Decisión a decisión:
- **KenLM**: `valencia_net_dogv2` no cambia ningún resultado (en HG2-009
  «nou» acierta igual, pero por la catalana por defecto en vez del modelo):
  con el DOGV del sistema ya estaba saturado. Con la AVL, un error grave
  nuevo: HG2-157 «Les reeixides de l'equip omplen el palmarès» → «exitoses».
  La UA no cambia nada más.
- **Clasificador** (actúa en 51 decisiones: cop, cops, deu; acierto propio
  sistema 47/51, `sentit_dogv2` 47/51, `sentit_dogv2_avl` 48/51):
  `sentit_dogv2` gana HG2-047 («Aquesta deu no s'asseca mai» → «brollador»)
  y pierde HG009 («un últim cop al banc» → «vegada»); `sentit_dogv2_avl`
  solo gana HG2-047.
- Con el mejor criterio de cada modelo (marge 1) todos llegan a 198-200
  aciertos, pero con 8-16 errores graves: se mantiene C1.

**Decisión del usuario (17/11/2026)**: **KenLM `valencia_net_dogv2` (MaCoCu net
+ el DOGV entero, sin la AVL) + clasificador `sentit_dogv2_avl` (MaCoCu net +
DOGV entero + AVL)**: la mejor combinación (194 / 1) y no pierde ninguna
decisión frente al sistema. Ojo para la publicación: el clasificador sale en
parte de textos de la AVL (vore el punto de la licencia en CLAUDE.md / la
ficha de Hugging Face).

### 4.20 Concordancia de los candidatos: el modelo solo elige la palabra (19/11, rama `concordancia-genere`)

Origen: dos fallos de la 2.0.0 que encontró un compañero en FLORES+ devtest.

- **461**: «L'aïllament és absolut un cop arribes» → «és **absoluta** una
  vegada». No era la regla de concordancia (spaCy hace «un cop» locución
  `fixed` y no cuelga «absolut» de «cop»), sino `concordanca="variants"`, el
  modo por defecto: proponía a KenLM las formas del otro género de las dos
  palabras anteriores (DET/ADJ/NUM/PRON) sin mirar si dependen del nombre, y
  KenLM prefería «absoluta una vegada».
- **782**: «La xocolata desfeta» → «El xocolate **desfeta**». spaCy analiza al
  revés («xocolata» `amod` de «desfeta») y `_adjectiu_enganxat` descartaba
  todos los participios (por BM-AVL-074, «El Decret, un cop aprovat»).

Cambios (decisión del usuario: que KenLM no haga concordancia y la haga la
regla):

1. `CONCORDANCA_PER_DEFECTE = "motor"`: la frase de cada candidato la hace
   `aplica_candidat` con la regla de concordancia (spaCy + fichero
   morfológico, desde el 11/11) y KenLM solo elige la palabra. Además puntúa
   menos frases.
2. `_adjectiu_enganxat` ya no descarta los participios. BM-AVL-074 sigue bien:
   «aprovat» cuelga de «Decret» y la comprobación del núcleo lo deja fuera.
3. Huecos de la regla que tapaban las variantes: determinante fuera de la
   tabla → fichero morfológico, solo si no es artículo y spaCy le da el género
   de antes («Diverses vegades»; sin esa condición, «a les nou» → «a lesa
   anou», porque «les» tiene lectura de adjetivo); palabra con el artículo
   apostrofado dentro del token («L'última vegada», que fallaba también con
   las variantes); «algun/alguns» en la tabla de determinantes (no está en el
   fichero morfológico).

Medido:

- Motor solo (local): 0 frases distintas en manual (218), 151 (142),
  homógrafos v1 (181) y v2 (82), BOE estricto (1.800) y el benchmark de género
  (110/119).
- KenLM en Abaco (`avalua_sistema_20261119_0843`, con los cambios 1 y 2 y sin
  «algun»): v1 **226** (2.0.0: 227), v2 112, manual 232 y 151 144. La única
  frase distinta era HG030 «Alguns cops arriba tard» → «Alguns colps»: el
  candidato de «vegades» salía «Alguns vegades» y KenLM lo veía improbable. Con
  «algun» en la tabla, las frases candidatas de HG030 son idénticas a las de la
  2.0.0 en los dos modos. **Confirmado en Abaco** (`avalua_sistema_20261119_0850`,
  commit `d53ebed`): **227 / 112 / 232 / 144**, con BLEU, chrF, TER y WER
  idénticos a los de la 2.0.0 en los cuatro benchmarks.

Queda: si spaCy analiza mal la frase, alguna palabra se queda en el género de
antes («La xocolata desfeta és molt bona» → «El xocolate desfet és molt
bona»). Tests nuevos en `tests/test_kenlm.py` (461 y 782).

### 4.21 Errores de la 2.0.0 en AINA ca-en (19/11, rama `errors-aina`)

Origen: el ETL de `traductor-es-va-en` compara la 2.0.0 + KenLM con la 1.2.0
+ FLOR traduciendo el catalán de AINA ca-en (15 M de pares) y FLORES+
devtest. 21 casos en 5 grupos. Con `main` (`bf5c0ca`, ya con la 4.20):

| # | Error | Frases AINA 1.2.0 → 2.0.0 | En `main` | Causa |
|---|---|---|---|---|
| 1 | «deu» (número o verbo) → «brollador» | 812 → 4.000 | sigue | `resoluble`: spaCy da NUM y el motor deja «deu», pero el modelo puede cambiarlo igualmente (la capa de spaCy solo se aplicaba a los irresolubles) y con λ 1,5 la palabra rara gana. |
| 2 | «nou» (nuevo, «de nou») → «anou» | 277 → 2.257 | sigue | spaCy da NOUN en los 6 casos («el nou de Bowie», «arriba el nou», «de nou», «observador no lineal nou») → decide KenLM, y λ 1,5 favorece «anou». |
| 3 | «al seu habitatge» → «al seua vivenda» | 29 → 609 | sigue | spaCy parte «al» en «a» + «l»; el «l» no empieza en ningún token del motor y la concordancia se lo salta. Con mayúscula («Al seu») spaCy ni lo parte. |
| 4 | 461 «absoluta», 782 «desfeta» | — | **arreglados** (4.20) | — |
| 4 | «estes petites despeses» → «estos xicotetes gastos» | — | sigue | El léxico ya ha traducido «petites» → «xicotetes» y la concordancia no toca tokens traducidos. |
| 5 | «estel» → «milotxa» | ya estaba | **arreglado** | El léxico del PR #33 ya no tiene «estel». |

Además, «a la seva despesa» → «a el seu gasto» (falta contraer; el mismo
fallo en el sentido masculino).

Cambios:

1. **Concordancia** (`concordanca_genere_sn.py`), sin spaCy: desde el nombre
   se va hacia la izquierda por las palabras ya traducidas que llevan el
   género nuevo («seua», «primera») y se corrige el artículo o la contracción
   de delante (`corregeix_determinant_abans`): «a la seua vivenda», «de la
   primera menció», «A LA SEUA VIVENDA». Un artículo que pasa a «el»/«els»
   se contrae con la preposición (`contrau_article`, sacada de
   `corregeix_determinant_abans`): «al seu gasto», «pel primer gasto». Un
   adjetivo que ya ha traducido el léxico y conserva el género original
   también concuerda («estos xicotets gastos»).
2. **spaCy también en los resolubles** (`Criteri.spacy_resolubles`, por
   defecto `True`): «per deu estats» (NUM) se queda «deu» sin consultar el
   modelo. Dos matices para no perder frases de los benchmarks: un NUM detrás
   de cualquier determinante femenino singular pasa al modelo («la deu del
   bosc», que spaCy da NUM: HG079, HG080, HG2-046), y un participio (VERB +
   `VerbForm=Part`) cuenta como adjetivo («van ser reeixides», HG2-154).
   Sin esos matices se perdían 4 frases.
3. **Género del nombre** (`punts.decisio_spacy`, `generes_de_nom`): si el
   determinante de delante tiene un género que no tiene ninguna lectura de
   nombre de la forma catalana según el fichero morfológico («nou» solo es
   nombre en femenino), la lectura de nombre es imposible: «el nou de
   Bowie», «arriba el nou», «amb el nou, prim i potent» se quedan «nou».
   «deu» es nombre en los dos géneros: no se aplica. Solo con el
   determinante: con el género que spaCy da a la propia palabra se perdían 7
   frases («panotxes torrades», «un sac de nous»).

Medido (local, sin KenLM; las reglas 2 y 3 se miden contra la referencia):

- Motor solo: 0 frases distintas en homógrafos v1 (181), v2 (81), manual
  (218) y 151 (142). Ninguno tiene estas construcciones.
- Reglas 2 y 3 en los puntos de v1, v2, manual y 151: 0 traducciones buenas
  bloqueadas; deciden la catalana en 22 (regla 2) y 10 (regla 3) puntos en
  los que la referencia deja la catalana.
- Casos del informe con un modelo falso que siempre prefiere la traducción:
  19 de 21 bien. Quedan 8 («programes de nou») y 9 («observador no lineal
  nou»): spaCy NOUN, sin determinante → decide KenLM.
- 119 tests en verde. El doctest de «L'estel va quedar enganxat» ya fallaba
  en `main` (léxico del PR #33): cambiado por «La galleda va quedar
  enganxada».

4. **λ propio para los irresolubles** (`Criteri.lam_irresoluble`;
   `CRITERI_KENLM`: 1,25, el resto igual: λ 1,5 para los resolubles, 0,75
   para las colisiones). La causa de fondo de los casos 8 y 9 es el λ 1,5:
   KenLM solo prefiere «nou» (por 3,5 y 6 puntos), pero la corrección por
   frecuencia da la vuelta al resultado («anou» gana por 5,8 y 3,3; margen 3).

**Medido con el KenLM real de la 2.0.0** (19/11). Docker no arrancaba en
el PC y `kenlm` no se instala en Windows, así que se hizo en tres pasos: el
sistema en local recoge las frases que KenLM tiene que puntuar (1.042 en los
4 benchmarks, 52 en los casos de AINA; las mismas con `main` y con la rama),
se puntúan en Abaco con `kenlm.Model.score` sobre el modelo de la 2.0.0, y
el sistema completo se ejecuta en local con esas puntuaciones (los ficheros
de `docker/kenlm/` son idénticos a los de Hugging Face, por md5).

Exactas, homógrafos v1 / v2 / manual / 151:

| Sistema | v1 | v2 | manual | 151 | Frases distintas de `main` |
|---|---|---|---|---|---|
| `main` (`bf5c0ca`) | 227 | 111 | 232 | 144 | — |
| Rama, λ irresolubles 1,5 (cambios 1-3) | 227 | 111 | 232 | 144 | 0 |
| Rama, λ irresolubles 1,25 (**elegido**) | 227 | **112** | 232 | 144 | +1 (HG2-113 «panolla») |
| Rama, λ irresolubles 1,0 | 227 | 115 | 231 | 144 | +4 (HG2-022, 024 «falta»; HG2-113, 115 «panolla») / −1 (BM-AVL-191 «les anous») |
| Rama, λ irresolubles 0,75 | 227 | 116 | 231 | 144 | +6 / −2 (además HG059 «una nou») |

`main` reproduce aquí las 227 / 232 / 144 de Abaco. En v2 salen 111, frente a
110 en la ejecución de Abaco de `bf5c0ca` (`avalua_sistema_20261119_0944`) y
112 en la de las 08:43. Frente a esta última, la única frase distinta es
HG2-086, «Els fesols recuits», cuya referencia dice «recuites» (está mal).
La comparación entre `main` y la rama es exacta porque se hace con las
mismas puntuaciones. λ 1,0 se descarta porque pierde BM-AVL-191, y se elige
1,25 porque mejora sin empeorar nada. En la simulación del detalle del 16/11
(257 decisiones), 1,25 da 195 aciertos y 1 grave, frente a 194 y 1 con 1,5.

**Casos de AINA con el KenLM real** (23 frases del informe). `main`
reproduce todos los errores reportados: «per brollador estats» (los casos
1-3 los decidía el clasificador de sentido), «comprar l'anou de Bowie»,
«amb l'anou, prima i potent», «al seua vivenda», «del primera menció»,
«estos xicotetes gastos». Con la rama, bien 1-7, 9-21 (el 9 por el λ
1,25). Quedan:

- 8, «programes de nou» → «d'anou»: con λ 1,25, «anou» sigue ganando por
  4,2. Haría falta λ ≤ 1,0, que pierde BM-AVL-191.
- 22 «manca» y 23 «rentadora» (grupo 6, los compañeros esperaban «falta» y
  «llavadora»): KenLM prefiere la catalana (en «rentadora» por 1,2 sin
  corrección; en «manca», con la corrección, por 2,3) y lejos del margen
  3 → se queda la catalana. Es el criterio de la catalana por defecto, no
  un fallo.

Pendiente: medir el λ en texto catalán real (tasa de traducción de cada
homógrafo en una muestra de AINA o de `catala_pur`), que es donde se ve el
problema; los benchmarks están equilibrados al 50 % por sentido.

### 4.22 KenLM de lemas con el texto de la 2.0.0 (20/11, petición del usuario; Abaco)

Se repite la prueba de la 4.16 con el texto del sistema actual. El 12-13/11
se hizo con `valencia_net_dogv` y el clasificador viejo; desde la 2.0.0 el
sistema es `valencia_net_dogv2` (MaCoCu net + el DOGV nuevo entero) +
`sentit_dogv2_avl`, con la concordancia de los candidatos (4.20) y λ 1,25
en los irresolubles (4.21).

- **Mismo lematizador** que el 12/11 (`LematitzadorLM`; decisión del
  usuario): todo a lema salvo las palabras candidatas y las que concuerdan
  en género (DET, ADJ, NUM, PRON con `Gender`).
- `valencia_net_dogv2.txt` → `valencia_net_dogv2_lemes.txt` → KenLM de
  orden 5 con la misma poda y su tabla de frecuencias.
- Claves nuevas del comparador: `kenlm_lemes_dogv2` (solo),
  `kenlm_lemes_dogv2_c1` (+ clasificador) y `kenlm_mescla_dogv2_c1` (formas
  de la 2.0.0 + lemas + clasificador), frente a `kenlm_dogv2_c1` (el
  sistema 2.0.0), con `--model-sentit sentit_dogv2_avl.json`; homógrafos v1
  y v2, manual y 151; rejilla de márgenes y λ y detalle de cada decisión.
- Lanzador: `pipeline/03_seleccio_de_model/model_llengua/prova_lemes_dogv2.sh`
  (rama `kenlm-lemes-2.0`).
- Criterio para darlo por bueno, el de la 4.16: más aciertos que el sistema
  en las 257 decisiones con no más errores graves, sin perder en el manual
  ni en el 151.

**Ejecución** (jobs 3286-3288, `compara_models_20261120_1012_lemes_dogv2`):
lematizar 1.445.150 frases, 655 s con 8 CPU (cambia el 21 % de los
tokens); KenLM 72 s; comparación ~1 h. El sistema sale igual que la
evaluación de la 2.0.0 (exactas 227 / 112 / 232 / 144).

**Fallo del comparador arreglado de paso**: si una palabra ya no se detecta
como ambigua, `detall` contaba la decisión como «traducida sin hacer
falta» aunque la palabra se quedara igual. Pasa con «recuita / recuites»:
desde el commit del compañero del 18/11 (`8616c0b`) el léxico ya no las
tiene como homógrafo (solo «recuit / recuits» → «brull / brulls»), así que
el motor las deja siempre. Ahora la tria de un punto no detectado es la
forma que queda en la traducción (`forma_que_queda`). Las cifras de abajo
están recalculadas así a partir del JSON del detalle.

257 decisiones de los homógrafos v1 + v2 (grave = traducida sin hacer
falta o candidata equivocada):

| Modelo | Criterio | Aciertos | Graves | Sin traducir | Exactas v1 / v2 / manual / 151 | ms/llamada |
|---|---|---|---|---|---|---|
| **Sistema 2.0.0** (`kenlm_dogv2_c1`) | sistema | **194** | **2** | 61 | **227** / 112 / **232** / 144 | **0,10** |
| Lemas solo | fijo | 200 | 7 | 50 | 225 / **120** / 231 / 144 | 5,0 |
| Lemas + clasificador | sistema | 196 | 3 | 58 | **227** / 114 / **232** / 144 | 4,9 |
| Mezcla formas + lemas + clasificador | sistema | 198 | 5 | 54 | 225 / 118 / **232** / 144 | 5,2 |

- Graves del sistema: HG2-028 «Si en falta algun» (ya conocido: valenciano
  correcto, la referencia pide «manca») y HG2-086, que en realidad está
  bien: «Les mongetes recuites» → «Els fesols recuits» (la concordancia
  cambia el adjetivo con el nombre; la referencia espera «recuites»).
- Lemas + clasificador, frente al sistema: gana 4 (HG053 «hamaques»,
  HG2-024 «falta», HG2-058 «llavadora», HG2-154 «exitoses») y pierde 2:
  HG2-123 «panotxes» (sin traducir) y un grave nuevo, HG041 «El sastre
  cosia calces» → «bragues», el mismo que el 12/11.
- Lemas solo y la mezcla traducen más (gandula / gandules, manca, panotxa)
  pero vuelven los graves de «cop / cops» → «vegada / vegades» (HG009,
  HG022, HG026), más «calces» y HG055 «gandules» → «hamaques».
- Con el mejor criterio de cada uno (margen 1, λ 1, elegido sobre estos
  mismos homógrafos): sistema 205 / 2, lemas + clasificador 206 / 5, lemas
  solo 203 / 7, mezcla 207 / 6.

**Lectura**: con el texto de la 2.0.0 pasa lo mismo que el 12-13/11. Los
lemas no mejoran al sistema sin añadir errores graves; lo que ganan es
traducir más, y cuestan ~50 veces más por llamada (spaCy en cada frase
candidata). Visto de paso: el sistema con margen 1 y λ 1 pasa de 194 a 205
aciertos con los mismos 2 graves; está elegido sobre el mismo benchmark y
habría que comprobarlo en texto real antes de cambiar nada.

Para el compañero: con el cambio del 18/11, «recuita» nombre (requesón)
ya no se traduce nunca a «brulla» (12 decisiones sin traducir en los
homógrafos).

**Variante «todo a lema»** (20/11, petición del usuario;
`LematitzadorLM(tot=True)`, `TOT=1 prova_lemes_dogv2.sh`; jobs 3290-3291 y
3293, `compara_models_20261120_1151_lemes_tot_dogv2`). Todo pasa a lema,
también las candidatas y las palabras que concuerdan («Les anous són
bones.» → «el anou ser bo .»); solo quedan la puntuación y los números. El
prior sale de la tabla de formas de la 2.0.0, porque en el texto de lemas
ya no están los plurales candidatos. Lematizar: 655 s con 8 CPU; KenLM 71 s.
El comparador ya lleva el arreglo de los puntos no detectados.

| Modelo | Criterio | Aciertos | Graves | Sin traducir | Exactas v1 / v2 / manual / 151 |
|---|---|---|---|---|---|
| **Sistema 2.0.0** | sistema | 194 | **2** | 61 | **227** / 112 / **232** / 144 |
| Todo a lema, solo | fijo | 195 | 7 | 55 | 222 / 118 / 231 / 144 |
| Todo a lema + clasificador | sistema | 187 | 4 | 66 | 223 / 109 / **232** / 144 |
| Mezcla formas + todo a lema + clasificador | sistema | **199** | 4 | 54 | 226 / **118** / **232** / 144 |
| *(4.22) Mezcla formas + lemas parciales + clasif.* | sistema | 198 | 5 | 54 | 225 / 118 / 232 / 144 |

Los 2 graves del sistema (HG2-028 y HG2-086, sección anterior) están en
todos; lo nuevo de cada uno:

- **Todo a lema, solo**: gana 14 decisiones (gandula / gandules, manca,
  rentadora, reeixida) y pierde 13: «cop / cops» → «vegada / vegades»
  (HG009, HG022), HG041 «calces» → «bragues», HG055 «gandules» →
  «hamaques», HG2-160 «reeixides» → «exitoses» (5 graves nuevos) y 7
  «nou» fruto sin traducir: con «una nou» → «un anou» desaparece la pista
  del género.
- **Todo a lema + clasificador**: el peor; gana 7 y pierde 14 (reeixida,
  panotxa, gandula sin traducir; graves nuevos HG041 «calces» y HG2-009
  «nou» → «anou»).
- **Mezcla formas + todo a lema + clasificador**: el que más acierta de
  todas las variantes de lemas: gana 7 (HG053 y HG2-106 «hamaques», HG2-022
  y HG2-024 «falta», HG2-058 y HG2-059 «llavadora», HG2-154 «exitoses») y
  pierde 2, los dos graves: HG009 «Els lladres van preparar un últim cop al
  banc» → «vegada» y HG041 «El sastre cosia calces» → «bragues». Exactas: v2
  +6, v1 −1.

**Lectura**: lematizarlo todo no arregla lo que no arreglaban los lemas
parciales. Solo, pierde el género («nou» / «anou») y vuelve el error de
«cop» → «vegada». La mezcla con el KenLM de formas recupera eso y saca +5
aciertos, pero con 2 graves nuevos; con el criterio de la 4.16 (más
aciertos sin más graves) no se adopta. Cuesta lo mismo que los lemas
parciales (~5 ms por llamada, spaCy en cada frase candidata).

**Búsqueda de la mejor configuración** (20/11, petición del usuario; job 3294,
`compara_models_20261120_1307_graella_lemes_tot{,_graella.json,_tria.md}`).
`compara_models.py --graella-completa` guarda ahora, para cada criterio,
todas las métricas de cada benchmark (exactas, BLEU, chrF, TER, WER), los
aciertos / graves / sin traducir de los homógrafos y el GD / GDV / GDC del
manual; `tria_criteris.py` elige. Rejilla: margen 0,5-5 (8 valores), λ 0,5-2
(4), λ de colisiones 0,5-1,5 (4), λ de irresolubles 0,75-2 (5), desempate
1/2/3 (solo con clasificador): 1.920 criterios por modelo con clasificador y
641 sin él. Tardó unos 5 minutos (las métricas de cada traducción se
calculan una vez).

| Modelo | Criterio actual | Mejor sin más graves (≤ 2) | Mejor absoluto |
|---|---|---|---|
| **Sistema 2.0.0** | 194 / 2 | **205 / 2** (margen 1, λ 1, λ col. 0,75, λ irr. 1, desempate 2) | 210 / 4 (margen 0,5) |
| Todo a lema | 195 / 7 | — (como mínimo 3 graves: 185 / 3) | 204 / 8 |
| Todo a lema + clasificador | 187 / 4 | 187 / 2 (margen 4) | 206 / 7 |
| Mezcla formas + todo a lema + clasificador | 199 / 4 | 199 / 2 (margen 5) | 212 / 10 |

Aciertos / graves en las 257 decisiones. Exactas del sistema con «mejor sin
más graves»: v1 230 (actual 227), v2 120 (112), manual 232 (232), 151 144
(144); GD / GDV del manual 1,0000 en todas las filas y GDC 0,922. Tabla con
todas las métricas en el `_tria.md`.

**Validación cruzada** (se elige con un banco de homógrafos, sin pasar de
los graves del sistema en ese banco, y se mide en el otro; entre paréntesis
el sistema actual):

| Modelo | Elegido en → medido en | Aciertos | Graves |
|---|---|---|---|
| Sistema 2.0.0 | v1 → v2 | 119 (113) | 3 (2) |
| Sistema 2.0.0 | v2 → v1 | 81 (81) | 3 (0) |
| Mezcla formas + todo a lema + clasif. | v1 → v2 | 118 (113) | 2 (2) |
| Mezcla formas + todo a lema + clasif. | v2 → v1 | 82 (81) | 3 (0) |
| Todo a lema + clasificador | v1 → v2 | 105 (113) | 3 (2) |
| Todo a lema + clasificador | v2 → v1 | 77 (81) | 2 (0) |
| Todo a lema | v2 → v1 | 78 (81) | 3 (0) |

**Lectura**:

- Con lemas no hay ninguna configuración mejor que el sistema con los
  mismos graves: la mezcla llega a 199 / 2 y el sistema ajustado a 205 / 2.
  Todo a lema, solo, no baja de 3 graves.
- El sistema ajustado (margen 1, λ 1, λ irresolubles 1) gana 11 aciertos
  sobre los mismos homógrafos, pero en la validación cruzada esa ganancia
  se queda en +6 aciertos en v2 y 0 en v1, y en las dos direcciones sube
  a 3 graves. Parte de la mejora es ajuste al banco. Antes de cambiar el
  criterio habría que mirar esos graves y medirlo en texto real (AINA).

**Qué frases son** (20/11, simulado en local con las puntuaciones en bruto
del detalle `compara_models_20261120_1012_lemes_dogv2_detall.json` y la
función `tria` del paquete; reproduce exactamente las cifras de Abaco:
194/2, 205/2, 119/3 y 81/3). Lo que cuenta es el margen; las λ casi no
cambian nada si se dejan como están:

| Criterio (el resto, el actual) | Aciertos / graves | v1 | v2 |
|---|---|---|---|
| Actual (margen 3) | 194 / 2 | 81 / 0 | 113 / 2 |
| Margen 2 | 199 / 2 | 81 / 0 | 118 / 2 |
| Margen 1 | 204 / 2 | 84 / 0 | 120 / 2 |
| Margen 1 + λ 1 + λ irr. 1 («afinado») | 205 / 2 | 84 / 0 | 121 / 2 |
| Margen 0,5 + λ 1 + λ irr. 1 | 210 / 4 | 86 / 1 | 124 / 3 |

- **Margen 1 / afinado**: 11 decisiones pasan de «sin traducir» a acierto y
  ninguna empeora: HG035 y HG037 «calces» → «bragues», HG043 «gandula» →
  «hamaca», HG2-022 y HG2-024 «manca» → «falta», HG2-059 «rentadora» →
  «llavadora», HG2-106 «gandules» → «hamaques», HG2-115 y HG2-121 «panotxa(es)»
  → «panolla(es)», HG2-148 y HG2-154 «reeixida(es)» → «exitosa(es)». En todas
  la traducción ganaba por 0,4-2,9 puntos, por debajo del margen 3.
- **Los graves de la validación cruzada no vienen del margen, sino de las
  λ** que eligió cada mitad:
  - elegido con v1 (λ 0,5 para los resolubles): HG2-160 «Ha acumulat moltes
    reeixides al llarg de la carrera» → «exitoses» (nombre convertido en
    adjetivo), y pierde HG2-047 «Aquesta deu no s'asseca mai» (el modelo
    gana al clasificador por más del desempate). Gana HG070, HG071 y HG075
    («manca / manques» → «falta / faltes»).
  - elegido con v2 (λ de colisiones 0,5): HG009 «Els lladres van preparar un
    últim cop al banc», HG022 «molts cops a la cara» y HG025 «La fruita
    tenia cops» → «vegada / vegades»: con λ bajo vuelve el sesgo hacia la
    palabra frecuente.
- **Margen 0,5**: graves nuevos HG041 «El sastre cosia calces» → «bragues» y
  HG2-095.

**Lectura**: bajar el margen de 3 a 1 (sin tocar las λ, o con λ 1) gana 10-11
aciertos en los dos bancos y no añade ningún grave; las λ de colisiones y de
resolubles no se deben bajar. Pero los bancos tienen la mitad de casos de
cada sentido, y en texto real el sentido catalán («calces» de época, «manca»
verbo, «reeixida» éxito) es mucho más frecuente: con margen 1 se traducirá
más a menudo, y ahí pueden salir los graves. Falta medirlo en AINA.

## 5. Cautelas
- Los márgenes y los λ se ajustan **sobre los mismos homógrafos** con los que
  se evalúa: las cifras son optimistas. Hay que confirmarlas en el 151, el
  BOE estricto y frases nuevas.
- Los resultados de la sección 4.5 son **simulados** a partir de las
  puntuaciones guardadas. Falta la ejecución real con el prior nuevo.
- El benchmark `homografs` (v1) ya contiene el 151.

---

## 6. Herramientas y cómo reproducir

| Herramienta | Qué hace |
|---|---|
| `compara_models.py` | Puntúa cada benchmark una vez con cada modelo y prueba una rejilla de criterios. Opciones: `--detall` (cada decisión, con puntuaciones en bruto), `--traces` (log P por token), `--lams-colisio`, `--prior-kenlm freq\|unigrama`, `--benchmarks ... 151 boe_estricte`. Job: `compara_models.sh`. |
| `simula_marges.py` | Simula en local cualquier margen, λ de colisiones y λ de homógrafos sobre un `_detall.json`. Comprueba antes que reproduce el sistema decisión a decisión. `--hibrid flor` simula el híbrido. |
| `visor_compara_models.html` | Abre los `_traces_<modelo>.json`: probabilidad por token, zona distinta, pérdida en la palabra frente al resto. |
| `kenlm/freq_unigrames.py` | Frecuencia de las candidatas en un texto de entrenamiento → `<modelo>_freq.json`. Es el cuarto paso de `entrena_kenlm.sh`. |
| `kenlm/termes_ambigus.py` | Conteo y contextos de las candidatas en net, DOGV, AVL y UA. Prepara `avl_net.txt` y `ua_net.txt`. |
| `kenlm/entrena_kenlm.sh` | Entrena un KenLM. `TEXT=` reutiliza un texto ya exportado; `PODA=""` entrena sin poda; `ORDRE=` otro orden; `SENSE_FREQ=1` no rehace la tabla de frecuencias (mismo texto). |
| `prova_ordres.sh` | (16/11) Entrena el KenLM del sistema con orden 6, 7 y 8 y lo compara con el de orden 5 (`kenlm_o6_c1`...), solo en homógrafos y manual. |
| `sentit_general.py` | Entrena el clasificador de sentido general (`recompte`, `entrena`) → `sentit.json`. |

**Palabras y corpus nuevos** (qué regenerar y con qué órdenes): sección
«Mantenimiento» de `src/avlizador/traductor_cat_val/model_llengua/README.es.md`
(16/11).

---

## 7. Pendiente
1. ~~KenLM sin poda y con AVL + UA~~ (hecho el 11/11: no mejoran, sección
   4.9).
2. ~~Regresiones en el 151 y el BOE estricto~~ (hecho el 11/11, simulado:
   sección 4.9).
3. Ejecución real con el prior de frecuencia (ya arreglado el `Cronometre`),
   para confirmar la simulación.
4. Elegir: KenLM solo (falla «a cops» en texto real), **híbrido** (FLOR en
   cop/cops + KenLM) o FLOR. Después, integración en el paquete (`kenlm`
   como extra; el modelo de 77 MB y la tabla de frecuencias dentro de la
   imagen Docker).

### 7.1 Opciones para que KenLM vea más contexto (anotadas, sin hacer)
Decisión del usuario (11/11): se dejan como opciones; antes se esperan los
resultados del prior de frecuencia y de los modelos sin poda.

| # | Opción | Qué arregla | Coste en CPU | Riesgo |
|---|---|---|---|---|
| 1 | KenLM de orden 6-7 (**probado el 16/11, orden 6, 7 y 8: no cambia ninguna decisión**, sección 4.18) | un poco más de distancia | igual | apenas ayuda: las secuencias largas casi no se repiten |
| 2 | **KenLM en los dos sentidos**: otro modelo entrenado con las frases al revés; se suman las dos puntuaciones | el candidato se puntúa también con las 4 palabras de su derecha | ~0,1 ms | bajo; un entrenamiento + ~20 líneas |
| 3 | **Clasificador de sentido por palabra** (fastText supervisado): frases valencianas con «colp» o «vegada», la palabra oculta, se aprende cuál era con todas las palabras de la frase | usa toda la frase («boxejador», «destral» → colp) | ~0,1 ms, pocos MB | solo donde hay datos (cop/cops, manca, nou); no para recuita, fartanera, panotxa |
| 4 | Modelo bidireccional pequeño (p. ej. RoBERTa-ca, 125 M): hueco oculto, P(colp) frente a P(vegada) | toda la frase, a los dos lados | ~50-100 ms, ~500 MB | puede tener el sesgo de FLOR hacia el catalán general |
| 5 | Híbrido: FLOR solo para cop/cops (sección 4.5) | lo que hace FLOR en «cop» (33/33) | FLOR cargado (1,5 GB) | ninguno nuevo |

Orden propuesto si hacen falta: 2 y 3 (baratas, sin torch). Si no llegan a
≤ 3 graves, el híbrido (5). La 4, solo si fallan las otras.

### 7.2 Camino C: arreglar «cop» sin FLOR (plan del 11/11)
Después de elegir la base KenLM (sección 4.10), el único punto débil es
«cop/cops». Plan:

- **C1. Clasificador de sentido** (opción 3).
  - Datos: frases valencianas (net + DOGV + AVL) con «colp(s)» (~3.300) y
    una muestra de las de «vegada/vegades». La palabra se sustituye por un
    hueco; la etiqueta es cuál era. Se excluye lo parecido a la evaluación.
  - Modelo: primero Naive Bayes en Python puro (tabla de recuentos en JSON,
    sin dependencias, local); si se queda corto, fastText supervisado en
    Abaco.
  - Uso: decide las colisiones solo, o desempata cuando KenLM gana por poco.
- **C2. KenLM en los dos sentidos** (opción 2). Se entrena otro KenLM con el
  texto invertido y la puntuación es la media de los dos sentidos.
- **Prueba:**
  - Conjunto de usos reales de «cop»: manual (19), gplsi (16) y homógrafos
    (33), con la etiqueta sacada de la referencia, más frases del corpus
    apartadas del entrenamiento.
  - Comparar con FLOR y con la base en las 257 decisiones, los «cop» reales,
    el 151 y el BOE.

Orden propuesto: C1 primero (local).

**Esquema de C2 (KenLM en los dos sentidos):**

```
ENTRENAMIENTO (Abaco)
  valencia_net_dogv.txt              «el boxejador va rebre molts colps a la cara .»
    → cada frase al revés            «. cara la a colps molts rebre va boxejador el»
    → lmplz igual que la base        → valencia_net_dogv_inv_o5.binary

USO  «El boxejador va rebre molts cops a la cara.»
  1. Candidatas: A «...molts colps a la cara.»   B «...moltes vegades a la cara.»
  2. Cada una se puntúa dos veces:
       izq→der (KenLM normal):   P(colps | va rebre molts)    ← ve la izquierda
       der→izq (KenLM invertido): P(colps | a la cara .)       ← ve la derecha
  3. Puntuación = media de las dos − λ · log P(palabra) (mismo prior y criterio)
  4. Gana la mayor, con el margen de siempre
```

| | C1 (clasificador) | C2 (dos sentidos) |
|---|---|---|
| Qué mira | todas las palabras a ±8, sin orden | 4 palabras a cada lado, en orden |
| Cuándo actúa | solo en «cop/cops» y solo si KenLM duda | en todas las palabras ambiguas, siempre |
| Qué aprende | qué palabras van con cada sentido | secuencias valencianas |
| Coste | ~420 KB + spaCy (ya está) | otro KenLM (~77 MB) |

Son compatibles: si C2 mejora la base, C1 puede desempatar encima.

---

## 8. Registro de decisiones y resultados

| Fecha | Qué | Motivo / evidencia |
|---|---|---|
| 05/11 | FLOR con margen 2 y la catalana por defecto | Traducir mal cambia el sentido; no traducir solo deja la catalana. |
| 10/11 | Se descartan `kenlm_cat`, `diff` y fastText | Sección 4.1: no distinguen sentidos y `diff` ocupa 3 GB. |
| 10/11 | Limpiar el valenciano (`net`) compensa | `val_net` > `val` con la mitad de texto. |
| 10/11 | `kenlm_val_net` NO sustituye a FLOR tal cual | 19 graves frente a 3 (sección 4.2). |
| 10/11 | Margen 6 para KenLM: insuficiente | «cop» no depende del margen (sección 4.3). |
| 10/11 | DOGV sí; UA no para el KenLM valenciano | GD 0,84 frente a 0,46. |
| 11/11 | Bug del prior de KenLM («<s> w </s>») corregido | Por eso λ no hacía nada (sección 2.3). |
| 11/11 | Prior = frecuencia contada, no el unigrama de KenLM | 189 / 4 frente a 189 / 5 (sección 4.5). |
| 11/11 | `Criteri.lam_colisio` (λ propio de las colisiones) | El mejor λ de «cop» no es el de los homógrafos. |
| 11/11 | La AVL y la UA no resuelven la frecuencia | Sección 4.7: +6 % de texto, misma proporción. Se prueban igualmente (sin poda) por si aportan contextos. |
| 11/11 | Lanzadas en Abaco: tablas de frecuencia, KenLM sin poda (`valencia_net_dogv_np`, `valencia_tot_np`) y comparación con 151 y BOE estricto | Commit `ffbed87`. Pendiente de resultados. |
| 11/11 | Más contexto para KenLM (dos sentidos, clasificador de sentido, RoBERTa): solo anotado | Sección 7.1. Se espera antes a los resultados del prior y de la poda. |
| 11/11 | Bug: el `Cronometre` del comparador ocultaba el `prior` de KenLM (ejecuciones 0931 y 1232 con el prior antiguo) | Arreglado; las cifras de la sección 4.9 se simulan con el prior correcto. |
| 11/11 | Sin poda y AVL + UA: no mejoran | 185 y 186 frente a 189 (sección 4.9); 444-472 MB frente a 77 MB. Se queda `valencia_net_dogv` con poda. |
| 11/11 | KenLM solo para «cop» no es seguro en texto real | λ ≥ 1 de colisiones → 2 errores graves en el manual AVL («a cops», «dues cops»). El híbrido los evita. |
| 11/11 | Híbrido: no es lento (FLOR en ~1 % de frases) pero mete FLOR en la imagen | El usuario no lo ve claro (sección 4.8). |
| 11/11 | **Base = KenLM solo** (`valencia_net_dogv`, margen 3, λ 0,75 colisiones / 1,5 homógrafos, prior de frecuencia) | Decisión del usuario. 189 / 4 (simulado); 1 grave en texto real. Las mejoras se miden contra esta base (sección 4.10). |
| 11/11 | Los 2 graves de «manca» son dudosos (etiqueta del benchmark) | «carència» no es candidata; «Si en falta algun» es correcto. Pendiente de revisión del usuario. |
| 11/11 | Siguiente: camino C (clasificador de sentido para «cop», KenLM en dos sentidos) | Sección 7.2. Propuesto empezar por C1. |
| 11/11 | C1 funciona: «KenLM; si gana por < 2, clasificador» iguala a FLOR en las 52 colisiones | Sección 4.11. Total estimado 191 / 2 sin FLOR. Falta validarlo en más texto real. C2 (KenLM en dos sentidos), pendiente del entrenamiento en Abaco. |
| 11/11 | Ejecución real (`1430`): base 189 / 4 confirmada; C1 191 / 2; C2 188 / 5 | Sección 4.12. **C2 descartado** (no mejora, doble de memoria). |
| 11/11 | gplsi usa «colp» = «vez» en su referencia | 8 de 16 «cop»; se evalúa por sentido. En «cop» real (35): FLOR 35, C1 33, base 31. |
| 11/11 | Veto del clasificador: descartado | En los 2 «cop» que fallan el clasificador tampoco está seguro (sección 4.13). |
| 11/11 | «manca»: incoherencia del léxico (E0247 manca→falta frente a E0248 manques→carències) | Los 2 graves de C1 vienen de ahí (sección 4.13). Propuesto al usuario: E0247 → «carència» (compañero) y aceptar «falta» en HG2-028. Pendiente. |
| 11/11 | **Se integra KenLM + C1 en el paquete como opción complementaria** (FLOR sigue por defecto) | Decisión del usuario. Diseño: `--model kenlm`, ficheros en `AVLIZADOR_KENLM_DIR`, extra `[kenlm]`, clasificador intercambiable. Se hace el 12/11 en la rama `kenlm`. |
| 12/11 | KenLM + C1 integrado en el paquete (`--model kenlm`; FLOR por defecto) | Sección 4.14. Tests en verde y clasificador idéntico al de la ejecución `1430`. **Reproducido en Abaco**: 227 / 110 / 229 / 145 / 1.887 / 1.553, 0 errores. |
| 12/11 | Clasificador de «cop» reentrenado sin la AVL (para poder distribuirlo) | Sección 4.15. Mismas decisiones del sistema en las 68 colisiones; dev 0,830 frente a 0,831. Propuesto sustituir el `nb.json` (pendiente del usuario). |
| 12/11 | **Se quita la AVL del clasificador** (`nb.json` = sin AVL; `sentit_cop.py` sin AVL por defecto) | Decisión del usuario. Mismas decisiones del sistema (sección 4.15). |
| 12/11 | Fusión de `main` en `kenlm` (interfaz Transducens, concordancia de género) y PR #19/#20 a `main` | Sin conflictos; 107/108 tests (el que falla ya fallaba en `main`: texto de la portada). Hay que volver a medir el sistema. |
| 12/11 | Prueba: KenLM de lemas (solo, + C1, mezcla formas + lemas) y foto del sistema actual, lanzado con `prova_lemes.sh` | Propuesta del supervisor (sección 4.16). |
| 12/11 | Sistema tras la fusión: KenLM + C1 224 / 106 / 232 / 144 / 1.894 / 1.550; FLOR 217 / 95 / 231 / 145 / 1.894 / 1.551 | Sección 4.17. Bajadas por E0248 («manques» → «faltes») frente a referencias antiguas y un bug de concordancia («molt freda»); subidas en manual y BOE por la concordancia. |
| 12/11 | **KenLM de lemas: no se adopta** | Sección 4.16. Lemas + C1 189 / 5 frente a 186 / 10, pero toda la diferencia es «manques» (E0248); sin manca/manques, 169 / 2 frente a 170 / 0, y ~40× más lento. |
| 13/11 | **Referencias de los homógrafos corregidas** (usuario + Claude, con permiso) | Coherencia con el léxico (E0247 manca→falta, E0248 manques→faltes): «manca» nombre → «falta» (HG069-071, HG2-021…024) y «manques» nombre → «faltes» (HG075, HG076, HG2-033…036), en `benchmark_homografs_cat_val.json`, `benchmark_sistema_final_cat_val.json` (el que se evalúa como `homografs`) y v2. Error de concordancia: HG2-048 «d'una brollador» → «d'un brollador» (HG029 «dos vegades» se cambió a «dues» y se deshizo: el valenciano del proyecto usa «dos» invariable, regla `cat_val/concordanca_dos_dues.py`). Recuento sin volver a ejecutar (decisiones del job 3035): KenLM + C1 191 / 5 (HG077, HG2-038, HG2-040, HG2-043 «manques» → «faltes»; HG2-028 «Si en falta algun»); lemas + C1 191 / 3; lemas 193 / 13; mezcla 190 / 14. |
| 13/11 | **Regla del pronombre personal** (`punts.decisio_spacy`, `Punt.pronom_abans`, `pos_tagger.es_pronom_personal`, `Token.pron_type`) | Detrás de un pronombre personal (spaCy PRON + `PronType=Prs`; en mayúscula se vuelve a preguntar en minúscula, porque «Tu» inicial sale PROPN) no puede ir un nombre: si la lectura dialectal es nombre, se deja la catalana. Vale para cualquier homógrafo irresoluble, sin lista de palabras. En los benchmarks solo la activan «manques»/«manca» con pronombre (homógrafos v1 2, v2 6; manual, 151, BOE estricto y gplsi 0, tras corregir un falso positivo con «S'afegeixen»). Cambia 3 decisiones, las 3 a bien: HG077, HG2-038, HG2-040 («faltes» → «manques»). KenLM + C1, recuento: 191 / 5 → **194 / 2** (quedan HG2-043 «velles faltes» y HG2-028 «Si en falta algun»). FLOR ya las acertaba. Falta confirmarlo en Abaco. |
| 13/11 | Repetición en Abaco (`compara_models_20261113_1016`): **KenLM + C1 194 / 2** (confirma el recuento), lemas + C1 191 / 3, lemas 193 / 13, mezcla 193 / 11 | Sección 4.16, «Repetición del 13/11». Los lemas no mejoran: confirmado. |
| 13/11 | **KenLM de lemas y mezcla: descartados** | Repetición del 13/11 (sección 4.16): no mejoran ni aciertos ni graves y son ~50× más lentos. Los fallos que quedan son de frecuencia y de palabras sin datos en el corpus, que los lemas no tocan. |
| 13/11 | **Fallo: la tabla de frecuencias se había quedado vieja** | `valencia_net_dogv_freq.json` era del 11/11 (candidatas de entonces): tenía «carències» y no «faltes», la candidata de «manques» desde E0248. Una candidata que no está en la tabla cuenta como 0 apariciones, y con λ eso es una ventaja enorme (+~5 puntos para «faltes»). Regenerada en Abaco (`freq_unigrames.py`; «faltes» 420, «manques» 33; copia de la vieja en `_freq_20261111.json`) y vuelto a evaluar (`avalua_sistema_20261113_1145`, `compara_models_20261113_1145`): **191 aciertos / 1 grave / 65 sin traducir** (antes 194 / 2 / 61); exactas v1 228 → 226, v2 111 → 110, el resto igual. Cambian 5 decisiones, todas «manques»: los 4 nombres pasan de «faltes» a sin traducir y HG2-043 de grave a acierto. Para que no vuelva a pasar (hecho, rama `kenlm-per-defecte`): `freq_unigrames.py` cuenta las candidatas y **todas las formas de una palabra del léxico** (una palabra que se marque ambigua más adelante ya estará en la tabla); `ModelKenLM` avisa (`AvisFreqKenLM`) al cargar y al puntuar si una candidata no está en la tabla; test en `tests/test_kenlm.py`. La próxima vez que se regenere la tabla en Abaco ya saldrá con todas las formas. |
| 13/11 | **KenLM + clasificador pasa a ser el modelo por defecto; FLOR, opcional** | Decisión del usuario. Iguala o mejora a FLOR en todo menos 1 frase del 151 y 1 de gplsi (tabla «Estado actual»), ~8.000× más rápido y sin torch. `translate_cat_val(text)` usa KenLM; sin `kenlm` o sin los ficheros, motor solo + aviso; `model="kenlm"` explícito da error; `model="flor"` sigue funcionando (extra `[ml]`). `avlizador avalua` evalúa KenLM por defecto (la clave de FLOR pasa de `sistema_final` a `flor`). Rama `kenlm-per-defecte`. |
| 13/11 | **Imagen Docker solo con KenLM** (sin torch ni FLOR) | Decisión del usuario. Los ficheros de KenLM se copian de `docker/kenlm/` (fuera de git) al construir, en `/opt/kenlm`; ahora se traen de Abaco, más adelante se publicarán en Hugging Face. `mem_limit` 4g → 2g; fuera `TORCH_NUM_THREADS`, `OMP_NUM_THREADS` y las variables de Hugging Face. `NOTICE`: KenLM (LGPL-2.1) y los datos del modelo (MaCoCu CC0, DOGV: condiciones por revisar). |
| 13/11 | DOGV nuevo (`dades/dogv_apunt/nova/`): ampliación, no se reentrena todavía | Contiene los 10.289 documentos de antes, idénticos, y 5.413 más (casi todos de 2025, +7,2 M palabras). En las palabras ambiguas apenas aporta (1 «colp» frente a 3.784 «vegada»; 0 de reeixida, gandula, anou, panotxa…). Se usará para el clasificador general; reentrenar KenLM con él, solo si hace falta. |
| 13/11 | Siguiente: clasificador de sentido **general** (hoy solo «cop»), uno por punto ambiguo entrenado con las frases del corpus de cada candidata | Decisión del usuario. Si una candidata no tiene datos, sin clasificador (se queda la catalana si KenLM duda). |
| 13/11 | **Clasificador de sentido general, parte del sistema** (rama `kenlm-per-defecte`, sin commitear) | Decisión del usuario: nada específico de «cop». `sentit.ClassificadorSentit` (un Naive Bayes por grupo; clase «0» = primer candidato, «1» = segundo) y `sentit_general.py` (entrenamiento): las palabras salen del léxico; los puntos con los mismos `lemas` comparten grupo (singular y plural); frases de MaCoCu net + DOGV, sin la AVL. `tria`: el desempate (KenLM gana por < 2 → decide el clasificador) vale para **todos** los puntos que tengan clasificador; sin él, la regla de siempre. El sistema carga `sentit.json` si existe; si no, `nb.json` (el de «cop»). Datos: 9 de 12 grupos con ≥ 20 frases por clase (sin datos: fartanera, panotxa, recuita). |
| 13/11 | **Umbral de calidad: 0,7 de acierto equilibrado en el dev** | Decisión del usuario. Primer entrenamiento, acierto equilibrado en frases apartadas: cop 0,89, deu 0,81, cops 0,75, nou 0,59, manca 0,56, rentadora 0,50, gandula 0,50, reeixida 0,49, calces 0,39. Solo entra en el sistema un grupo que demuestre que acierta (≥ 0,7): cop, cops, deu. «manca» no separa sentidos porque en el valenciano real (DOGV) «manca» también se usa como nombre; los demás, por falta de datos. Cuando haya más datos, un grupo que pase el umbral entra solo. |
| 13/11 | **«nou» que no se traducía según el final de la frase** (fallo visto por el usuario en Docker) | La etiqueta de spaCy de «nou» cambia con un punto o un espacio al final («una nou» ADJ → «una nou.» NUM) y con NUM se dejaba siempre «nou». Dos arreglos: (1) spaCy etiqueta el texto sin los espacios del principio y del final (`pos_tagger._analitza_sense_espais`; ninguna frase de los benchmarks los tiene, no cambia ninguna cifra); (2) NUM detrás de un determinante indefinido femenino singular («una nou», rasgos de spaCy, sin lista) no es el numeral: decide el modelo. «la nou» (dorsal) y «unes nou hores» siguen siendo numeral (decisión del 03/11). |
| 13/11 | **Medido en Abaco** (`avalua_sistema_20261113_1308`, `compara_models_20261113_1308`; clasificador general con cop, cops y deu + las dos reglas de «nou») | 257 decisiones: **193 aciertos / 1 grave / 63 sin traducir** (11:45: 191 / 1 / 65). Exactas v1 226 → **227**, v2 110 → **111**; manual 232, 151 144, BOE estricto 1.894 y gplsi 1.550 igual. Cambian 4 decisiones: las 2 ganancias son de la regla «una nou» (HG059 «Es va menjar una nou», HG2-001 «Ha caigut una nou de l'arbre»: spaCy NUM → ahora decide KenLM y acierta «anou»). El clasificador general decide 8 puntos (antes 6) sin cambiar ningún resultado: separar «cop» y «cops» da las mismas decisiones, y en «deu» decide 2 (HG2-053 bien; HG2-047 «Aquesta deu no s'asseca mai» se queda «deu», igual que antes). Ningún error grave nuevo. |
| 16/11 | **KenLM de orden 6, 7 y 8: descartado** (`compara_models_20261116_0916` y `_0922`) | Mismo texto, poda y tabla de frecuencias; solo cambia el orden. Las 257 decisiones son idénticas a las del orden 5 (193 aciertos / 1 grave / 63 sin traducir; exactas v1 227, v2 111, manual 232); la diferencia entre candidatas varía ≤ 0,06 en el 90 % de los casos. Con el mejor criterio (margen 1), +1 en v2 (HG2-034). Ocupa más (91-112 MB frente a 77) y un orden > 6 exige compilar `kenlm` con `KENLM_MAX_ORDER`/`MAX_ORDER=10`. Sección 4.18. |
| 16/11 | **Lemas cerrados; se queda la estructura actual** (KenLM de formas, orden 5, + clasificador general) | Decisión del usuario. Los lemas se probaron en todas las palabras ambiguas; ganan en algunas (manca, gandules, panotxa) pero con 8-18 casos por palabra y traduciendo más (13 graves frente a 1): no se usan ni por palabra. spaCy decide 68 de las 257 decisiones y falla 7, todas leves. Los «sin traducir» vienen sobre todo de falta de datos (41 + 14 de 63). Sección 4.16, «Cierre». |
| 19/11 | **La concordancia de los candidatos la hace la regla, no KenLM** (`concordanca="motor"` por defecto; participios pegados al nombre; «diversos», «algun», «L'últim») | Decisión del usuario, por FLORES+ devtest 461 («és absoluta una vegada») y 782 («El xocolate desfeta»). Motor solo: 0 frases distintas en 6 benchmarks. KenLM en Abaco sin «algun»: 226 / 112 / 232 / 144 (HG030 «Alguns vegades»); con «algun» (`avalua_sistema_20261119_0850`): **227 / 112 / 232 / 144**, métricas idénticas a la 2.0.0. Sección 4.20. |
| 19/11 | **Errores de AINA de la 2.0.0**: concordancia del artículo y la contracción hacia la izquierda («a la seua vivenda»), spaCy también en los resolubles («per deu estats»), género del nombre según el fichero morfológico («el nou de Bowie»), **λ 1,25 para los irresolubles** (`lam_irresoluble`) | Informe del ETL de `traductor-es-va-en` (AINA ca-en, FLORES+). Con el KenLM real (puntuado en Abaco, sistema en local): `main` 227 / 111 / 232 / 144, la rama con λ 1,5 da las mismas frases, con λ 1,25 **227 / 112 / 232 / 144** (+HG2-113, sin pérdidas); λ 1,0 pierde BM-AVL-191. Casos de AINA: 20 de 23 bien; quedan «programes de nou» y «manca»/«rentadora» (catalana por defecto). Sección 4.21. |
