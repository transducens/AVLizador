*[Llegiu-lo en valencià](README.md)*

# MaCoCu-ca: frases en catalán puro (filtradas por Grau Dialectal)

Saca de **MaCoCu-ca 1.0** las frases en catalán **puro** (GD 0 con al
menos 2 marcadores orientales), para traducirlas después al valenciano
con AVLizador y obtener un corpus paralelo catalán/valenciano con el que
ajustar algún modelo (decisión del usuario, 06/11/2026). **De momento no
se traduce nada**: solo se filtra.

## El corpus

- MaCoCu-ca 1.0, CLARIN.SI, [`hdl 11356/1837`](https://www.clarin.si/repository/xmlui/handle/11356/1837),
  licencia **CC0**. Web de 2022 (dominios .cat, .es, .ad, .fr, .it,
  .eu), 5,9 M documentos, 1.737 M palabras.
- `MaCoCu-ca-1.0.xml.zip` (4,72 GB; md5 `ee39dfa0d626432ae5c44aa9071908bb`),
  15,6 GB descomprimido. El `.dtd` (3 KB) solo describe el esquema.
- Formato "prevert": `<doc>` con título, URL, dominio y fluidez; `<p>` con
  calidad jusText (`good`, `short`, `neargood`...), idioma, fluidez
  (`lm_score` 0-1, Monocleaner), si es título y si tiene datos sensibles.
  Ya vienen sin párrafos casi duplicados.
- Va en `dades/macocu/` (en el `.gitignore`, como las salidas).

**MaCoCu-ca no es solo catalán**: en una muestra de 300 párrafos buenos,
el 51 % era catalán puro, el 6 % valenciano puro (GD 1: Diputació de
Castelló, ayuntamientos...), el 17 % mezcla y el 26 % sin marcadores.

## Cómo se filtra

**Paso 1, `extreu`** (sin spaCy, una pasada; ~1 hora para todo el XML):

1. Párrafos `quality="good"`, `lang="ca"`, no título, no sensibles y
   `lm_score >= 0,7` (deja fuera el ~10 % menos fluido; `--lm-min`).
2. Frases de 8 a 40 palabras, completas, sin listas ni mayúsculas
   enteras y con pocos números (el criterio del benchmark manual,
   `construeix_pool.py`). Sin repetidas.
3. **Prefiltro de GD seguro**. spaCy solo **quita** marcadores en el GD
   (formas verbales que no son verbo, homógrafos con otra categoría),
   nunca los añade. Por tanto, una frase que sin spaCy no llega a 2
   posibles marcadores catalanes, o que tiene un marcador valenciano que
   no depende de spaCy, nunca saldrá como catalana pura, y se descarta
   antes. Primero un corte por palabras sueltas (cota superior, 2,6 M
   palabras/s) y después con el tokenizador del motor, el mismo de
   `calcula_gd` (0,3 M palabras/s).

Salida: `candidates.jsonl` y `estadistiques_extreu.json`.

**Paso 2, `gd`** (spaCy, en paralelo y reanudable): `calcula_gd(text,
dialecte="cat")` de cada candidata; se quedan las de GD 0 con al menos 2
marcadores. `--fraccio 0.2` hace una muestra uniforme y determinista (por
hash del id; la misma frase siempre entra o no) y `--maxim N` para al
llegar a N frases. Si se corta, al volver a lanzarlo sigue donde lo
dejó (`progres_gd.json`; `--reinicia` para empezar de cero).

Salida: `catala_pur.jsonl` y `estadistiques_gd.json`. Cada línea:

```json
{"id": "macocu.ca.2.3.s4", "doc": "macocu.ca.2", "domini": "tempsdeflors.girona.cat",
 "url": "https://...", "lm_score": 0.892,
 "text": "Aquesta xifra alta de visitants s'ha traduït també amb una ocupació gairebé plena...",
 "gd": 0.0, "marcadors_orientals": ["aquesta", "gairebé"], "total_paraules": 37}
```

## Uso

Desde la raíz del repositorio, con `avlizador` instalado (`pip install -e .`):

```bash
python pipeline/08_traduccio_corpus/macocu/filtra_macocu.py extreu
python pipeline/08_traduccio_corpus/macocu/filtra_macocu.py extreu --limit-mb 200   # prueba
python pipeline/08_traduccio_corpus/macocu/filtra_macocu.py gd --processos 6
python pipeline/08_traduccio_corpus/macocu/filtra_macocu.py gd --processos 6 --fraccio 0.2
```

Si no está el XML descomprimido, el script lo lee directamente del
`.zip` (no hacen falta los 15 GB).

### En Abaco

`filtra_macocu.sh` (solo CPU, 16 núcleos, 32 GB, 24 h) hace los dos
pasos; el GD usa un proceso por núcleo menos uno. Si se acaba el tiempo,
relanzarlo continúa donde lo dejó. Instrucciones (descargar el `.zip` con
`wget` en Abaco y lanzar con `sbatch`) en la cabecera del script.

```bash
sbatch filtra_macocu.sh                  # todas las candidatas
FRACCIO=0.2 sbatch filtra_macocu.sh      # muestra del 20 %
```

## Mediciones (06/11/2026, portátil, 8 núcleos)

- **Prefiltro seguro, comprobado**: de 4.000 frases válidas, pasan 521
  (13 %); el GD exacto da 461 catalanas puras (88 % de las que pasan) y
  **ninguna** catalana pura queda fuera por el prefiltro.
- **Paso 1** con los primeros 200 MB: 485.514 párrafos → 226.023 buenos
  → 521.168 frases válidas → **63.031 candidatas**, en 49 s. Para el XML
  entero: ~1 hora y unos 5 M de candidatas.
- **Paso 2** con 6 procesos: ~90-100 candidatas/s (4.000 en 46 s, con el
  arranque de spaCy); el 86 % son catalanas puras. Todas las candidatas:
  ~13-15 h; con `--fraccio 0.2`, ~3 h.

## Límites

- El separador de frases no trata abreviaturas ("Sr.", "núm."): la frase
  cortada acaba sin punto o empieza en minúscula y la descarta el filtro.
- Una web puede aportar muchas frases (`estadistiques_extreu.json` lista
  los 30 dominios con más candidatas). Si hace falta, se limita por
  documento o dominio al muestrear para traducir.
- El GD tiene sus errores conocidos ("finalitat", colisiones verbales
  como "permet"): ver `documentacio/resultats_gd_gdv_gdc.md`.
