# Desglose por frase: XCOMET-XL sin referencia y juez Qwen 3.6

Petición del 19/11/2026: no quedarse con la media de cada métrica, sino ver
frase a frase dónde difieren XCOMET-XL sin referencia (`../comet/`, modo
`qe`: catalán + traducción) y el juez LLM (`../jutge_llm/`, Qwen 3.6
35B-A3B, GEMBA-ESA solo con la traducción), en el manual mezcla (458).

`desglossa_frases.py` no puntúa nada: lee los JSON que ya existen y añade a
cada frase y sistema nuestras medidas (igual a la referencia, chrF y TER
contra la referencia, GD de la salida con sus marcadores) y clasifica cada
tramo marcado como error: «val» / «cat» si contiene una forma valenciana /
catalana del léxico, «neutra» si no, «no_trobat» si el texto no está en la
traducción (el juez a veces pone razonamiento en el tramo).

Sistemas por defecto: referencia (el valenciano del manual como
traducción), sin traducir (el catalán tal cual), AVLizador 2.0.0 y
gemma3:12b (el mejor LLM del baseline: TER más bajo y GD más alto).

```
python desglossa_frases.py
python desglossa_frases.py --sistemes referencia copia avlizador_1.1.0 ollama_gemma3-12b \
    --parells referencia:copia avlizador_1.1.0:copia
```

Salidas en `resultats/` (gitignorado; se regenera en ~30 s):

- `frases_sistemes.csv`: una fila por frase y sistema (para filtrar en Excel).
- `frases.csv`: una fila por frase, los sistemas en columnas y, por cada
  par A / B, la diferencia A − B en cada métrica y las palabras que cambian.
- `resum.md`: medias; por par, en cuántas frases cada métrica prefiere A o
  B y las 20 donde más prefiere B; dónde XCOMET y el juez ordenan los
  sistemas al revés; palabras más marcadas como error.
- `visor.html`: visor sin dependencias (subconjunto, par, métrica, orden,
  búsqueda; tramos de error de cada métrica y formas del léxico en color).

## Solo XCOMET de un sistema

`visor_xcomet.py` no necesita el juez: genera
`resultats/xcomet_<sistema>.html` con la nota de XCOMET sin referencia de
cada frase, sus tramos de error (por gravedad, con la confianza y si caen en
una forma valenciana o catalana del léxico), la referencia con las palabras
que difieren subrayadas y, desplegable, los otros sistemas con su diferencia.

```
python visor_xcomet.py                       # AVLizador 2.0.0
python visor_xcomet.py --sistema avlizador_1.1.0 --compara copia referencia
```

## Lo que falta para la 2.0.0 (Abaco)

AVLizador 2.0.0 solo tenía XCOMET con referencia. Entrada:
`../comet/entrades/avlizador_2.0.0.json` (ya en `main`).

```
cd ~/scrapeo/AVLizador && git checkout main && git pull
# XCOMET sin referencia: vuelve a puntuar todos los sistemas (unos minutos de GPU)
cd pipeline/03_seleccio_de_model/comet && MODE=qe sbatch comet.sh
# Juez: con la caché (resultats/qwen3.6-35b-a3b/cache.jsonl) solo puntúa las
# traducciones nuevas de la 2.0.0
cd ../jutge_llm && wc -l resultats/qwen3.6-35b-a3b/cache.jsonl   # ~3.506; si no existe, lo puntúa todo (horas)
sbatch --array=0 jutge_llm.sh
```

Después, en el PC:

```
scp "nmartin@abaco:~/scrapeo/AVLizador/pipeline/03_seleccio_de_model/comet/resultats/*_qe*" pipeline/03_seleccio_de_model/comet/resultats/
scp "nmartin@abaco:~/scrapeo/AVLizador/pipeline/03_seleccio_de_model/jutge_llm/resultats/qwen3.6-35b-a3b/*.json" "nmartin@abaco:~/scrapeo/AVLizador/pipeline/03_seleccio_de_model/jutge_llm/resultats/qwen3.6-35b-a3b/resum.md" pipeline/03_seleccio_de_model/jutge_llm/resultats/qwen3.6-35b-a3b/
git diff --stat pipeline/03_seleccio_de_model/comet/resultats/   # los sistemas viejos deberían salir iguales
```

## Primera lectura (con la 1.1.0 en lugar de la 2.0.0)

- Referencia / sin traducir: XCOMET prefiere el catalán en 238 frases y
  el valenciano en 125 (95 empates); el juez, 175 / 132 (151 empates).
  En las 456 frases donde el GD dice que la referencia es más valenciana,
  XCOMET le da más nota en 124 y el juez en 131.
- Tramos de error que caen en formas valencianas del léxico, en la
  referencia: XCOMET 173 de 640, el juez 425 de 893 («esta» 54, «este» 25,
  «servicis» 23, «seua» 18...). En sin traducir, sobre formas catalanas:
  XCOMET 49 de 464, el juez 202 de 641. Las dos métricas castigan más el
  valenciano normativo que el catalán.
- Fuera del léxico también caen formas valencianas (incoativos «establix»,
  «reflectix»; «conéixer», «puguen»): el GD no las cuenta como marcador,
  así que la columna «val» es un mínimo.

(Cifras de la 1.1.0 con la clasificación antigua, que no ampliaba los
trozos de palabra: el «val» real es algo más alto. Se rehacen con el
desglose completo.)

## XCOMET-XL sin referencia en AVLizador 2.0.0 (19/11/2026)

Puntuado en Abaco el 19/11 (`MODE=qe sbatch comet.sh`, 12:55). Los 14
sistemas que ya había salen idénticos (el `git diff` solo cambia fecha y
segundos): la puntuación es estable. El juez Qwen 3.6 de la 2.0.0 sigue
en cola (job 3241, 18 frases nuevas con la caché subida).

Visor: `python visor_xcomet.py` → `resultats/xcomet_avlizador_2.0.0.html`;
publicado (privado) en https://claude.ai/artifact/NP3q2LgfrV2D9Ktj3p8BSp.

### Cifras

Medias en el manual mezcla (458): sin traducir 97,04; **AVLizador 2.0.0
97,04** (BOE 97,55, AVL 96,45); 1.1.0 96,98; gemma3:12b 96,87; referencia
96,82. Frases con algún error: 279.

Frase a frase (empate = ±0,5 puntos, como `comet.sh`):

| 2.0.0 frente a | Gana 2.0.0 | Empate | Pierde |
|---|---|---|---|
| 1.1.0 | 11 | 447 | 0 |
| Sin traducir | 95 | 187 | 176 |
| Referencia | 74 | 333 | 51 |
| gemma3:12b | 132 | 159 | 167 |

- Frente a la 1.1.0 solo cambian 21 frases y no pierde en ninguna. Lo que
  más sube es la concordancia de género (BM-AVL-196 «El → La» +9,8,
  BM-BOE-135 «associades → associats» +3,8, BM-BOE-226 «totes → tots»
  +2,9). «esmentat → mencionat» (8 frases) casi no lo nota (−0,2 a +2,1);
  «esta → este» resta un poco (−0,1, −0,24).
- Tramos de error: 596 (535 leves, 59 graves, 2 críticos). **263 caen en
  una forma valenciana del léxico, 0 en una catalana**, 333 en palabras
  neutras. Las más marcadas: esta 19, servicis 14, servici 9, este 8,
  xic 5, vostés 5, tindre 4, xics 4, sigut 4, perjuí 4, estes 4, duració 4.
- De las 232 frases idénticas a la referencia, XCOMET marca algún error en
  129.
- Las peores: BM-AVL-023 53,71, BM-AVL-036 65,53, BM-AVL-015 67,39,
  BM-AVL-192 68,27, BM-AVL-012 68,95. Las dos primeras, vistas:
  - BM-AVL-023: frase metalingüística («creéssim / reportéssim»); XCOMET
    marca casi todo en los tres sistemas (2.0.0 53,71, referencia 55,13,
    sin traducir 48,49). La 2.0.0 deja «reportéssim» sin traducir.
  - BM-AVL-036: la 2.0.0 = referencia y saca 19,70 menos que sin traducir.
    Es una cita antigua de Jaume Gassull; marca «llauradors» (por
    «camperols», confianza 0,54) y «lo chafa y esclafa» (por «aixafa»).

### Cómo funciona XCOMET-XL (para explicarlo)

- Red neuronal de Unbabel (XLM-RoBERTa-XL dentro, ~3.500 M de
  parámetros) entrenada para imitar a evaluadores humanos de traducción
  (WMT: notas de calidad y errores marcados, sobre todo pares como
  inglés–alemán o chino–inglés). **No usa reglas, diccionarios ni nuestro
  léxico.**
- En modo `qe` solo recibe el original (catalán) y la traducción; la
  referencia valenciana no entra.
- Devuelve una nota de 0 a 100 y los tramos que cree errores, con
  gravedad (leve / grave / crítico) y confianza (la probabilidad que da
  el modelo de que ese trozo sea error). La nota final combina una
  estimación global de la frase con una penalización por esos errores.
- Trabaja con subpalabras («bra» + «ma»): marca cada subpalabra y los
  tramos son grupos de subpalabras seguidas. Por eso devuelve trozos de
  palabra («bra», «ció influenciar») y a veces deja el apóstrofo fuera
  («d» + «oferir…»). No da posiciones, solo el texto.
- Las etiquetas «forma valenciana / catalana / neutra» del visor no son de
  XCOMET: las ponemos nosotros después, con los marcadores del GD de la
  salida. Si el tramo es un trozo de palabra, se clasifica la palabra
  entera (desde el 19/11; antes salían 195 «val» en vez de 263).
- Por qué no sirve aquí: nunca ha visto una adaptación catalán →
  valenciano. Para él una buena traducción dice lo mismo que el original,
  así que copiar el catalán le parece casi perfecto y cada cambio
  dialectal («camperols → llauradors», «aquest → este») le parece una
  desviación. No sabe que el destino es el valenciano normativo.

### Para analizar el 20/11

1. Revisar en el visor las peores (BM-AVL-015, 192, 012, 212, 127) y las
   que la 2.0.0 pierde más frente a sin traducir (orden «Més perd»), para
   ver si hay algún error real de la 2.0.0 detrás o solo dialecto.
2. Filtrar «Tros en: forma valenciana» y contar qué formas castiga más
   (esta/este, servici(s), xic(s), vostés…) frente a la referencia.
3. Las 74 / 51 frases en que la 2.0.0 gana / pierde frente a la
   referencia: ¿la 2.0.0 deja formas catalanas («aquest», «servei») que
   XCOMET premia?
4. HECHO (20/11): juez de la 2.0.0 traído y `desglossa_frases.py`
   ejecutado; ver la sección siguiente.
5. Decidir qué se lleva a la reunión (visor, tabla y la explicación de
   arriba).

## Juez Qwen 3.6 en AVLizador 2.0.0 (20/11/2026)

Job 3241 acabado (20/11 00:03); resultados traídos de Abaco con `scp`. Los
14 sistemas que ya había salen idénticos (solo cambia la fecha): el juez
también es estable con la caché. `python desglossa_frases.py` (valores por
defecto, ~1 min) → `resultats/{frases_sistemes.csv,frases.csv,resum.md,visor.html}`.

### Medias en el manual mezcla (458)

| Sistema | XCOMET qe | Juez | GD | chrF | Iguales a la ref. | Tramos XCOMET val / cat / total | Tramos juez val / cat / total |
|---|---|---|---|---|---|---|---|
| Referencia | 96,82 | 77,00 | 0,998 | 100,00 | 458 | 239 / 0 / 640 | 426 / 0 / 893 |
| Sin traducir | 97,04 | 79,22 | 0,010 | 87,97 | 1 | 2 / 83 / 464 | 5 / 203 / 641 |
| AVLizador 2.0.0 | 97,04 | 76,60 | 1,000 | 96,34 | 232 | 263 / 0 / 596 | 449 / 0 / 924 |
| gemma3:12b | 96,87 | 78,83 | 0,360 | 87,46 | 11 | 60 / 40 / 558 | 162 / 97 / 710 |

El juez pone a la 2.0.0 igual que la 1.1.0 (76,60 frente a 76,62) y por
debajo de la referencia (77,00), sin traducir (79,22) y gemma3:12b (78,83).
En su tabla general (`../jutge_llm/resultats/qwen3.6-35b-a3b/resum.md`) los
LLM que dejan el catalán (salamandra 81,28, llama3.1 80,25, qwen3:14b 79,57)
quedan por encima de sin traducir; todos los AVLizador, abajo.

### Frase a frase (empate = misma nota exacta)

| Par | Métrica | Gana A | Empate | Gana B |
|---|---|---|---|---|
| 2.0.0 / sin traducir | XCOMET | 131 | 107 | 220 |
| | Juez | 122 | 160 | 176 |
| 2.0.0 / gemma3:12b | XCOMET | 150 | 97 | 211 |
| | Juez | 115 | 172 | 171 |
| 2.0.0 / referencia | XCOMET | 113 | 269 | 76 |
| | Juez | 61 | 330 | 67 |

(La tabla de XCOMET de la sección anterior usa empate = ±0,5 puntos; aquí
`resum.md` cuenta empate solo con la misma nota.)

- En las 231 frases en que la 2.0.0 es idéntica a la referencia y sin
  traducir no, sin traducir saca más nota en 95 (XCOMET) y 85 (juez).
- **Las dos métricas apenas coinciden entre sí**: correlación de Spearman
  XCOMET ~ juez por frase 0,27 en la 2.0.0, 0,29 en la referencia, 0,35 en
  sin traducir, 0,38 en gemma3:12b (0,33 todo junto). Solo en 242 de las
  458 frases ordenan igual los 4 sistemas (los 6 pares); en 8 frases
  invierten 5 o 6 de los 6 pares (BM-BOE-200, BM-AVL-031, 107, 181, 205,
  BM-BOE-058, 215, 230: `resum.md`, sección 3).
- Tramos del juez en la 2.0.0: 449 de 924 caen en formas valencianas del
  léxico, 0 en catalanas. Las más castigadas: esta 55, este 34, seua 26,
  servicis 24, estos 14, seues 13, estes 12, tindre 11, sigut 10. Fuera del
  léxico, también valencianas: conéixer 7, reflectix, establix, requerix,
  puguen, hagen.

### 2.0.0 frente a la 1.1.0 en el juez

Cambian 21 frases; el juez sube 5, baja 5 y deja 11 igual. Lo que baja no
son errores de la 2.0.0:

- «finalitat → fi» con la concordancia nueva («Amb este fi», «amb este
  mateix fi»; *fi* ‘finalitat’ es masculino): BM-BOE-138 65 → **45**
  (la 2.0.0 coincide con la referencia «Amb este fi», que también saca 45;
  la 1.1.0 decía «Amb esta fi», concordancia mal, y sacaba 65), BM-BOE-087
  75 → 65, BM-BOE-089 85 → 75. **El juez premia el género equivocado.**
- «esmentades → mencionades» (BM-BOE-102 75 → 65, BM-BOE-184 85 → 75); en
  otras dos frases el mismo cambio sube (BM-BOE-093 85 → 95, BM-BOE-101
  75 → 85): ruido.
- Suben: «contenir → contindre» (BM-BOE-120), «associades → associats»
  (BM-BOE-135), «quina / la seua → quin / el seu» (BM-BOE-167).

### Lectura

El juez confirma lo de XCOMET: no ve el dialecto (castiga sobre todo las
formas valencianas normativas, nunca las catalanas de la 2.0.0, porque no
hay) y en lo poco que distingue entre 1.1.0 y 2.0.0 llega a preferir una
concordancia errónea. Además, las dos métricas casi no se ponen de acuerdo
frase a frase (ρ ≈ 0,3): no son una medida estable de calidad para esta
tarea. Se quedan las medidas de superficie contra la referencia (exactas,
chrF, TER) y el GD.

## Por qué XCOMET da casi lo mismo a la referencia y a la 2.0.0 (20/11/2026)

Visor con el juez publicado (privado): https://claude.ai/artifact/2eAjUANG2eREw1nVncJV4k
(par «AVLizador 2.0.0 / Referència», «Només A ≠ B»).

Diferencia de medias: 2.0.0 97,04 − referencia 96,82 = +0,22. De dónde sale:

1. **La mitad de las frases no cuentan.** En 232 de 458 la 2.0.0 es idéntica
   a la referencia y XCOMET `qe` solo ve catalán + traducción: misma nota.
   Única excepción, BM-AVL-175 (+0,15): `referencia.json` y los sistemas del
   baseline llevan el catalán viejo («s'ha clos»); la 2.0.0, el corregido el
   05/11 («s'ha tancat»).
2. **BOE (211 de las 226 frases distintas): +0,55 de media para la 2.0.0**,
   +0,255 en la media total. La referencia del BOE es el BOE valenciano
   oficial, traducido del castellano por su lado: se aparta del catalán
   también en cosas no dialectales. Ediciones de palabras respecto al
   catalán: referencia 7,2, 2.0.0 3,9. Lo más frecuente es el futuro
   («podrà» / «pot» 20, «podran» / «poden» 7, «serà» / «és» 7, «haurà» /
   «ha» 5…: 119 frases, +0,51 de media, +0,13 en total); después,
   reformulaciones («retret» / «encongit», «realització» / «pràctica»,
   orden de palabras). La 2.0.0 solo cambia lo dialectal y deja la frase
   del catalán, y XCOMET premia quedarse cerca del original.
3. **AVL (15 frases distintas): −0,98 para la 2.0.0**, −0,03 en total.
   Casi todo es «noi / noia → xic / xica» frente a «xiquet / xiqueta» de la
   referencia (9 frases, −1,47 de media; BM-AVL-038 −6,35): XCOMET marca
   «xic» (en catalán «un xic» = «una mica»).
4. **Es casi todo ruido.** En 101 de las 226 la diferencia es ≤ 0,5;
   desviación típica de la diferencia 2,4 puntos; la correlación entre
   «cuánto más se aparta la referencia del catalán» y la diferencia de nota
   es solo 0,10 (Spearman). Los tramos de error son casi todos leves (575
   de 640 en la referencia), con confianza en torno a 0,42 (solo 7 de 596
   por encima de 0,5 en la 2.0.0) y a menudo trozos de palabra («x», «ics»,
   «ced»). Los saltos grandes son frases raras: BM-BOE-183 +22 (texto con
   corchetes), BM-BOE-054 +10,7 (la referencia mueve «que hi ha hui»).

No es dialecto: las dos son igual de valencianas (GD 1,000 / 0,998). La
diferencia viene del estilo de la referencia del BOE, que XCOMET castiga por
alejarse del catalán, y de «xic». Ningún caso apunta a un error real de la
2.0.0. Scripts del análisis: scratchpad de la sesión (`refavl/`), no se
guardan.

