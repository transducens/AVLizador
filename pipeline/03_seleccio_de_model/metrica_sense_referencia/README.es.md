# Métrica sin referencia para cat→val (tipo CometKiwi)

Las métricas existentes (XCOMET, CometKiwi) penalizan formas valencianas
correctas («tindre», «este», «xiquet», «ací») porque su norma implícita es el
catalán central (ver `../comet/README.md`). Aquí se construye una métrica
sin referencia (src catalán + salida → nota) que aprenda lo contrario: las
formas del léxico de AVLizador en catalán son errores en la salida
valenciana.

Trabajo por fases (decisión del usuario, 18/11/2026): 1 exploración, 2
corpus sintético (esta carpeta), 3 entrenamiento (`ReferencelessRegression`
de unbabel-comet, xlm-roberta-large, Abaco), 4 meta-evaluación en el
benchmark manual.

## Fase 2: corpus sintético

Decisiones del usuario:

- **Nada de evaluación en el entrenamiento**: fuera las frases (exactas y
  casi iguales, Jaccard ≥ 0,6) del manual, homógrafos v1/v2, el 151,
  gplsi, el benchmark de género y la muestra de `boe_net`; los BOE estricto
  y amplio completos (están publicados en Hugging Face) y la mostra de
  2.000; y las líneas del BOE de las que sale el manual (`id_origen`).
  `--exclou-documents` quita además los documentos enteros del manual.
- **Ninguna salida de AVLizador** en el entrenamiento.
- **Evaluación estricta del léxico**: toda forma catalana del léxico en la
  salida es un error, aunque la norma AVL la admita («aquest», «servei»).
- **Positivos**: valenciano con GD = 1 y al menos 2 marcadores; el catalán,
  sin ningún marcador valenciano y al menos uno catalán.
- **Tipo 3** (error de sentido): frases del corpus y frases escritas a mano
  (`homografs_creats.json`) para cubrir todas las formas y lecturas.
- **Reserva del 20 % del léxico** por familia y estratificada por
  frecuencia, para el test de circularidad.

Pasos:

```
python prepara_positius.py --processos 6   # positius.jsonl, homografs_corpus.jsonl
python prepara_lexic.py                    # famílies i reserva (lexic_parells.json)
python genera_corpus.py                    # train/val/test.csv + test_circularitat.csv
python genera_corpus.py --sense-reserva    # el mismo sin reserva (modelo final), en complet/
```

Las salidas van a `dades/metrica_sense_referencia/` (gitignorado).

| Tipo | mt | score |
|---|---|---|
| 0 positivo | el valenciano | 0,9 |
| 1 sin traducir | el src tal cual | 0,1 |
| 2 dialecto parcial | 10/30/60/100 % de los marcadores en catalán | 0,5 → 0,2 según la fracción real |
| 3 error de sentido | homógrafo con la lectura equivocada | 0,1 |
| 4 mezcla | bloques alineados del src o del mt al azar | 0,3 |

### Resultado (18/11/2026)

Positivos: **22.910** (BOE 22.085, AVL sintético 825) de 267.962 líneas
del BOE y 28.049 pares realineados de la AVL. Exclusiones del BOE: 37.628
frases de evaluación, 819 casi iguales y 250 líneas del manual.

| Versión | train | val | test | nota media |
|---|---|---|---|---|
| Con reserva (para el test de circularidad) | 55.547 | 8.187 | 8.270 | 0,50 |
| Sin reserva (`complet/`, modelo final) | 71.248 | 10.555 | 10.608 | 0,41 |

Filas de train sin reserva: positivos 18.313, sin traducir 17.311,
dialecto parcial 17.485, error de sentido 969, mezcla 17.170. Con reserva
el tipo 1 baja a 4.803: la familia de «este» quedó reservada en el sorteo
(semilla fija) y su forma catalana sale en la mayoría de frases.

Reserva: 1.161 familias de 5.801 (5.520 formas), estratificada. Entre las
reservadas: este/esta/estos/estes, eixe…, el subjuntivo de «ser» (siga,
fóra…), orde, desenrotllament, duració, xicotet. `test_circularitat.csv`:
3.967 frases × (original, reservadas en catalán) + 2.549 de control, con
42 familias reservadas.

Tipo 3 del corpus (forma:lectura, antes del tope de 300): nou compartida
1.074, nous compartida 550, deu compartida 594, manca dialectal 105, cop
vegada 33 / colp 9, y casos sueltos; las 168 frases creadas cubren las 20
formas y todas sus lecturas.

### Detalles

- **Pares del léxico**: los mismos cargadores que el GD y el traductor,
  solo las formas que sobreviven a los filtros del GD (ambigüedades,
  colisión verbal, homógrafos irresolubles). Los marcadores de una frase
  los da el GD con spaCy (las formas verbales que coinciden con nombres,
  «persones»→«personis», solo cuentan si spaCy dice verbo).
- **Sustitución**: de derecha a izquierda y sobre la forma ya cambiada,
  con las funciones de elisión del motor (artículo, «de», contracciones) y
  el género del léxico («l'eixida» → «la sortida», «d'este gasto» →
  «d'aquesta despesa»).
- **Familias**: formas de un mismo infinitivo, entradas con la misma glosa
  castellana sin plural ni género, y formas que comparten la valenciana o
  la catalana. La frecuencia para estratificar es la de los marcadores en
  los positivos.
- **Reserva**: las formas reservadas nunca aparecen como error en el `mt`
  del entrenamiento (no se catalanizan, no se mezclan, no hay tipo 1 si
  el src las lleva); sí pueden aparecer en valenciano en los positivos.
  `test_circularitat.csv` (de validación y test): original, solo las
  reservadas en catalán, y de control el mismo número de no reservadas.
  El modelo que se entrena con reserva sirve para el test; para el modelo
  final, `--sense-reserva`.
- **Homógrafos**: las 20 formas catalanas ambiguas del léxico (nou, nous,
  deu, manca, manques, cop, cops, reeixida(es), rentadora(es),
  recuita(es), calces, gandula(es), panotxa(es), fartanera(es)). «sota»
  queda fuera: su valenciano tiene dos palabras («davall de») y el DOGV dice
  «sota» 580 veces frente a 783 «davall».
- **Corpus sintético de la AVL**: desde la línea 17.172 el catalán tiene
  restos del LLM («/no_think», «</think>») y las columnas se desplazan; se
  realinea con una ventana (`realinea_sintetic`).

## Fase 3: entrenamiento (Abaco)

`configs/referenceless_complet.yaml` (modelo final, corpus sin reserva) y
`configs/referenceless_reserva.yaml` (solo para el test de circularidad),
para unbabel-comet 2.2.7 (pytorch-lightning 2): `ReferencelessRegression`,
xlm-roberta-large, fp16 (`16-mixed`; las 2080 Ti no tienen bf16), lote 8 ×
acumulación 4 = 32, `encoder_learning_rate` 1e-5, `learning_rate` 1,5e-4,
`nr_frozen_epochs` 0,3, embeddings congelados, hasta 5 épocas con
validación cada media época y parada temprana por `val_pearson`
(paciencia 3 = 1,5 épocas). Se guarda el mejor checkpoint.

`entrena_metrica.sh` usa el venv de XCOMET (`~/venvs/comet`), comprueba la
GPU y los datos, y registra la memoria de la GPU cada minuto. Con `PROVA=1`
hace 200 lotes con el encoder descongelado desde el principio para medir
el pico de memoria.

```
# En el PC: subir los datos (unos 100 MB)
ssh nmartin@abaco "mkdir -p ~/scrapeo/AVLizador/dades/metrica_sense_referencia/complet"
scp dades/metrica_sense_referencia/{train,val,test,test_circularitat}.csv nmartin@abaco:scrapeo/AVLizador/dades/metrica_sense_referencia/
scp dades/metrica_sense_referencia/complet/{train,val,test}.csv nmartin@abaco:scrapeo/AVLizador/dades/metrica_sense_referencia/complet/

# En Abaco
cd ~/scrapeo/AVLizador && git fetch && git checkout metrica-sense-referencia && git pull
cd pipeline/03_seleccio_de_model/metrica_sense_referencia && mkdir -p logs
PROVA=1 sbatch entrena_metrica.sh               # primero la prueba
sbatch entrena_metrica.sh                       # modelo final
VARIANT=reserva sbatch entrena_metrica.sh       # modelo del test de circularidad
```

Salida: `models/<variante>/lightning_logs/version_N/` (`hparams.yaml`,
`checkpoints/*.ckpt`, `metrics.csv`), la estructura que espera
`comet.load_from_checkpoint`.
