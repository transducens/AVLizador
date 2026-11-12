*[Llegiu-lo en valencià](README.md)*

# MaCoCu-ca: corpus web catalán, filtrado por Grau Dialectal

Trabajo con **MaCoCu-ca 1.0** para tener datos de entrenamiento:
frases catalanas puras traducidas al valenciano (corpus paralelo) y
frases valencianas reales del propio corpus, y un primer KenLM con todo
el corpus para sustituir a FLOR (decisiones del usuario, 06/11 y
09/11/2026).

## Estructura

| Carpeta / fichero | Qué hay |
|---|---|
| [`comu.py`](comu.py) | Lectura del XML (o del `.zip`), párrafos, frases, frase válida y párrafo bueno; lo usan todos |
| [`catala/`](catala/README.es.md) | `filtra_macocu.py` (GD 0, catalán puro) y `tradueix_macocu.py` (traducción con AVLizador), con sus `.sh`, la calidad de los datos y las decisiones |
| [`valencia/`](valencia/README.es.md) | `filtra_valencia.py` (GD > 0,5, formas valencianas) y su `.sh` |
| [`analitza_macocu.py`](analitza_macocu.py) | Análisis del corpus entero sin filtrar (GD y palabras del léxico) |
| [`kenlm/`](kenlm/README.es.md) | KenLM con todo MaCoCu sin filtrar (primera prueba) |

Datos (fuera de git): `dades/macocu/` (corpus y salidas del catalán),
`dades/macocu/valencia/` y `dades/macocu/kenlm/`.

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

## Análisis del corpus entero sin filtrar (`analitza_macocu.py`, 09/11/2026)

Petición del usuario: se quiere entrenar con todo MaCoCu (primera prueba,
KenLM en `kenlm/`), así que hay que saber cuánto catalán y cuánto
valenciano tiene y cuántas veces salen las palabras problemáticas.
Tres pasos: `recompte` (una pasada por el XML, sin spaCy, 20 min en el
portátil con 6 procesos), `gd` (GD de cada frase de una **muestra del 2 %
de los documentos**, 118.500 documentos y 1.807.629 frases, 53 min) e
`informe` (`dades/macocu/analisi_macocu.{json,md}`).

```bash
python pipeline/08_traduccio_corpus/macocu/analitza_macocu.py recompte --processos 6 --fraccio 0.02
python pipeline/08_traduccio_corpus/macocu/analitza_macocu.py gd --processos 6
python pipeline/08_traduccio_corpus/macocu/analitza_macocu.py informe
```

### El corpus

5.939.710 documentos, 43.945.726 párrafos (good 24,8 M, short 11,9 M,
neargood 4,6 M, otros 2,6 M; 8,7 M títulos), 89.891.455 frases y
**1.772,5 M de palabras** (1.613,8 M en párrafos `good` en catalán).

### Grau Dialectal (muestra del 2 %)

GD sin `dialecte`: frase sin marcadores = sin GD.

| Subconjunto | Frases | GD global | GDV | GDC | Sin marcadores | GD 0 | (0, 1) | GD 1 | GD 0 / 1 con ≥2 marcadores |
|---|---|---|---|---|---|---|---|---|---|
| Todo | 1.807.629 | 0,185 | 0,976 | 0,995 | 63,4 % | 27,9 % | 3,6 % | 5,1 % | 8,2 % / 0,69 % |
| Párrafos buenos | 1.361.156 | 0,181 | 0,975 | 0,995 | 55,1 % | 34,4 % | 4,6 % | 5,9 % | 10,5 % / 0,86 % |
| Filtro (`filtra_macocu`) | 880.784 | 0,174 | 0,974 | 0,994 | 52,3 % | 37,3 % | 4,1 % | 6,3 % | 10,3 % / 0,78 % |

Por documento (suma de marcadores de sus frases de la muestra): sin
marcadores 19,3 %, GD 0 36,5 %, (0, 0,25) 21,8 %, [0,25, 0,5) 11,1 %,
[0,5, 0,75) 6,1 %, [0,75, 1) 1,3 %, GD 1 4,0 %. Documentos claramente
valencianos (≥5 marcadores y GD ≥ 0,75): **1.799 de 118.500 (1,5 %)**,
unos 90.000 en todo el corpus.

**El GD 1 está inflado.** Las 92.305 frases de GD 1 de la muestra (5,1 %)
son en gran parte falsos marcadores conocidos del GD, palabras que
también son catalán normal: vegada/vegades, permet, alcalde, últim*, fem,
investigació, falta, quasi, consideren, naixement... Solo **53.787 (58 %)
tienen algún marcador valenciano "fuerte"** (seua, esta/este/estos,
sigut, siga, ací, tindre, hui, xiquets, eixe/eixos, meua, haja, puga,
vesprada...) y solo **7.894 (0,44 % de la muestra) tienen dos o más**.
Por TLD, el más valenciano es `.es` (GD 0,339) y luego `.com` (0,212);
`.cat` 0,151. Dominios más valencianos (≥50 marcadores):
infoguiavalencia.com, viupaterna.es, lenciclopedia.org,
diccionarivalencia.com, valenciaplaza, levanteud.com, valenciadiari.com,
benidorm.org, fallas.com, memoriacastello.cat...

**Lectura**: MaCoCu es catalán oriental con un poco de valenciano. Con
los marcadores fiables, el valenciano real ronda el 3 % de las frases
(~2,7 M en todo el corpus si se escala la muestra) y el valenciano claro
(≥2 marcadores fuertes) el 0,4 % (~400 mil). Entrenar con todo es
entrenar con catalán.

### Palabras del léxico (corpus entero, forma escrita, sin mirar el sentido)

Las que decide FLOR:

| Catalán | n | Valenciano | n |
|---|---|---|---|
| cop | 596.367 | colp / vegada | **6.789** / 615.471 |
| cops | 74.735 | colps / vegades | 2.471 / 372.566 |
| nou | 1.176.761 | anou | **237** |
| nous | 445.806 | anous | **656** |
| deu | 272.267 | brollador | 1.610 |
| manca / manques | 131.939 / 843 | falta / carències | 214.490 / 3.296 |
| rentadora(es) | 7.788 / 2.166 | llavadora(es) | 168 / 46 |
| calces | 3.379 | bragues | 275 |
| gandula(es) | 691 / 1.899 | hamaca(ques) | 1.392 / 1.656 |
| panotxa(es) | 619 / 278 | panolla(es) | 98 / 82 |
| reeixida(es) | 5.175 / 2.145 | exitosa(es) | 6.679 / 2.052 |

Las formas valencianas que importan para decidir son rarísimas: "colp"
sale 88 veces menos que "cop", "anou" 237 veces frente a 1,2 M de "nou".
Un KenLM entrenado solo con MaCoCu casi no las ha visto. (Vegada, falta,
hamaca o exitosa son también catalán normal: sus cifras no miden
valenciano.)

Por grupo de `problema` (suma de formas; hay formas compartidas, como
"fins" preposición, "després" adverbio o "mentre", que inflan el lado
valenciano): cambio de género 99 entradas, catalán 3,55 M / valenciano
4,25 M; colisión 44, 4,16 M / 1,67 M (nens 341 mil / xiquets 64 mil,
aquí 743 mil / ací 70 mil, batlle 27 mil / alcalde 315 mil); homonimia
léxica 29, 2,72 M / 4,87 M. Tabla completa, entrada a entrada, en
`dades/macocu/analisi_macocu.md`. Cambio de género con más casos:
habitatge(s) 349 mil / vivenda(es) 24 mil, ensenyament 139 mil /
ensenyança 6,5 mil, escombraries 21 mil / fem 259 mil (verbo "fer").
