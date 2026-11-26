# XCOMET-XL sobre el benchmark manual (03/11/2026)

[COMET](https://github.com/Unbabel/COMET) es una métrica aprendida de
Unbabel: un modelo que lee la frase de origen, la traducción y la
referencia y da una nota de 0 a 100. **XCOMET-XL** (`Unbabel/XCOMET-XL`,
unos 3.500 millones de parámetros) es la versión grande; además de la
nota, marca los trozos de la traducción que considera errores
(`error_spans`, con gravedad *minor*, *major* o *critical*).

Aquí se puntúan traducciones que **ya existen** del manual mezcla (458
frases), sin volver a traducir:

- `../baseline_llm/resultats/`: AVLizador 1.0.1, el motor solo, **sin
  traducir** (el catalán tal cual) y los 9 LLM del baseline.
- `entrades/avlizador_1.1.0.json`: AVLizador 1.1.0 (`avlizador avalua
  --benchmarks manual` del 03/11/2026).

## Qué queremos saber

COMET mide sobre todo si se conserva el **significado**, y el catalán
sin traducir significa lo mismo que el valenciano. Por eso el "sin
traducir" es la prueba clave: si COMET le da casi la misma nota que a
AVLizador, **no ve el dialecto** y no sirve para evaluar esta tarea (o
solo sirve junto con el GD). Si los separa, es una buena métrica para
presentar. Los `error_spans` dirán si marca como error las formas
catalanas ("aquest", "seva", "serveis"...).

## Ficheros

| Fichero | Qué hace |
|---|---|
| `puntua_comet.py` | Carga el modelo una vez y puntúa los JSON que se le pasan (`entrada`, `hipotesi`, `referencia`); un JSON por sistema con la nota y los errores de cada frase, y `resum__<modelo>.md` con la nota media por sistema (mezcla, BOE, AVL) |
| `comet.sh` | Job de SLURM para Abaco (1 GPU), con su propio venv |
| `entrades/` | Traducciones que no están en el baseline (AVLizador 1.1.0) |
| `resultats/` | Salidas (las de prueba, `*_limit*`, no entran en git) |

## Cómo lanzarlo en Abaco

Una sola vez, en el login:

1. En huggingface.co, entrar en `Unbabel/XCOMET-XL` y aceptar las
   condiciones (el modelo es de acceso restringido).
2. Crear un token de **lectura** (Settings → Access Tokens → Read) y
   guardarlo en Abaco con el venv del paquete:
   `~/venvs/avlizador/bin/hf auth login` (en versiones antiguas,
   `huggingface-cli login`; a "Add token as git credential?", no). Queda
   en `~/.cache/huggingface/token` y el job lo usa solo.

Después:

```bash
cd ~/scrapeo/AVLizador && git pull && git checkout comet
cd pipeline/03_seleccio_de_model/comet
LIMIT=10 sbatch comet.sh     # prueba: 10 frases por sistema
cat logs/<jobid>_xcomet.out  # torch ... cuda True, y una tabla al final
sbatch comet.sh              # todo
```

La primera vez el job crea el venv `~/venvs/comet` (torch de CUDA 12.8 +
`unbabel-comet`) y descarga el modelo (~14 GB): tarda bastante más.
Variables: `PRECISIO=fp32` (si fp16 diera problemas; necesita una GPU de
16 GB), `QE=1` (sin referencia: solo origen y traducción), `LOT=4` (si
falta memoria en la GPU).

Traer los resultados (desde `scrapeo/` en local):

```powershell
scp -r nmartin@abaco:scrapeo/AVLizador/pipeline/03_seleccio_de_model/comet/resultats pipeline/03_seleccio_de_model/comet/
```

## Decisiones

- **fp16 por defecto**: XCOMET-XL en fp32 ocupa ~14 GB y las GPU de
  Abaco tienen 11 GB.
- **Venv propio** (`~/venvs/comet`): `unbabel-comet` fija versiones que
  chocan con el venv del paquete, y el torch de PyPI por defecto no ve
  las GPU de Abaco (driver CUDA 12.9; ver el job 2646 del LoRA en
  `../model_llengua/sesgo/README.md`).
- **Licencia**: XCOMET-XL es CC BY-NC-SA 4.0 (sin uso comercial). Sirve
  para evaluar; no entra en el paquete ni en la entrega.
- **Sin probar en local** (decisión del usuario): solo se comprobó el
  script con un modelo falso.

## Resultados (jobs 2682 de prueba y 2697 completo, 03/11/2026)

Los dos jobs acabaron sin errores (GPU en uso, fp16; el `.err` solo trae
avisos de Lightning). Unos 37 s por sistema. Tabla completa en
`resultats/resum__XCOMET-XL.md`:

| Sistema | Mezcla | BOE | AVL | Frases con error |
|---|---|---|---|---|
| **Sin traducir** (catalán tal cual) | **97,41** | 98,22 | 96,47 | 147/458 |
| AVLizador 1.0.1 | 97,40 | 98,00 | 96,70 | 175/458 |
| AVLizador 1.1.0 | 97,40 | 98,01 | 96,70 | 174/458 |
| qwen3:14b | 97,37 | 98,18 | 96,43 | 162/458 |
| llama3.1:8b | 97,32 | 98,13 | 96,37 | 152/458 |
| Motor solo | 97,29 | 97,85 | 96,64 | 182/458 |
| gemma4:12b … qwen2.5:14b | 97,19 … 93,26 | | | 184-347/458 |

**Conclusión: XCOMET-XL no ve el dialecto y no sirve para evaluar esta
tarea.** El "sin traducir" queda primero, empatado con AVLizador, y los
LLM que casi no tocan el catalán (qwen3:14b, llama3.1:8b) quedan por
delante del motor solo. Los datos:

- **Casi no castiga las formas catalanas.** En el "sin traducir" hay 245
  "aquest*" y solo marca 3 como error. Marca alguna vez "noi" (5),
  "tenir" (3) y "seva/meva/teva" (1 cada una); el resto de los errores
  que marca son preposiciones y artículos.
- **Castiga el valenciano correcto.** AVLizador acierta exactamente la
  referencia en 229 frases, y aun así XCOMET marca errores en 84 de
  ellas. En 31 da menos de 95 y en 109 puntúa mejor el catalán sin
  traducir que la traducción idéntica a la referencia. Marca como error
  "vostés", "Orde", "servici", "tindre", "llavada", "abellix", "estes",
  "xic/xics", "gastos"… Caso extremo: BM-AVL-012, idéntica a la
  referencia, 64,75 (el catalán sin traducir, 74,23).
- **Diferencia frase a frase entre AVLizador 1.1.0 y el "sin
  traducir"**: −0,01 de media. AVLizador gana en 58 frases, el "sin
  traducir" en 103 y hay 297 empates (±0,5).
- La AVL puntúa más baja que el BOE en todos los sistemas: el texto es
  más literario y más dialectal.

En resumen, XCOMET mide si se conserva el significado y se fía de un
valenciano "estándar" cercano al catalán. Para presentar resultados se
quedan las métricas de superficie (exactas, BLEU, chrF, TER, WER) y el
**GD/GDV/GDC**, que son las que separan a AVLizador del "sin traducir"
(TER 5,57 frente a 15,76; GD 0,99 frente a 0,03). XCOMET puede servir,
como mucho, de control de que una traducción no rompe el significado:
ningún sistema nuestro baja de los LLM malos en eso.

### AVLizador 2.0.0 (17/11/2026, modo completo)

Petición del usuario: puntuar también la versión 2.0.0 (KenLM
`valencia_net_dogv2` + clasificador `sentit_dogv2_avl`), como el resto de
sistemas. Entrada: `entrades/avlizador_2.0.0.json`, la salida de
`avlizador avalua --benchmarks manual` de la evaluación de release
(`resultats_release_2.0.0/kenlm_manual_20261117_1009.json`). Rama
`version-2.0.0` (`19d995c`); el job vuelve a puntuar todos los sistemas
y da las mismas notas que el 03/11 a los de antes.

| Sistema | Mezcla | BOE | AVL | Frases con error |
|---|---|---|---|---|
| **AVLizador 2.0.0** (motor + KenLM + clasificador) | **97,44** | 98,06 | **96,73** | 168/458 |
| Sin traducir (catalán tal cual) | 97,41 | **98,22** | 96,47 | **147/458** |
| AVLizador 1.0.1 (motor + FLOR-760M) | 97,40 | 98,00 | 96,70 | 175/458 |
| AVLizador 1.1.0 (motor + FLOR-760M, P1) | 97,40 | 98,01 | 96,70 | 174/458 |
| qwen3:14b | 97,37 | 98,18 | 96,43 | 162/458 |
| llama3.1:8b | 97,32 | 98,13 | 96,37 | 152/458 |
| Motor solo | 97,29 | 97,85 | 96,64 | 182/458 |
| gemma4:12b … qwen2.5:14b | 97,19 … 93,26 | | | 184-347/458 |

La 2.0.0 queda primera por **0,03 puntos** sobre el "sin traducir", que
sigue ganando en el BOE y tiene menos frases marcadas con error. La
conclusión no cambia: **XCOMET-XL no ve el dialecto**; la 2.0.0 solo
confirma que no rompe el significado (como las anteriores, por delante
de todos los LLM). Las métricas que separan a AVLizador del "sin
traducir" siguen siendo las de superficie y el GD (manual mezcla: TER
5,58 frente a 15,76).

### Siguiente: dos modos más y pares contrastivos (04/11/2026, petición del supervisor)

Para separar el problema del modelo del de cómo se le plantea la tarea,
`puntua_comet.py` tiene ahora `--mode` (en el job, `MODE=`):

- `MODE=ref`: traducción + referencia, **sin el original catalán**. Así el
  "sin traducir" deja de tener ventaja por ser idéntico al origen.
- `MODE=qe`: origen + traducción, sin referencia (estimación de calidad).
  Se añade la **referencia valenciana como un sistema más**: el par
  referencia / "sin traducir" es el par contrastivo valenciano / catalán
  de cada frase, y el resumen dice en cuántas gana el valenciano.

XCOMET no tiene un modo de "solo la traducción". Para eso está el juez
LLM de `../jutge_llm/` (GEMBA-ESA con Qwen 3.6, del WMT26; Gemma 4 descartado).

```bash
MODE=ref sbatch comet.sh
MODE=qe sbatch comet.sh
```

### Modo `ref`: sin ver el catalán (04/11/2026, prueba `LIMIT=10` y completo)

Solo traducción + referencia valenciana; la referencia entra también como
sistema, comparada consigo misma (debería ser el techo):

| Sistema | Mezcla | BOE | AVL | Frases con error |
|---|---|---|---|---|
| **Sin traducir** (catalán tal cual) | **97,17** | 97,81 | 96,44 | 204/458 |
| qwen3:14b | 97,12 | 97,76 | 96,37 | 209/458 |
| llama3.1:8b | 97,11 | 97,77 | 96,34 | 209/458 |
| qwen3:8b | 97,04 | 97,58 | 96,41 | 211/458 |
| gemma4:12b | 96,89 | 97,48 | 96,21 | 232/458 |
| salamandra-7b-instruct | 96,73 | 97,61 | 95,70 | 200/458 |
| AVLizador 1.1.0 | 96,69 | 97,25 | 96,05 | 227/458 |
| AVLizador 1.0.1 | 96,68 | 97,24 | 96,04 | 228/458 |
| Motor solo | 96,61 | 97,14 | 96,00 | 231/458 |
| **Referencia valenciana** (= la referencia) | **96,54** | 96,86 | 96,16 | 187/458 |
| gemma3:12b … qwen2.5:14b | 96,51 … 93,54 | | | 253-349/458 |

**La referencia, comparada consigo misma, queda por debajo del catalán
sin traducir y XCOMET marca error en 187 de sus 458 frases** (hipótesis y
referencia son el mismo texto). En la prueba de 10 frases pasaba igual
(97,31 frente a 98,20). Es decir, XCOMET no mide el parecido con la
referencia: castiga las formas valencianas por sí mismas, venga o no el
original catalán. **Queda descartado del todo para esta tarea**, en
cualquier modo (`MODE=qe` se lanzó al final, el 09/11/2026, y lo
confirma: ver la sección siguiente). El juez LLM de `../jutge_llm/` (Qwen
3.6, GEMBA-ESA solo con la traducción) da lo mismo: prefiere el catalán.

### Modo `qe`: sin referencia (09/11/2026, completo)

Solo catalán de origen + traducción (como un usuario que no tiene
referencia). Lanzado al final para cerrar los tres modos; la referencia
valenciana entra como un sistema más (`referencia__XCOMET-XL_qe.json`):

| Sistema | Mezcla | BOE | AVL | Frases con error |
|---|---|---|---|---|
| qwen3:14b | **97,12** | 97,75 | 96,39 | 196/458 |
| salamandra-7b-instruct | 97,11 | 97,98 | 96,09 | 185/458 |
| llama3.1:8b | 97,09 | 97,70 | 96,37 | 193/458 |
| **Sin traducir** (catalán tal cual) | 97,04 | 97,66 | 96,32 | 184/458 |
| AVLizador 1.0.1 | 97,00 | 97,49 | 96,43 | 284/458 |
| gemma4:12b | 96,98 | 97,51 | 96,38 | 238/458 |
| AVLizador 1.1.0 | 96,98 | 97,49 | 96,40 | 285/458 |
| qwen3:8b | 96,95 | 97,43 | 96,39 | 209/458 |
| Motor solo | 96,91 | 97,42 | 96,32 | 291/458 |
| gemma3:12b | 96,87 | 97,49 | 96,14 | 259/458 |
| **Referencia valenciana** (manual) | **96,82** | 97,07 | 96,52 | 280/458 |
| qwen2.5:7b | 95,72 | 96,31 | 95,03 | 274/458 |
| mistral-nemo:12b | 95,39 | 96,11 | 94,55 | 319/458 |
| qwen2.5:14b | 93,56 | 94,04 | 93,00 | 356/458 |

Pares contrastivos (referencia valenciana − catalán sin traducir, misma
frase): gana el valenciano en 91, empate (±0,5) en 175, gana el catalán
en 192; diferencia media −0,22.

Lectura:

- **La referencia valenciana queda por debajo de 10 de los 13 sistemas**,
  también del catalán sin traducir (96,82 frente a 97,04), y XCOMET marca
  error en 280 de sus 458 frases. Es el resultado que se esperaba: sin
  referencia, con el catalán delante, lo que se aparta del original se
  castiga.
- **Sigue sin ver el dialecto**: en el "sin traducir" marca como error
  solo 4 de las 245 apariciones de *aquest\**; en cambio, de las 227
  frases en que AVLizador 1.0.1 coincide exactamente con la referencia,
  marca error en 126. Los trozos marcados en la referencia caen en formas
  valencianas normativas: *servicis/servici*, *esta*, *estos*,
  *arreplega*, *duració*, *díhuit*... (los `error_spans` salen partidos
  en subpalabras: "s", "x", "ix", "ci").
- Las diferencias entre los sistemas buenos son de décimas (96,9-97,1),
  menores que la que separa a la referencia del "sin traducir".

**Conclusión: XCOMET-XL descartado en los tres modos** (completo, `ref` y
`qe`). En los tres, el catalán sin traducir puntúa igual o mejor que
AVLizador y que la propia referencia valenciana. Para esta tarea se
quedan las métricas de superficie (exactas, BLEU, chrF, TER, WER) junto
con el GD, que es el único que separa el valenciano del catalán.

## Cómo interpretar XCOMET en esta tarea (conclusión, 20/11/2026)

Con la 2.0.0 puntuada en modo `qe` y el desglose frase a frase
(`../desglossament_frases/README.es.md`, secciones del 19 y el 20/11).

**Qué mide.** XCOMET-XL imita valoraciones humanas de traducciones entre
lenguas distintas (WMT: inglés–alemán, chino–inglés…). Sin referencia, lo
que responde es: «¿esta frase dice lo mismo que el original y está bien
escrita?». En una adaptación catalán → valenciano el significado no cambia,
así que la nota más alta la saca lo más parecido al original. No sabe que
el destino es el valenciano normativo de la AVL.

**Pruebas:**

- En modo `qe`, sin traducir saca 97,04, igual que AVLizador 2.0.0
  (97,04), y la referencia valenciana algo menos (96,82).
- En la 2.0.0, de los 596 tramos que marca como error, 263 caen en una
  forma valenciana del léxico (esta, servicis, xic…) y ninguno en una
  catalana.
- En modo `ref`, la referencia comparada consigo misma saca 96,54, por
  debajo de sin traducir (97,17); marca error en 187 frases idénticas a la
  referencia. Del catalán sin traducir solo marca 3 de 245 «aquest*» en
  modo completo (4 en `qe`).
- Entre la referencia y la 2.0.0 (+0,22 para la 2.0.0) no decide el
  dialecto (GD 0,998 y 1,000), sino quién se aparta menos del catalán: le
  resta el futuro del BOE valenciano oficial («podrà» frente a «pot») y le
  resta «xic».
- Frase a frase es ruidoso: la confianza de los tramos ronda 0,42 (solo 7
  de 596 por encima de 0,5 en la 2.0.0) y la diferencia entre la referencia
  y la 2.0.0 varía 2,4 puntos de una frase a otra.

**Usos:**

| Uso | ¿Sirve? |
|---|---|
| Medir cuán valenciano es un texto | No: no ve el dialecto |
| Ordenar sistemas de adaptación dialectal | No: gana el que menos cambia, incluso no traducir |
| Comparar con la referencia | No: castiga su estilo y su valenciano normativo |
| Recompensa para entrenar un modelo | No: enseñaría a no traducir |
| Control de que no se rompe el sentido | Sí, con cuidado |

Un adaptador perfecto debería sacar en XCOMET más o menos lo mismo que el
catalán sin traducir, porque no cambia el significado. La 2.0.0 saca eso
(97,04) y, frente a la 1.1.0, no baja en ninguna frase. Una bajada clara
frente a sin traducir sería una alarma solo si es de varios puntos y en
una frase donde el sistema se aparta de la referencia; las diferencias
pequeñas son ruido.

La calidad de la adaptación se mide contra la referencia (exactas, chrF,
TER) y con el GD/GDV de la salida; si hace falta, con evaluación humana.
El juez LLM (`../jutge_llm/`, Qwen 3.6) lleva a la misma conclusión: tampoco
ve el dialecto y llega a premiar una concordancia equivocada («Amb esta fi»
65 frente a «Amb este fi» 45).

Para explicarlo: «XCOMET mide la fidelidad al original, no el dialecto de
destino. En una adaptación catalán → valenciano la nota más alta la saca el
texto sin cambiar. Que AVLizador empate con el catalán sin traducir significa
que no pierde sentido ni fluidez, que es lo único que XCOMET puede decirnos
aquí. Para medir la adaptación usamos la referencia y el Grau Dialectal.»

