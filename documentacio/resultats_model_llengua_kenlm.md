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

Resultados: pendientes.

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
| `kenlm/entrena_kenlm.sh` | Entrena un KenLM. `TEXT=` reutiliza un texto ya exportado; `PODA=""` entrena sin poda. |

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
| 1 | KenLM de orden 6-7 | un poco más de distancia | igual | apenas ayuda: las secuencias largas casi no se repiten |
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
| 12/11 | Prueba: KenLM de lemas (solo, + C1, mezcla formas + lemas) y foto del sistema actual, lanzado con `prova_lemes.sh` | Propuesta del supervisor (sección 4.16). Pendiente de resultados. |
