# Clasificador fastText valenciano/catalán

*(Versión en valenciano: [README.md](README.md).)*

Primer paso (10/11/2026) para probar [fastText](https://fasttext.cc/)
como sustituto de FLOR en la decisión de las palabras ambiguas
(`model_llengua/`), junto con los dos KenLM (catalán y valenciano; ver
`../kenlm/`).

## Qué es y cómo se usará

fastText **no es un modelo de lenguaje**: no da la probabilidad de una
frase, sino un **clasificador** de textos. Aquí aprende dos clases,
`val` y `cat`, a partir de palabras, pares de palabras (`-wordNgrams 2`)
y trozos de 3 a 5 letras (`-minn 3 -maxn 5`; sirven para terminaciones
como "-isca/-eixi" o "-ix/-eix" aunque la palabra no esté en el
entrenamiento).

En la traducción se usará igual que FLOR: el motor genera las frases
valencianas completas de cada candidato ("Un altre colp..." / "Una altra
vegada..."), fastText da a cada una la probabilidad de ser valenciana y
gana la más alta, con el mismo `Criteri` (margen y catalana por defecto)
para poder compararlos. Es muy rápido en CPU (milisegundos por frase) y
el modelo comprimido (`.ftz`) ocupa pocos MB.

**Límite**: mide "cuánto suena a valenciano", no el sentido. Como las
clases salen de los marcadores del GD, aprende sobre todo el propio
léxico: en un homógrafo ("calces") tenderá a preferir la forma
dialectal, sea cual sea el sentido. Eso es lo que hay que medir.

## Datos

`prepara_dades.py` (salida en `dades/macocu/fasttext/`):

| Clase | Origen | Criterio |
|---|---|---|
| `cat` | `dades/macocu/catala_pur.jsonl` (4,49 M frases) | GD 0 con ≥ 2 marcadores (`../catala/`) |
| `val` | `dades/macocu/valencia/valencia.jsonl` | GD ≥ `--gd-val` (1,0) con ≥ `--min-marcadores` (2) occidentales |

- El valenciano con un solo marcador es casi siempre catalán normal con
  un falso marcador ("vegada", "permet", "alcalde"): por eso el criterio
  es el del catalán al revés. En una muestra (300 MB del XML), pasan
  5.006 de 47.624 frases valencianas; en MaCoCu entero, unas 280.000.
- Mismo número de frases por clase (el catalán, muestreado al azar con
  semilla 13) y 10.000 por clase para validar.
- Fuera las frases de los benchmarks (manual, homógrafos v1/v2, 151).
- Texto normalizado como el de KenLM (`../kenlm/exporta_text.normalitza`):
  minúsculas, apóstrofo separado, números a "0", puntuación separada. La
  misma función hay que aplicarla a las frases que se clasifiquen.

## En Abaco

Una vez, compilar fastText (solo hace falta `make` y `g++`; el paquete
`fasttext-wheel` no tiene versión para Python 3.13):

```bash
cd ~ && git clone https://github.com/facebookresearch/fastText.git && cd fastText && make
./fasttext 2>&1 | head -3      # comprobar
```

Cuando haya terminado el filtro valenciano (`../valencia/`):

```bash
cd ~/scrapeo/AVLizador/pipeline/08_traduccio_corpus/macocu/fasttext
sbatch entrena_fasttext.sh                   # hiperparámetros fijos
AUTOTUNE=600 NOM=autotune sbatch entrena_fasttext.sh   # o que los busque 10 min
```

El job (4 CPU, 8 GB, 3 h como máximo; se espera menos de 30 min) prepara
los datos, entrena (`classificador.bin`), lo prueba en `valid.txt`
(precisión y cobertura por clase), lo comprime (`classificador.ftz`) y
da la probabilidad de cada clase para los pares de prueba (la misma
frase en catalán y en valenciano). Salida: `<jobid>_fasttext.out`.

Variables: `NOM`, `PREPARA` (opciones de `prepara_dades.py`, p. ej.
`PREPARA="--min-marcadors 1 --gd-val 0.75"`), `REINICIA=1` (volver a
preparar los datos), `AUTOTUNE` (segundos), `DIM` (50), `EPOCH` (10),
`LR` (0,5), `NGRAMS` (2), `MINN`/`MAXN` (3/5).

## Siguiente paso

Comparar FLOR, KenLM catalán (gana el candidato menos probable), KenLM
valenciano (gana el más probable) y fastText en los homógrafos v1/v2 y el
manual, con todas las métricas (exactas, BLEU, chrF, TER, WER, GD/GDV de
la salida), el acierto en las palabras ambiguas, y el tiempo y la memoria
en CPU.
