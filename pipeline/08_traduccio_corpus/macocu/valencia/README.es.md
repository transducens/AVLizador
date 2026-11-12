*[Llegiu-lo en valencià](README.md)*

# MaCoCu-ca: frases con formas valencianas (GD > 0,5)

Saca de **MaCoCu-ca 1.0** las frases con formas valencianas: **GD > 0,5**
(más marcadores occidentales que orientales), para tener valencià real
del corpus (decisión del usuario, 09/11/2026). Servirá, por ejemplo, para
que el KenLM vea "colp", "anou", "seua", "este"... que en MaCoCu son muy
raras (ver el análisis en el [README de `macocu/`](../README.es.md)). Es
el filtro simétrico del catalán ([`../catala/`](../catala/README.es.md)) y
comparte con él la lectura del corpus ([`../comu.py`](../comu.py)).

## Cómo se filtra

**Paso 1, `extreu`** (sin spaCy, una pasada por el XML):

1. Los mismos párrafos y frases que el filtro catalán: `good`, `lang="ca"`,
   no título, no sensibles, `lm_score >= 0,7`; frases de 8 a 40 palabras,
   completas, sin repetidas.
   - Los párrafos en castellano (`lang="es"`) quedan fuera a propósito:
     "este", "esta", "alcalde", "vos" son marcadores valencianos y
     también castellano (en la muestra del análisis, 2.703 frases `es`
     salían con GD > 0,5).
   - El `lm_score` (Monocleaner, un modelo de catalán) castiga un poco el
     valenciano: el 6,5 % de las frases con GD > 0,5 quedan por debajo de
     0,7, frente al 2 % de las catalanas puras. Mirado a mano, lo que
     quita es basura (castellano, wiki sin limpiar, letras que faltan),
     así que se deja el mismo umbral.
2. **Prefiltro seguro**. spaCy solo **quita** marcadores en el GD, nunca
   los añade. Sin spaCy se calcula una cota superior de los occidentales
   (todos los posibles) y una inferior de los orientales (léxico simple
   que no es homógrafo, los que no dependen de spaCy). Si la cota superior
   no llega al mínimo de marcadores o no supera a la inferior oriental, el
   GD exacto nunca puede ser > 0,5 y la frase se descarta sin perder nada.

Salida: `dades/macocu/valencia/candidates.jsonl` y `estadistiques_extreu.json`.

**Paso 2, `gd`** (spaCy, en paralelo y reanudable): `calcula_gd(text)`;
se quedan las de GD > `--min-gd` (0,5) con al menos `--min-marcadores`
(1). Si se corta, al relanzarlo sigue donde lo dejó (`--reinicia` para
empezar de cero).

Desde el 10/11/2026 va unas 3 veces más rápido con el mismo resultado
(salida idéntica byte a byte a la de `calcula_gd` en 64.064 candidatas):
spaCy solo pasa por las frases con alguna palabra que lo necesita (formas
verbales y homógrafos, ~80 %) y por lotes (`nlp.pipe`) en vez de una
llamada por frase. Medido en local: 187 → 583 frases/s con 1 proceso,
395 → 552 frases/s con 4. El `.sh` lanza un proceso por CPU.
El paso 1 (`extreu --processos N`) también va en paralelo: el proceso
principal lee el XML (~5 % del tiempo) y los trabajadores hacen el
prefiltro; misma salida y mismas estadísticas (comprobado en 150 MB),
1,7 veces más rápido con 4 procesos (600 MB: 136 → 81 s).

Salida: `dades/macocu/valencia/valencia.jsonl` y `estadistiques_gd.json`.
Cada línea guarda los marcadores, para poder filtrar después sin volver a
pasar spaCy:

```json
{"id": "macocu.ca.1.2.s1", "doc": "macocu.ca.1", "domini": "transparencia.dipcas.es",
 "url": "https://...", "lm_score": 0.924,
 "text": "Però este espai no s'ha fet només per a parlar nosaltres, també volem escoltar-te a tu...",
 "gd": 1.0, "occ": 2, "ori": 0, "marcadors_occidentals": ["este", "este"],
 "marcadors_orientals": [], "total_paraules": 26}
```

## Uso

```bash
python pipeline/08_traduccio_corpus/macocu/valencia/filtra_valencia.py extreu
python pipeline/08_traduccio_corpus/macocu/valencia/filtra_valencia.py extreu --limit-mb 200   # prueba
python pipeline/08_traduccio_corpus/macocu/valencia/filtra_valencia.py gd --processos 6
```

En Abaco (solo CPU, 16 núcleos, 32 GB; desde esta carpeta):

```bash
sbatch filtra_valencia.sh
MIN_MARCADORS=2 REINICIA=1 sbatch filtra_valencia.sh   # más exigente, desde cero
```

## Mediciones (09/11/2026, portátil)

- **Prefiltro comprobado**: en 26.412 frases válidas al azar de la
  muestra del análisis, pasan 4.341 (16,4 %); el GD exacto da 1.740 con
  GD > 0,5 y **ninguna** queda fuera por el prefiltro.
- **Primeros 100 MB**: 265.678 párrafos → 118.740 buenos → 261.804
  frases válidas → 43.090 candidatas (29 s) → **18.119 frases con GD >
  0,5** (6,9 % de las válidas; GD en 148 s con 6 procesos). Para el XML
  entero: unos 7 M de candidatas y unos **3 M de frases**; en Abaco, ~1 h
  y 20 min el paso 1 y ~1-2 h el paso 2 (el filtro catalán hizo 5,2 M en
  54 min con 15 procesos).
- **Ojo con los falsos marcadores**: el 83 % de las frases seleccionadas
  tienen un solo marcador occidental, y los más frecuentes son en buena
  parte palabras que también son catalán normal: vegada (1.099),
  vegades (782), fem (492), permet (442), últim (365), falta (358),
  alcalde (273), quasi (254)... junto a marcadores claros como seua
  (700), esta (373), sigut (275), ací (212). Con 2 marcadores o más
  quedan 2.995 de 18.119 (17 %). También cuela alguno raro ("bla bla
  bla"). Antes de usarlas, decidir el criterio (por ejemplo, ≥2
  marcadores o excluir los falsos marcadores conocidos del GD, ver
  `documentacio/resultats_gd_gdv_gdc.md`).

## Análisis de la salida (10/11/2026)

`analitza_valencia.py` lee `valencia.jsonl` (sin spaCy: cada frase ya trae
sus marcadores) y escribe `dades/macocu/valencia/analisi_valencia.md` y
`.json`: frases por número de marcadores valencianos y cuántas llevan
también alguno catalán, marcadores más frecuentes (en total y en las
frases de un solo marcador, donde están los falsos), dominios y TLD,
longitud, `lm_score` y ejemplos al azar de cada grupo.

```bash
srun --mem=4000M python pipeline/08_traduccio_corpus/macocu/valencia/analitza_valencia.py
```
