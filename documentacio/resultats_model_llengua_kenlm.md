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

---

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
