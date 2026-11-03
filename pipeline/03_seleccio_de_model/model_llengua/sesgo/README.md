# Pruebas para reducir el sesgo de FLOR (02/11/2026)

FLOR-760M prefiere la palabra que ha visto más veces ("rentadora" frente
a "llavadora", "nou" frente a "anou", "deu" frente a "brollador"),
porque se entrenó con mucho más catalán que valenciano. El margen 5
compensa en parte ese sesgo (ver `../../traces/README.md`), pero no lo
corrige. Aquí se prueban tres opciones para corregirlo.

## Las tres opciones

1. **Párrafo valenciano delante**: cada frase candidata se puntúa como
   continuación de un párrafo fijo en valenciano normativo
   (`paragrafs.json`: P1 escrito a mano, P2-P5 sacados de la AVL sin
   ninguna palabra ambigua). No se entrena nada; va algo más lento.
2. **Frecuencia en textos valencianos**: a la nota se le suma
   `μ × (log f_val − log f_cat)`. Las frecuencias son de la AVL y del BOE
   en valenciano frente al BOE en catalán (`freq.json`). Solo ayuda con
   las palabras que aparecen en esos textos: "gandula", "hamaca",
   "brulla", "fartada" y "panotxa" salen 0 veces.
3. **FLOR adaptado al valenciano (LoRA)**: un adaptador entrenado con
   40.000 frases de la AVL y del BOE en valenciano, sin ninguna frase de
   los benchmarks. En Abaco con GPU (`entrena_lora.sh`); después se usa
   en CPU.

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

```bash
python pipeline/03_seleccio_de_model/model_llengua/sesgo/sesgo_flor.py puntua --paragraf P1 --eixida pipeline/03_seleccio_de_model/model_llengua/sesgo/resultats/P1.json
python pipeline/03_seleccio_de_model/model_llengua/sesgo/sesgo_flor.py compara pipeline/03_seleccio_de_model/model_llengua/sesgo/resultats/*.json
```

## Resultados

Palabras ambiguas acertadas (la referencia usa un solo candidato). La v2
sale con 161 y no 160: en una frase hay dos palabras ambiguas ("deu
rentadores").

| Configuración | v1 (para elegir) | v2 (comprobación) | Manual (comprobación) |
|---|---|---|---|
| Ahora (λ 0,5, margen 5) | 83/101 | 113/161 | 33/34 |
| Mejor λ y margen elegidos con la v1 (λ 0,75) | 85/101 | 113/161 | 33/34 |
| **Opción 2** (μ 2, elegido con la v1) | **88/101** | **117/161** | 32/34 |
| Opción 1, P1 | *pendiente* | | |
| Opción 1, P2 y P4 | *pendiente* | | |
| Opción 3, LoRA | *pendiente (Abaco)* | | |

**Opción 2**: gana 7 casos en las comprobaciones ("colp" 2, "anou(s)",
"brollador" 3, "carència", "llavadora", "panolla") y pierde 2: "manca"
verbo (HG2-032) pasa a "carència", y "cop" con sentido de "vez"
(BM-AVL-005) pasa a "colp". Empuja hacia "colp" porque "colp" aparece 38
veces en los textos valencianos y 0 en los catalanes, mientras que
"vegada" sale casi igual en los dos.

La primera prueba de la opción 1 (02/11, con P1 y una sola puntuación
por candidato, sin las variantes de concordancia) dio v1 87 y v2 115.
Las pasadas de ahora la repiten con el mismo cálculo que el traductor.

## Pendiente

- **La opción 1 es lenta en local**: la pasada sin párrafo tardó 17
  minutos, y la de P1 llevaba más de 68 a las 17:14. FLOR vuelve a leer
  el párrafo entero en cada llamada: frases completas, frases parciales
  (`dreta`) y palabras sueltas (`prior`). Dos arreglos posibles:
  (a) calcular el párrafo una sola vez y reutilizarlo (`past_key_values`
  de transformers), comprobando que da las mismas puntuaciones que ahora;
  (b) lanzar las pasadas en Abaco, en paralelo y solo con CPU.
- Terminar las pasadas P1, P2 y P4 (en local) y, en Abaco, la opción 3:
  copiar `resultats/lora.json` y ejecutar `compara` con todos los
  ficheros.
- Probar combinaciones: la opción 1 o la 3 junto con la 2 (`compara` ya
  incluye la frecuencia en cada fichero).
- Con la mejor opción, medir el benchmark manual completo (458 frases)
  y las trazas antes de cambiar nada del paquete.
