# Benchmarks del BOE para el traductor

Tres benchmarks construidos a partir del BOE alineado catalán/valenciano
(267.963 pares, `dades/boe/catala/` y `dades/boe/valencia/`). Sirven para
medir el traductor `traductor/` sobre texto oficial real, sobre todo en la
dirección cat→val.

Todos tienen el mismo formato que los demás benchmarks del proyecto (una
lista de `{"id", "oriental", "occidental"}`, donde `oriental` es el catalán
y `occidental` el valenciano), y se generan con un solo comando, desde la
raíz del repo:

```
python pipeline/05_corpus_boe/construeix_boe_dialectal.py
```

El script tarda unos minutos (spaCy) y reproduce los ficheros idénticos
(semilla 21). Esta carpeta está fuera de git (`dades/`): si se pierde, se
vuelve a generar.

## Qué hay

| Fichero | Pares | Para qué sirve |
|---|---|---|
| `benchmark_boe_mostra_2000.json` | 2.000 | Muestra general, sin filtrar. Mide el traductor contra el BOE tal cual, con todo el ruido de estilo. |
| `benchmark_boe_dialectal_estricte.json` | 2.000 (de 9.453) | **Regresiones.** Solo pares en los que todas las diferencias son dialectales seguras. |
| `benchmark_boe_dialectal_ampli.json` | 2.000 (de 73.705) | **Huecos.** Pares sin reformulación; aquí aparecen las diferencias que el motor todavía no conoce. |
| `benchmark_boe_dialectal_estricte_complet.json` | 9.453 | El estricto entero. |
| `benchmark_boe_dialectal_ampli_complet.json` | 73.705 | El amplio entero. |

Los dos ficheros `*_complet.json` son para análisis; para medir el motor
se usan las muestras de 2.000.

## Por qué hacen falta

La versión valenciana del BOE es una traducción independiente que
reformula mucho: "Pel que fa a" → "Quant a", el presente pasa a futuro
("és" → "serà"), frases reordenadas... En la muestra general, el 56,5% de
los pares son reformulaciones de este tipo, y ahí el motor acierta el 1%
de las frases. No es un fallo dialectal, es estilo. Los dos benchmarks
dialectales separan ese ruido de lo que queremos medir.

## Cómo se construyen

1. **Muestra general**: líneas de 40 a 300 caracteres con ratio de longitud
   valenciano/catalán de 0,85 a 1,15; 2.000 al azar.
2. **Filtro estructural** (para los dos dialectales; líneas de 30 a 300
   caracteres, mismo ratio): se alinean las palabras de los dos lados
   (`difflib`) y solo se quedan los pares **idénticos** o con **solo
   sustituciones palabra por palabra** (bloques 1:1 de hasta 2 palabras,
   sin inserciones, eliminaciones ni reordenaciones; se admite la "a" de
   "per a"). Esto es el **amplio**. No usa diccionario.
3. **Estricto**: del amplio, los pares con al menos una diferencia en los
   que **todas** las diferencias son dialectales seguras:
   - (a) el par está en los diccionarios del traductor (léxico,
     conjugaciones, demostrativos);
   - (b) spaCy da el mismo lema y los mismos rasgos (tiempo, modo,
     persona, número, forma verbal) en los dos lados, con el mismo
     prefijo elidido y el mismo enclítico; el género no se compara, para
     que entre "dues"/"dos";
   - (c) solo cambia el acento abierto/cerrado ("entès"/"entés");
   - (d) es la "a" de "per a" + infinitivo;
   - (e) es un incoativo, con la misma transformación que aplica
     `traductor/rules/cat_val/incoatius.py` ("estableix"/"establix").

   Cualquier otra diferencia (mayúsculas, tiempo verbal, palabra sin
   clasificar) deja el par fuera.

Recuento sobre el BOE completo: 109.563 pares descartados por longitud,
84.695 reformulados, 32.079 idénticos, 7.895 con diferencias de
mayúsculas, 24.278 con alguna diferencia sin clasificar, 7.906 explicados
por el diccionario y 1.547 por los criterios (b) a (e).

Dos versiones previas del estricto se descartaron por fugas detectadas
mirando ejemplos: con solo "mismo lema" entraban cambios de tiempo verbal
("pot" → "podrà"), y sin exigir los mismos clíticos entraban cambios de
estructura ("acords" → "d'acords", "s'ha" → "ha").

**Limitación del estricto**: el criterio (a) usa el propio diccionario, así
que mide lo que el motor **debería** saber. Sirve para detectar
regresiones, no para descubrir huecos; para eso está el amplio.

## Cómo se usan

Desde `pipeline/03_seleccio_de_model/`:

```
python evalua_models.py --model traductor --direccio cat-val --benchmark ../../dades/boe/benchmarks/benchmark_boe_dialectal_estricte.json
python evalua_models.py --model traductor --direccio cat-val --benchmark ../../dades/boe/benchmarks/benchmark_boe_dialectal_ampli.json
python evalua_models.py --model traductor --direccio cat-val --benchmark ../../dades/boe/benchmarks/benchmark_boe_mostra_2000.json
```

La línea "Exactes" que sale por pantalla está normalizada; la cifra que
vale es el campo `exactes` del JSON que se guarda en `resultats/`.

## Resultados del motor cat→val (21/10/2026)

| Benchmark | Exactas | BLEU | chrF |
|---|---|---|---|
| Estricto | 1.677/2.000 (83,9%) | 96,87 | 98,80 |
| Amplio | 1.177/2.000 (58,9%) | 87,91 | 95,39 |
| Muestra general | 458/2.000 (22,9%) | ~77 | — |

JSON en `pipeline/03_seleccio_de_model/resultats/benchmark_traductor_cat-val_boe_dialectal_{estricte,ampli}_20261021.json`
y `..._20261021_participis.json` (muestra general).

**Fallos más frecuentes del estricto** (errores del motor o de los datos,
sin arreglar a 21/10/2026):
- "Servei(s)"/"SERVEIS" no pasa a "Servici(s)" en mayúscula o plural (44);
- "durada" no pasa a "duració" (23);
- "recerca" no pasa a "investigació" (21);
- se escribe "anous" donde debería quedar "nous" (18);
- se pierden mayúsculas: "Decret Llei", "Orgànica", "Llei" (~30);
- se escribe "interesos" en lugar de "interessos" (10);
- "este" donde la referencia quiere "eixe" (13; es el valor por defecto
  de los demostrativos);
- "Comitè"/"comprèn" se quedan sin el acento valenciano (10).

**En el amplio** dominan las diferencias de estilo de la referencia, no
dialectales: el presente pasa a futuro ("és" → "serà" 57, "pot" → "podrà"
52), "a" → "en" (59) y mayúsculas.

Detalle y contexto: `documentacio/hoja_de_ruta_traductor_invers.md`,
sección "21/10/2026 (cierre) — Dos benchmarks BOE dialectal".
