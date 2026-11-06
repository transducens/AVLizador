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

## 06/11/2026 09:31 — Margen 2 con la catalana por defecto + léxico del 05/11

`avlizador avalua` (sistema final, 0 errores). Cambios frente a la
última tabla: FLOR solo traduce los homógrafos si ve la traducción >2
puntos más probable que la catalana (antes, margen 5 a favor del motor;
ver `src/avlizador/traductor_cat_val/model_llengua/README.es.md`,
"Margen 2 con la catalana por defecto"); léxico del compañero del 05/11
(género, "esmentar"→"mencionar", "contenir"→"contindre"), con las 8
formas de subjuntivo de "mantenir" recuperadas (`cc1791d`); arreglos de
`b0f493f` (`problema` en lista y participio femenino con apóstrofo).

| Benchmark | Sistema | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ | Errors |
|---|---|---|---|---|---|---|---|---|
| Manual mezcla BOE + AVL (458) | Motor + FLOR-760M | 228/458 (49,8 %) | 90,93 | 96,33 | 95,92 | 5,59 | 5,98 | 0 |
| Manual BOE (246) | Motor + FLOR-760M | 33/246 (13,4 %) | 83,90 | 93,56 | 92,81 | 9,24 | 9,89 | 0 |
| Manual AVL (212) | Motor + FLOR-760M | 195/212 (92,0 %) | 99,08 | 99,54 | 99,52 | 0,41 | 0,41 | 0 |
| BOE estricto, muestra (2.000) | Motor + FLOR-760M | 1887/2000 (94,3 %) | 99,03 | 99,65 | 99,58 | 0,30 | 0,57 | 0 |
| BOE amplio, muestra (2.000) | Motor + FLOR-760M | 1212/2000 (60,6 %) | 88,35 | 95,57 | 94,80 | 3,66 | 5,92 | 0 |
| 151 + homógrafos (253) | Motor + FLOR-760M | 218/253 (86,2 %) | 95,14 | 97,54 | 97,54 | 0,88 | 0,88 | 0 |
| Homógrafos v2, equilibrado por sentido (160) | Motor + FLOR-760M | 95/160 (59,4 %) | 84,29 | 92,29 | 92,22 | 5,82 | 5,82 | 0 |

Frente al 05/11 (margen 5, léxico anterior: manual 229, BOE 32, AVL 196,
estricto 1.888, amplio 1.213, homógrafos 233, v2 124):

- **Margen 2**: homógrafos −15 y v2 −29. En el v2, las frases que dejan
  la catalana 42 → 57/59 y las que piden la valenciana 82 → 38/101: menos
  errores de sentido, más palabras sin traducir (precio aceptado). En el
  manual pierde BM-AVL-191 ("les anous" → "les nous").
- **"mantenir"** (formas recuperadas): +2 exactas (BM-BOE-113,
  boe_164913).
- **"esmentar" → "mencionar"**: unas 30 frases cambian, −1 exacta en el
  estricto (boe_122224). Las fuentes oficiales prefieren "esmentar":
  corpus AVL 231 "esment*" / 65 "mencion*", BOE valenciano 5.166 / 3.310
  (BOE catalán 11.133 / 109). Pendiente de hablarlo con el compañero.
- **Participio femenino**: "a l'esmentada" ya da "a la mencionada" (antes
  "al mencionada"), 4 frases, ninguna llega a exacta (la referencia dice
  "esmentada").
- Ejecución anterior de hoy sin el arreglo de `te_problema` (no válida):
  manual 213, v2 82 (= motor solo).

## 03/11/2026 10:40 — P1 + concordancia del adjetivo con el determinante

Si spaCy da ADJ a la palabra ambigua y su género no concuerda con el
determinante ("una nou", "les nous"), decide FLOR en vez de spaCy
(`punts.decisio_spacy`; detalle en `traces/README.md`). Solo se midieron
estos tres benchmarks: en el resto la regla no salta (comprobado con
spaCy). Frente a las 09:41: v2 +2 (HG2-004, HG2-016), manual +1
(BM-AVL-191), 0 pérdidas.

| Benchmark | Sistema | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ | Errors |
|---|---|---|---|---|---|---|---|---|
| 151 + homógrafos (253) | Motor + FLOR-760M (P1 + det.) | 233/253 (92,1 %) | 97,57 | 98,97 | 98,92 | 0,49 | 0,49 | 0 |
| Homógrafos v2, equilibrado por sentido (160) | Motor + FLOR-760M (P1 + det.) | **124/160 (77,5 %)** | 91,90 | 95,92 | 95,89 | 3,24 | 3,24 | 0 |
| Manual mezcla BOE + AVL (458) | Motor + FLOR-760M (P1 + det.) | **228/458 (49,8 %)** | 90,90 | 96,35 | 95,93 | 5,60 | 6,00 | 0 |

## 03/11/2026 09:41 — Sistema final con párrafo valenciano delante (P1)

Desde el 03/11 FLOR puntúa cada frase como continuación de un párrafo
corto en valenciano (`ModelLlengua(context=...)`, `CONTEXT_PER_DEFECTE`)
para reducir su sesgo hacia la forma catalana. Pruebas y comparación
frase a frase en `model_llengua/sesgo/README.md`. Respecto al 30/10 solo
cambian homógrafos (+7), gplsi (+3) y la v2 (111 → 122, +15/−4); el
resto, idéntico.

| Benchmark | Sistema | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ | Errors |
|---|---|---|---|---|---|---|---|---|
| Manual mezcla BOE + AVL (458) | Motor + FLOR-760M (P1) | 227/458 (49,6 %) | 90,88 | 96,34 | 95,92 | 5,61 | 6,01 | 0 |
| Manual BOE (246) | Motor + FLOR-760M (P1) | 32/246 (13,0 %) | 83,82 | 93,59 | 92,82 | 9,26 | 9,94 | 0 |
| Manual AVL (212) | Motor + FLOR-760M (P1) | 195/212 (92,0 %) | 99,08 | 99,54 | 99,52 | 0,41 | 0,41 | 0 |
| 151 (banco curado) | Motor + FLOR-760M (P1) | 146/154 (94,8 %) | 99,32 | 99,66 | 99,65 | 0,27 | 0,27 | 0 |
| 151 + homógrafos (253) | Motor + FLOR-760M (P1) | **233/253 (92,1 %)** | 97,57 | 98,97 | 98,92 | 0,49 | 0,49 | 0 |
| Homógrafos v2, equilibrado por sentido (160) | Motor + FLOR-760M (P1) | **122/160 (76,2 %)** | 91,27 | 95,79 | 95,72 | 3,41 | 3,41 | 0 |
| BOE estricto, muestra (2.000) | Motor + FLOR-760M (P1) | 1880/2000 (94,0 %) | 98,95 | 99,64 | 99,56 | 0,32 | 0,59 | 0 |
| BOE amplio, muestra (2.000) | Motor + FLOR-760M (P1) | 1203/2000 (60,2 %) | 88,24 | 95,54 | 94,75 | 3,73 | 6,00 | 0 |
| gplsi (1.958) | Motor + FLOR-760M (P1) | **1547/1958 (79,0 %)** | 93,61 | 97,05 | 96,91 | 2,74 | 2,75 | 0 |

## 02/11/2026 — Baseline: AVLizador frente a LLM generalistas (manual mezcla)

9 LLM usados tal cual en Abaco (Ollama, 1 GPU por modelo, instrucción
mínima igual para todos, temperatura 0; job 2578, 0 errores) más el
umbral de no traducir. Script, condiciones, lectura completa y tablas del
BOE y de la AVL en `baseline_llm/` (README y `resum_baseline.md`).

| Sistema | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ | GD | GDV | GDC |
|---|---|---|---|---|---|---|---|---|---|
| *Referencia (valenciano)* | — | — | — | — | — | — | *0,9973* | *0,9998* | *0,9182* |
| **AVLizador: motor + FLOR-760M** | **227/458 (49,6 %)** | **90,88** | **96,34** | **95,92** | **5,61** | **6,01** | **0,9936** | **0,9995** | **0,9189** |
| AVLizador: motor solo | 214/458 (46,7 %) | 90,39 | 96,10 | 95,65 | 5,91 | 6,30 | 0,9764 | 0,9981 | 0,9194 |
| Sin traducir (catalán tal cual) | 1/458 (0,2 %) | 69,25 | 87,97 | 86,21 | 15,76 | 16,08 | 0,0264 | 0,9200 | 0,9978 |
| gemma3:12b | 11/458 (2,4 %) | 70,54 | 87,46 | 85,93 | 16,13 | 16,72 | 0,3889 | 0,9530 | 0,9701 |
| llama3.1:8b | 1/458 (0,2 %) | 68,32 | 87,55 | 85,73 | 16,28 | 16,69 | 0,0601 | 0,9239 | 0,9951 |
| gemma4:12b | 1/458 (0,2 %) | 67,49 | 87,06 | 85,23 | 16,88 | 17,22 | 0,0564 | 0,9273 | 0,9957 |
| qwen3:8b | 1/458 (0,2 %) | 66,86 | 86,88 | 84,97 | 17,23 | 17,57 | 0,0382 | 0,9227 | 0,9969 |
| qwen3:14b | 2/458 (0,4 %) | 66,83 | 86,81 | 84,89 | 17,32 | 17,83 | 0,0435 | 0,9227 | 0,9965 |
| qwen2.5:7b | 1/458 (0,2 %) | 63,57 | 85,36 | 83,23 | 19,50 | 19,85 | 0,0372 | 0,9242 | 0,9971 |
| qwen2.5:14b | 0/458 (0,0 %) | 59,04 | 82,96 | 80,57 | 22,55 | 22,93 | 0,0975 | 0,9325 | 0,9927 |
| mistral-nemo:12b | 1/458 (0,2 %) | 59,35 | 82,89 | 80,52 | 22,86 | 23,40 | 0,1263 | 0,9365 | 0,9908 |
| salamandra-7b-instruct | 4/458 (0,9 %) | 57,77 | 79,50 | 77,61 | 26,06 | 27,14 | 0,1517 | 0,9359 | 0,9885 |

GD = formas valencianas / formas con marca; GDV = 1 − catalanas /
palabras; GDC = 1 − valencianas / palabras (más bajo = más valenciano).
Ningún LLM baja del TER de no traducir, y su salida sigue siendo
catalán: GD 0,04-0,15 (gemma3, 0,39) frente a 0,994 de AVLizador; GDC
0,99, como la entrada. Dejan "aquest(a/s/es)", "seva/seves",
"serveis"... sin cambiar o reformulan la frase. Por partes, TER del
sistema final frente al mejor LLM: BOE 9,26 frente a 18,83 (gemma3; sin
traducir, 20,16); AVL 0,41 frente a 10,16 (llama3.1; sin traducir, 9,50).

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
