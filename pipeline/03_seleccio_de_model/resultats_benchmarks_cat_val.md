# Resultados de los benchmarks cat→val

Tabla de consulta rápida con todas las métricas de cada ejecución de
`evalua_models.py` en catalán → valenciano. Las ejecuciones más nuevas van
arriba. Para el contexto (cómo se hizo cada benchmark, qué falla y por
qué), ver `documentacio/hoja_de_ruta_benchmark_manual.md` (sección 10) y
`documentacio/metodologia_i_resultats.md` (secciones 15 y 17).

**Sistema principal = motor + FLOR-760M** (`--model traductor_ml`, es
`traductor.translate_cat_val`). El motor solo (`--model traductor`) se
mide al lado solo como comparación.

## Cómo se evalúa todo de una vez

`avalua_sistema_final.py` ejecuta el sistema final en todos los
benchmarks (manual BOE, AVL y mezcla; 151; 151 + homógrafos; BOE estricto
y amplio; gplsi) en un solo proceso, con todas las métricas, y al acabar
escribe la tabla en `resultats/resum_sistema_final_<fecha>.md`, lista
para pegarla aquí. Desde esta carpeta:

```powershell
python avalua_sistema_final.py
```

Opciones: `--amb-motor` (añade el motor solo), `--benchmarks manual_boe
manual_avl` (solo esos), `--limit 5` (prueba rápida), `--llista` (ver los
nombres). El BOE estricto completo (9.453) solo entra si se pide:
`--benchmarks boe_estricte_complet`. La columna "Errors" tiene que ser 0.

## Métricas

| Métrica | Qué mide | Mejor |
|---|---|---|
| Exactas | Frase idéntica a la referencia (sin distinguir mayúsculas, apóstrofos normalizados) | ↑ |
| BLEU | Coincidencia de n-gramas de palabras (sacrebleu, media de las frases) | ↑ |
| chrF | Coincidencia de n-gramas de caracteres (sacrebleu, media de las frases) | ↑ |
| chrF++ | chrF + n-gramas de palabras (`word_order=2`) | ↑ |
| TER | % de ediciones de palabra para llegar a la referencia; mover un bloque = 1 edición (`sacrebleu.sentence_ter`). De corpus: suma de ediciones / suma de palabras de la referencia | ↓ |
| WER | Igual que el TER pero sin desplazamientos: Levenshtein por palabras (`distancia_paraules`). De corpus. WER ≥ TER; si se separan, hay reordenaciones | ↓ |

TER y WER (desde el 30/10/2026): separación por espacios, distinguen
mayúsculas, la puntuación va pegada a la palabra. Cada frase del JSON
guarda `ter`, `wer`, `ter_edicions`, `wer_edicions` y `ref_paraules`; el
resumen, `ter_corpus` y `wer_corpus`.

## 30/10/2026 (08:41-09:02) — Sistema final en todos los benchmarks

`python avalua_sistema_final.py` (motor + FLOR-760M), 0 errores. El
benchmark de **evaluación principal es el manual mezcla (458)**.

| Benchmark | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ |
|---|---|---|---|---|---|---|
| **Manual mezcla BOE + AVL (458)** | **227 (49,6 %)** | **90,88** | **96,34** | **95,92** | **5,61** | **6,01** |
| Manual BOE (246) | 32 (13,0 %) | 83,82 | 93,59 | 92,82 | 9,26 | 9,94 |
| Manual AVL (212) | 195 (92,0 %) | 99,08 | 99,54 | 99,52 | 0,41 | 0,41 |
| 151 (banco curado, 154 frases) | 146 (94,8 %) | 99,32 | 99,66 | 99,65 | 0,27 | 0,27 |
| 151 + homógrafos (253) | 226 (89,3 %) | 96,38 | 98,21 | 98,18 | 0,74 | 0,74 |
| BOE estricto, muestra (2.000) | 1.880 (94,0 %) | 98,95 | 99,64 | 99,56 | 0,32 | 0,59 |
| BOE amplio, muestra (2.000) | 1.203 (60,2 %) | 88,24 | 95,54 | 94,75 | 3,73 | 6,00 |
| gplsi (1.958) | 1.544 (78,9 %) | 93,52 | 97,00 | 96,86 | 2,77 | 2,79 |

Los manuales dan exactamente lo mismo que las ejecuciones de las 08:14-08:19
(misma versión del sistema).

**Frente a la última medida de cada benchmark** (frase a frase; las
referencias son idénticas, solo cambia el sistema):

| Benchmark | Antes | Ahora | Ganadas / perdidas | Medida anterior |
|---|---|---|---|---|
| 151 | 146 | 146 | = | 23/10 |
| 151 + homógrafos | 226 | 226 | = | 29/10 |
| BOE estricto (muestra) | 1.778 | **1.880** | +104 / −2 | 22/10, motor solo |
| BOE amplio (muestra) | 1.206 | 1.203 | +0 / −3 | 23/10, motor + FLOR |
| gplsi | 1.486 | **1.544** | +94 / −36 | 22/10, motor solo |

- **BOE estricto, +102**: es el trabajo de datos del 22-29/10:
  "servei(s)"→"servici(s)" en mayúsculas y plural (46), "recerca"→
  "investigació" (10), "desenvolupament"→"desenrotllament" (9),
  "comitè"→"comité" (6), "despeses"→"gastos" (4), subjuntivos
  ("tingui"→"tinga", "hagi"→"haja"). Pierde 2.
- **BOE amplio, −3**: las tres por el dato nuevo `E1664`/`E1665`
  ("finalitat(s)"→"fi"/"fins"), ya señalado el 28/10; el BOE quiere
  "finalitat".
- **gplsi, +58 netas**. Gana: "petit(s/a/es)"→"xicotet..." (37, `E0167`
  del 30/10), "obtenir"/"mantenir"→"obtindre"/"mantindre" (28),
  "vermell"→"roig" (6), "aviat"→"prompte", "servei"→"servici". Pierde:
  "cementiri"→"cementeri" (5, la referencia no lo cambia), FLOR elige
  "vegada" donde la referencia dice "colp" (9: el gplsi usa "colp" para
  "vez"), "durada"→"duració" (4), ordinales canónicos "sisé"→"sext" (3) y
  "recerca"→"investigació" (2). Dos casos especiales:
  - `gplsi_35719`: ahora sale "d'espill" (correcto) y la referencia dice
    "de espill" (errata de la referencia).
  - `gplsi_45688`: **regresión real**: "Necessito informació..." ya no se
    traduce ("Necessite"). spaCy `md` etiqueta "Necessito" a principio de
    frase como `PROPN` y `cat_val/conjugacions_dict.py::_pos_admet` lo
    descarta. Es el bug ya visto el 28/10 ("sol·licitin", "Afirmin");
    con "Ara necessito..." sí traduce. Propuesta pendiente: descartar el
    `PROPN` solo si la palabra va en mayúscula y no empieza la frase.

Ficheros: `resultats/benchmark_sistema_final_<benchmark>_20261030_0841.json`
y la tabla en `resultats/resum_sistema_final_20261030_0841.md`.

## 30/10/2026 — Benchmarks manuales (BOE, AVL y mezcla)

Benchmarks en `dades/benchmark_manual/`:
`benchmark_manual_boe_cat_val.json` (246, BOE revisado desde el original),
`benchmark_manual_avl_cat_val.json` (212, AVL) y
`benchmark_manual_cat_val.json` (458 = **las del BOE y las de la AVL
juntas**, no frases nuevas). 0 líneas `ERROR:`.

| Benchmark | Sistema | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ |
|---|---|---|---|---|---|---|---|
| BOE 246 | **motor + FLOR** | 32 (13,0 %) | 83,82 | 93,59 | 92,82 | **9,26** | **9,94** |
| BOE 246 | motor solo | 32 (13,0 %) | 83,53 | 93,46 | 92,66 | 9,50 | 10,15 |
| AVL 212 | **motor + FLOR** | **195 (92,0 %)** | **99,08** | **99,54** | **99,52** | **0,41** | **0,41** |
| AVL 212 | motor solo | 182 (85,8 %) | 98,35 | 99,16 | 99,12 | 0,80 | 0,80 |
| Mezcla 458 | **motor + FLOR** | **227 (49,6 %)** | **90,88** | **96,34** | **95,92** | **5,61** | **6,01** |
| Mezcla 458 | motor solo | 214 (46,7 %) | 90,39 | 96,10 | 95,65 | 5,91 | 6,30 |

Ediciones (WER) por frase, motor + FLOR:

| Ediciones | 0 | 1 | 2-3 | 4-6 | 7+ |
|---|---|---|---|---|---|
| BOE (246) | 32 | 36 | 81 | 77 | 20 |
| AVL (212) | 195 | 11 | 6 | 0 | 0 |

Longitud media de la referencia: BOE 32,3 palabras, AVL 26,4.

Resumen de la lectura:
- FLOR frente al motor solo: AVL +14 / −1 exactas (pierde BM-AVL-191,
  "les anous"); en el BOE cambia 12 frases, todas a mejor, pero ninguna
  llega a exacta.
- AVL: los 17 fallos que quedan: "xic/xica" donde la AVL quiere
  "xiquet/xiqueta" (9), "reportar" frente a "generar" (3, de la
  referencia) y 5 sueltos.
- BOE: las diferencias son sobre todo de la referencia, no dialectales:
  futuro ("pot"→"podrà" ×20), reformulaciones, artículos y orden. Mirar
  TER/WER y chrF, no las exactas.

Ficheros de resultados (`resultats/`):

| Benchmark | Motor + FLOR | Motor solo |
|---|---|---|
| BOE | `benchmark_Traductor_Invers_ML_FLOR-760M_20261030_0814.json` | `benchmark_Traductor_Invers_20261030_0814.json` |
| AVL | `benchmark_Traductor_Invers_ML_FLOR-760M_20261030_0816.json` | `benchmark_Traductor_Invers_20261030_0816.json` |
| Mezcla | `benchmark_Traductor_Invers_ML_FLOR-760M_20261030_0819.json` | `benchmark_Traductor_Invers_20261030_0819.json` |

(Las ejecuciones de las 08:01-08:05 del mismo día dan las mismas
traducciones, pero sin TER ni WER.)

Cómo se repite (desde esta carpeta):

```bash
for b in boe_ avl_ ""; do
  python evalua_models.py --model traductor_ml --direccio cat-val --benchmark ../../dades/benchmark_manual/benchmark_manual_${b}cat_val.json
  python evalua_models.py --model traductor    --direccio cat-val --benchmark ../../dades/benchmark_manual/benchmark_manual_${b}cat_val.json
done
```
