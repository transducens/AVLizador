# Pruebas para reducir el sesgo de FLOR (02-03/11/2026)

FLOR-760M prefiere la palabra que ha visto más veces ("rentadora" frente
a "llavadora", "nou" frente a "anou", "deu" frente a "brollador"),
porque se entrenó con mucho más catalán que valenciano. El margen 5
compensa en parte ese sesgo (ver `../../traces/README.md`), pero no lo
corrige. Aquí se prueban tres opciones para corregirlo.

**Decisión (03/11/2026, usuario): se integra la opción 1 con el párrafo
P1** en el paquete (`model_llengua/puntuador.py`,
`CONTEXT_PER_DEFECTE`). Las opciones 2 y 3 se descartan. Resultados en
todos los benchmarks: sección "Integración".

## Las tres opciones

1. **Párrafo valenciano delante**: cada frase candidata se puntúa como
   continuación de un párrafo fijo en valenciano normativo
   (`paragrafs.json`: P1 escrito a mano, P2-P5 sacados de la AVL sin
   ninguna palabra ambigua). No se entrena nada. Se aplica a todas las
   llamadas a FLOR: la frase entera, la frase hasta la palabra (`dreta`)
   y la palabra sola (`prior`).
2. **Frecuencia en textos valencianos**: a la nota se le suma
   `μ × (log f_val − log f_cat)`. Las frecuencias son de la AVL y del BOE
   en valenciano frente al BOE en catalán (`freq.json`). Solo ayuda con
   las palabras que aparecen en esos textos: "gandula", "hamaca",
   "brulla", "fartada" y "panotxa" salen 0 veces.
3. **FLOR adaptado al valenciano (LoRA)**: un adaptador (rango 16, 1
   época, 768 pasos) entrenado con 40.000 frases de la AVL y del BOE en
   valenciano, sin ninguna frase de los benchmarks. En Abaco con GPU
   (`entrena_lora.sh`); después se usa en CPU.

**Protocolo**: los parámetros (λ, μ, margen, qué párrafo) se eligen
**solo con la v1** (`homografs`). La **v2** (`homografs_v2`) y las palabras
ambiguas del **manual** solo sirven para comprobar.

## Ficheros

| Fichero | Qué hace |
|---|---|
| `prepara_dades.py` | Genera `paragrafs.json`, `freq.json` y `entrenament_valencia.txt` (este último no entra en git) a partir de `dades/avl/` y `dades/boe/` |
| `sesgo_flor.py puntua` | Puntúa con FLOR (con `--paragraf` o `--adaptador`) las palabras ambiguas de la v1, la v2 y el manual → `resultats/<nombre>.json` |
| `sesgo_flor.py compara` | Prueba todas las combinaciones de λ, μ y margen sin volver a llamar a FLOR, elige con la v1 y muestra la v2 y el manual |
| `entrena_lora.py`, `entrena_lora.sh` | Opción 3: entrena el adaptador en Abaco y luego puntúa con él |

`resultats/` y `lora_valencia/` no entran en git: las cifras están aquí.

```bash
python pipeline/03_seleccio_de_model/model_llengua/sesgo/sesgo_flor.py puntua --paragraf P1 --eixida pipeline/03_seleccio_de_model/model_llengua/sesgo/resultats/P1.json
python pipeline/03_seleccio_de_model/model_llengua/sesgo/sesgo_flor.py compara pipeline/03_seleccio_de_model/model_llengua/sesgo/resultats/*.json
```

## Resultados

Palabras ambiguas acertadas (la referencia usa un solo candidato). La v2
sale con 161 y no 160: en una frase hay dos palabras ambiguas ("deu
rentadores"). "Criterio actual" = λ 0,5, margen 5, sin frecuencia.

| Configuración | v1 (para elegir) | v2 (comprobación) | Manual (comprobación) |
|---|---|---|---|
| Base, criterio actual | 83/101 | 113/161 | 33/34 |
| Base, mejor en v1 (λ 0,75) | 85/101 | 113/161 | 33/34 |
| Opción 2, frecuencia (μ 2, elegido con la v1) | 88/101 | 117/161 | 32/34 |
| **Opción 1, P1** (escrito a mano, 27 palabras), criterio actual | **90/101** | **124/161** | 33/34 |
| Opción 1, P2 (AVL, "corfa", 59 palabras), criterio actual | 88/101 | 118/161 | 33/34 |
| Opción 1, P4 (AVL, nota de prensa, 59 palabras), criterio actual | 85/101 | 116/161 | 33/34 |
| Opción 3, LoRA, criterio actual | 80/101 | 119/161 | 33/34 |
| Opción 3, LoRA, mejor en v1 (λ 0, margen 10) | 86/101 | 121/161 | 33/34 |

Combinaciones: sumar la frecuencia a P1 no ayuda (v1 90, v2 121, con
λ 0,25 y μ 0,5). Con P2 y P4, elegir λ y margen con la v1 los sube a 89
(margen 6; P4 también λ 1), pero son ajustes de una o dos palabras y no
se usan. LoRA + párrafo no se ha probado (descartado el LoRA, ver abajo).

### Qué gana y qué pierde cada uno frente a la base (criterio actual)

| | Gana | Pierde |
|---|---|---|
| P1 | +22: deu→brollador 4, rentadora(es)→llavadora(es) 6, gandula (vaga) 4, cop→colp 2, fartaneres 2, recuita, manca→carència, calces→bragues, panotxa→panolla | −4: "manca" verbo 2, rentadora(es) cuando la referencia la deja 2 |
| P2 | +20: casi las mismas | −10: las de P1 más gandula, fartanera, panotxes, manques |
| P4 | +22: casi las mismas | −17: gandula→hamaca 2, panotxa(es) 4, manca/manques 4, rentadora(es) 3... |
| LoRA | +12: gandula (vaga) 4, fartaneres 2, colp, brollador, carència, calces... | −9: gandula→hamaca 4, cop→colp, nou→anou, manca, panotxes... |

Lectura:

- **Los tres párrafos mejoran la base en la v1 y en la v2** y ganan en las
  mismas palabras (deu, rentadora, cop, fartaneres): el efecto no es
  casualidad de un párrafo. Pero **cuánto mejora depende del párrafo**:
  P1 (corto, valenciano cotidiano lleno de rasgos: hui, xiquets, eixit,
  vore, seua) es el más limpio; P4 (nota de prensa formal, con pocos
  rasgos dialectales) casi no se separa de la base.
- **Todos pierden "manca" verbo** ("la regió manca de...") en la v2: el
  párrafo empuja hacia "carència" también cuando no toca.
- **El LoRA sí aprende valenciano** (perplejidad en valenciano 26,95 →
  11,35), pero eso no lo hace elegir mejor: gana y pierde en las mismas
  palabras (acierta "gandula" vaga, falla "gandula" hamaca), y en la v1
  baja de 83 a 80. Además es lo más complicado de mantener (entrenar en
  GPU, un fichero más, `peft`). **Descartado.**
- **La frecuencia** mejora menos que P1, pierde en el manual y no cubre
  las palabras que no salen en el corpus. **Descartada.**
- El manual no distingue nada (34 palabras ambiguas, 33 aciertos en casi
  todo).
- **Ojo**: solo se han comparado tres párrafos, y P1 se eligió con la v1
  entre esos tres. La v2 confirma la elección, pero es poca muestra.

## Tiempo de ejecución

- **Opción 1**: la primera versión volvía a leer el párrafo en cada
  llamada a FLOR (P1 llevaba más de 68 minutos sin acabar, frente a 17
  sin párrafo). Arreglado el 03/11: el párrafo pasa por FLOR **una sola
  vez** al cargar el modelo y se guardan sus `past_key_values`; en cada
  llamada solo se calculan los tokens de la frase. Pasadas completas (las
  tres benchmarks, 296 palabras): **base 1.029 s, P1 918 s, P2 915 s**:
  el párrafo ya no cuesta tiempo. Las puntuaciones coinciden con las del
  cálculo completo salvo ruido de bfloat16 (≤0,4 en log-probabilidad,
  ~0,04 en la diferencia entre candidatos); la versión del paquete da
  exactamente las mismas que `sesgo_flor.py`.
- **Opción 2**: sin coste (una suma).
- **Opción 3**: el adaptador se fusiona con el modelo al cargarlo; la
  traducción tarda lo mismo. El entrenamiento, ~5 minutos en GPU.

## Incidencias

- **LoRA, job 2646 (02/11)**: cortado por el límite de 6 h. El driver de
  Abaco es CUDA 12.9 y el `torch` de PyPI por defecto venía compilado para
  un CUDA más nuevo: `cuda False`, y el entrenamiento se hizo en CPU.
  Arreglado: `entrena_lora.sh` instala `torch` del índice cu128 si no ve
  la GPU (y para si sigue sin verla), y `entrena_lora.py` no entrena en
  CPU sin `--permet-cpu`. El job 2647 (03/11) entrenó en GPU en 273 s.

## Integración (03/11/2026)

`ModelLlengua` lleva ahora un `context` (por defecto
`CONTEXT_PER_DEFECTE` = P1); `ModelLlengua(context=None)` vuelve al
comportamiento anterior. Afecta a todo lo que usa `ModelLlengua`:
`translate_cat_val`, `avlizador avalua`, `model_llengua/avalua.py` y las
trazas. `sesgo_flor.py` carga el modelo con `context=None` (pone él el
párrafo).

Medida en todos los benchmarks (`avalua_sistema_final.py`, 03/11 09:13,
0 errores; tabla en `resultats/resum_20261103_0913.md`) y comparada
**frase a frase** con la ejecución del 30/10 (sin párrafo; el motor no ha
cambiado desde entonces: las únicas frases distintas son las de palabras
ambiguas). La v2 se compara con las trazas del 02/11
(`traces/resultats/homografs_v2.json`, también sin párrafo).

| Benchmark | Sin párrafo | Con P1 | Frases que cambian |
|---|---|---|---|
| Manual mezcla (458) | 227 | 227 | 0 |
| Manual BOE (246) / AVL (212) | 32 / 195 | 32 / 195 | 0 |
| 151 | 146/154 | 146/154 | 0 |
| **151 + homógrafos (253)** | 226 | **233** (BLEU 96,38 → 97,57) | +7 / −0 |
| **Homógrafos v2 (160)** | 111 | **122** | +15 / −4 |
| BOE estricto (2.000) | 1.880 | 1.880 | 0 |
| BOE amplio (2.000) | 1.203 | 1.203 | 0 |
| gplsi (1.958) | 1.544 | **1.547** | +3 / −0 (y 1 sin efecto) |

- **Gana**: homógrafos +7 ("un últim colp", "gandula" tumbona, "brollador"
  ×3, "recuita", "colp"); v2 +15 ("brollador", "llavadora(es)" ×6,
  "bragues", "gandula" ×3, "panolla", "fartades" ×2, "carència"); gplsi +3
  ("colp(s)", "tercer colp": golpes reales que antes salían "vegada").
- **Pierde** (solo en la v2, −4): "manca" verbo → "carència" (HG2-031,
  HG2-032) y "rentadora(es)" cuando la referencia la deja (HG2-061,
  HG2-070). Son las mismas pérdidas que en la prueba.
- **Los benchmarks reales sin homógrafos no cambian** (manual, 151, BOE):
  el párrafo solo actúa donde FLOR decide.
- **Tiempo**: el mismo que el 30/10 (~5 min los manuales y el 151, ~5 min
  los homógrafos, ~25 min todo con la v2 nueva). Medido por llamada:
  1,68 s con párrafo y 1,74 s sin él.
- `pytest`: 48/48 (todos los doctests incluidos; ninguno cambia).

## Pendiente

- **"manca" verbo** sigue fallando (y ahora en 2 frases más): el arreglo
  natural es el filtro de categoría/concordancia entre spaCy y FLOR
  (`../../traces/README.md`), no el párrafo.
- Solo se han probado tres párrafos (P3 y P5 sin medir). Si se quiere
  afinar, probar más párrafos cortos y cotidianos como P1, eligiendo
  siempre con la v1.
- `avalua_sense_context.py`: el sistema completo sin párrafo, para
  repetir la comparación en el mismo día si cambia algo del motor.
