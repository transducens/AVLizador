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

- solo ve **hacia la izquierda y como mucho 4 palabras**: en «molts cops a la
  cara», «cara» no influye en cómo puntúa «cops», y «boxejador» queda lejos;
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
| `valencia_net_dogv_np_o5` (pendiente) | igual, **sin poda** | — |
| `valencia_tot_np_o5` (pendiente) | net + DOGV + AVL (sin evaluación) + UA (GD ≥ 0,8), sin poda | — |

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
1. Ejecución real con el prior de frecuencia y λ de colisiones (Abaco), y
   simulación fina en local.
2. KenLM **sin poda** (`valencia_net_dogv_np`) y con **AVL + UA**
   (`valencia_tot_np`).
3. Regresiones en el 151 y el BOE estricto.
4. Elegir: KenLM solo, híbrido o FLOR. Después, integración en el paquete
   (`kenlm` como extra; el modelo y la tabla de frecuencias dentro de la
   imagen Docker).

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
