*[Llegeix-ho en castellà](README.es.md)*

# BOE net — corpus depurat de soroll d'estil (02-05/10/2026)

Versions DERIVADES del corpus BOE (`../boe/`), pensades per a separar
diferències **dialectals reals** de diferències d'**estil del traductor**
(mateix text oficial, traduït dos vegades per equips distints). Els
fitxers originals de `../boe/` **no es toquen mai** -- tot el que hi ha
ací s'obté executant els scripts de `boe/` indicats baix, i es pot
regenerar sempre que calga.

## Fitxers

| Fitxer | Què és |
|---|---|
| `corpus_entrenamiento_net.jsonl` | `../boe/corpus_entrenamiento.jsonl` (260.345 de 267.962 files) menys les dos categories de soroll de baix. |
| `descartados_estilo.jsonl` | Les 7.617 files tretes, amb el motiu (`motivo_descarte`) -- mai es perden en silenci. |
| `visor_diferencias.html` + `visor_diferencias_chunks/` | Visor de les 178.416 frases amb diferència real, ordenades de MÉS a MENYS diferència -- vore baix. |

## `depurar_ruido_estilistico.py` -- les dos categories de soroll

```bash
cd ../../boe
python depurar_ruido_estilistico.py
```

Dos categories detectades amb seguretat del 100% (no calen regles
difuses, només comparar tokens normalitzats):

- **`solo_mayusculas`** (7.260 files, 2,7%): les dos frases tenen
  exactament les mateixes paraules en el mateix orde, només difereixen
  en majúscules/minúscules -- el valencià capitalitza cada paraula del
  títol d'una llei ("Llei Orgànica", "Mesures Urgents"), el català no.
  Convenció tipogràfica d'un dels dos equips, no té res a vore amb
  dialecte.
- **`reordenament_pur`** (357 files, 0,1%): mateix multiconjunt de
  paraules, orde distint -- típicament anteposició/posposició de
  l'adjectiu ("eixos següents" / "següents eixos"). Preferència d'estil
  sistemàtica, no gramàtica dialectal.

**Reanàlisi fet després de depurar** (sobre els 520 documents complets,
no només els 169 amb paràgrafs alineats que mira `analizar_corpus.py`):
83.602 parells de substitució distints, amb el top per freqüència
dominat per parells dialectals ja confirmats (`aquesta/esta` 18.784
vegades, `seva/seua` 13.727, `sigui/siga` 7.413...). Dos troballes noves
a seguir investigant:

- **`pot`→`podrà`, `és`→`serà`, `poden`→`podran`, `ha`→`haurà`** (27.000+
  instàncies juntes): NO és dialecte, és una diferència de TEMPS verbal
  (present vs. futur) -- probablement convenció de redacció legal d'un
  equip concret, no gramàtica valenciana/catalana. Candidat a una
  tercera categoria de soroll a filtrar.
- **`s'escau`→`és el cas`** (5.574 vegades): sembla elecció lèxica/
  idiomàtica real, candidata a afegir al glossari si es confirma.
- Sospitosos per paraules massa curtes/genèriques (`a`→`en`, `preveu`→
  `en`, `s'ha`→`es`): probablement mesclen casos reals amb soroll pur de
  l'algorisme de diff, revisar abans de confiar-hi.

## `generar_visor_diferencias.py` -- visor frase a frase, dos ordes

```bash
cd ../../boe
python generar_visor_diferencias.py
# despres, per a obrir-lo:
cd ../dades/boe_net
python -m http.server 8000
# -> http://localhost:8000/visor_diferencias.html
```

A diferència de `analizar_corpus.py` (nomes 169 documents) i de
`depurar_ruido_estilistico.py` (agrupa per PARELLA de paraules, no per
frase), este visor treballa a nivell de **frase completa**, sobre els
**520 documents** de `corpus_entrenamiento_net.jsonl`, amb dos pestanyes
independents (filtre i càrrega per separat en cada una):

- **"Mayor diferencia primero"** (similitud ascendent): per a trobar
  errors d'alineament reals, començant per les més sospitoses.
- **"Mayor similitud primero"** (similitud descendent, afegida
  05/10/2026): les frases quasi idèntiques llevat d'un detall -- sol ser
  el cas més net de substitució dialectal puntual (mateixa idea que
  `ratio_medio_frase` a `depurar_ruido_estilistico.py`, ara a nivell de
  frase sencera en compte de parell de paraules).

El diff resaltat de cada frase es calcula UNA sola vegada i es reutilitza
per a les dos pestanyes (només canvia l'orde en què s'escriuen els
chunks).

**Arquitectura (mateixa lliçó que el visor de `analizar_corpus.py`,
vore `../../boe/README.md`)**: amb ~178.000 frases, embeure-les totes al
HTML tornaria a disparar el pes del fitxer -- ací es parteixen en trossos
("chunks") de 1.000 frases, carregats amb `fetch()` a mesura que es fa
scroll o es prem "Carregar més" (un directori de chunks per pestanya). Per
això **cal un servidor local** per a usar-lo (no val obrir-lo fent doble
clic) -- la pròpia pàgina ho explica si `fetch()` falla.

## Pendent (acordat, no implementat encara)

- Filtrar la 3a categoria de soroll (present/futur: `pot/podrà`...).
- Confirmar `s'escau/és el cas` i afegir-lo al glossari si procedix.
- Revisar els parells de paraules massa curtes/genèriques.
- Investigar per què `es_tabla()` no agafa les taules de tarifes de
  `BOE-A-2013-13616`/`BOE-A-2012-8745` (vore `../../boe/README.md`).
- Portar les senyals de confiança dialectal a un filtre real dins
  d'`exportar_entrenamiento.py`, no només a taules d'inspecció visual.
