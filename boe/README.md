*[Llegeix-ho en castellà](README.es.md)*

# Scraper del BOE en català i valencià

Descarrega de forma ètica i respectuosa el corpus lingüístic de documents
del BOE (Boletín Oficial del Estado) que tenen **traducció oficial** al
català o al valencià, publicats com a "suplement en llengua catalana/
valenciana" a boe.es.

## Resum del procés (3 fases, ja completades)

El scraping va acabar el 2026-09-10 (log: "Finalizado") i el corpus ja no
crix més: 521 PDF en cada idioma, 2009-2015. A partir d'ahí, tres fases:

**1. Scraping** (`scraper_boe.py`) — descarrega només els PDF amb
traducció oficial real (classe `puntoPDFsup`), respectant `robots.txt` i
amb ritme de cortesia (8s-2min d'espera entre peticions). Detalls i
xifres de temps en ["Troballes importants"](#troballes-importants-llig-ho-abans-dexecutar)
i ["Cortesia amb el servidor"](#cortesia-amb-el-servidor-per-què-trigarà-diversos-dies)
més avall. Eixida: `../dades/boe/{catalan,valenciano}/<any>/BOE-*.pdf`.

**2. Extracció** (`construir_corpus.py`) — text de cada PDF a nivell de
**paràgraf real** (bloc de PyMuPDF, amb info de font per a fusionar
correctament paràgrafs tallats per salts de pàgina sense confondre
títols en cursiva amb cos de text — vore
["Construcció del corpus"](#construcció-del-corpus-per-a-estudi) més
avall per al perquè exacte). Eixida: `../dades/boe/corpus.json`, 45,5M/45,4M
caràcters, 6,83M/6,80M paraules (català/valencià).

**3. Alineació** (`alinear_corpus_bleualign.py`, amb `texto_comun.py`) —
per similitud de text amb [Bleualign](https://github.com/rsennrich/Bleualign)
en lloc de per coincidència exacta de recompte (açò descartava documents
sencers per una sola discrepància). Abans s'exclouen els paràgrafs
tabulars (pressupostos/aranzels/formularis, `texto_comun.es_tabla`) per a
no embrutar l'alineació. Eixida: `../dades/boe/corpus_bleualign.jsonl`,
**302.977 parells de frase** (94,0% de cobertura sobre les frases en
català després d'excloure taules, similitud mitjana 0,71).
Detall complet en
["corpus_bleualign.jsonl"](#corpus_bleualignjsonl-alineació-per-similitud-no-per-posició)
més avall.

Sobre açò, dos ferramentes més: `analizar_corpus.py` genera un informe
HTML d'anàlisi/QA del corpus (vocabulari dialectal, morfologia, diff
textual, i la mateixa alineació de Bleualign — vore més avall, secció
"Analítica del corpus"); i
`exportar_entrenamiento.py` filtra `corpus_bleualign.jsonl` a un
subconjunt net per a entrenar (`corpus_entrenamiento.jsonl`, 268.735
parells, 88,7%) — vore el seu docstring per a la regla de dos nivells
usada (un únic llindar de similitud no basta: hi ha parells dialectals
correctes de similitud molt baixa que no cal perdre).

## Troballes importants (llig-ho abans d'executar)

Abans d'escriure el scraper es va inspeccionar `robots.txt` i l'estructura
real de les pàgines de boe.es. Dos coses canvien el que és possible/
raonable descarregar:

1. **`robots.txt` prohibix explícitament** `/diario_boe/txt.php?*lang=ca`,
   `?lang=va`, i `/diario_boe/xml.php?` (el text pla/XML del document en
   llengua cooficial). El scraper respecta açò i **mai** sol·licita eixes
   rutes. Per tant, el corpus només pot construir-se a partir dels
   **PDF** enllaçats al sumari diari — no hi ha drecera de text pla.

2. Al sumari de cada dia, cada document té un enllaç a PDF amb dos
   variants possibles:
   - `<li class="puntoPDF">` → el PDF **en castellà** (el document no
     té traducció; el sumari l'enllaça igualment a manera de
     referència).
   - `<li class="puntoPDFsup">` → el PDF **realment traduït**, amb
     nom de fitxer `BOE-X-YYYY-NNNNN-C.pdf` (català) o `...-V.pdf`
     (valencià).

   El scraper **descarrega únicament el segon tipus**. Açò és intencional:
   només una part dels documents publicats cada dia (sobretot Lleis,
   Reials Decrets Legislatius i Reials Decrets-llei) reben traducció
   oficial; la majoria d'Ordres/Resolucions mai la tenen. El corpus
   resultant serà molt més xicotet que "tot el BOE d'eixe any" — és
   normal que molts dies no aporten cap document.

3. `robots.txt` també bloqueja, un a un, diversos centenars de PDF
   concrets (per causes legals/de privacitat alienes a este projecte). El
   scraper carrega `robots.txt` una vegada a l'inici i comprova **cada
   URL** (calendari, dia i document) contra eixes regles abans de
   sol·licitar-la, amb un matcher propi que sí interpreta els comodins
   `*`/`$` (es va comprovar que `urllib.robotparser` de la llibreria
   estàndard de Python **no** els interpreta bé i hauria deixat passar
   peticions que `robots.txt` demana bloquejar).

## Instal·lació

```bash
pip install -r requirements.txt
```

## Ús

Execució completa (català 2001–2025, valencià 2001–2015):

```bash
python scraper_boe.py
```

Només un idioma i/o rang d'anys:

```bash
python scraper_boe.py --idiomas catalan --anio-desde 2010 --anio-hasta 2015
```

Prova ràpida (es para després de N documents descarregats, sense esperar
dies):

```bash
python scraper_boe.py --max-documentos 3 --verbose
```

El scraper és **reprenible**: es pot interrompre (Ctrl+C) i tornar a
llançar-lo amb el mateix comandament; reprendrà justament on ho va deixar
gràcies a `../dades/boe/progreso.json` (dies ja processats i documents ja
descarregats no es tornen a demanar). Un dia només es marca com a
completat si **tots** els seus documents es van descarregar correctament;
si algun falla o es talla l'execució a mitges, eixe dia es reintenta en la
següent execució.

## Eixida

```
../dades/boe/
├── progreso.json          # registre de represa
├── scraper.log             # log complet amb timestamp, URL i status code
├── catala/
│   ├── 2001/
│   │   └── BOE-A-2001-XXXXX-C.pdf
│   └── ...
└── valencia/
    ├── 2001/
    │   └── BOE-A-2001-XXXXX-V.pdf
    └── ...
```

`progreso.json` guarda també metadades per document (títol en l'idioma
corresponent, data, URL origen) — útil per a catalogar el corpus després.

## Cortesia amb el servidor (per què trigarà diversos dies)

Tot el trànsit és seqüencial (una sola petició a la vegada, sense fils ni
async), amb sessió persistent, User-Agent realista rotat entre 5
navegadors, capçaleres completes (Accept, Accept-Language, Referer),
reintents amb backoff exponencial (30s/60s/120s) davant de 429/503/
timeout, i una pausa de 10 minuts si el servidor seguix retornant error
després d'esgotar els reintents. Els temps d'espera aplicats són:

| Entre...      | Espera aleatòria |
|---------------|-------------------|
| documents     | 8–20 s            |
| dies          | 15–30 s           |
| mesos         | 30–60 s           |
| anys          | 60–120 s          |

**Estimació de temps total**: el calendari anual del català enllaça de
l'orde d'uns ~290 dies amb "suplement" (la majoria sense cap document
traduït, però cada un exigix igualment una petició de cortesia). Amb
~23 anys de català i ~15 de valencià, açò són de l'orde d'unes **11.000
peticions a nivell de dia**, que a ~22 s de mitjana entre cada una sumen
per si soles **unes 68–70 hores**. Sumant les esperes entre mesos/anys i
les descàrregues dels documents realment traduïts (probablement uns
centenars al llarg de tot el rang), l'execució completa dels dos idiomes
requerix aproximadament **3–4 dies d'execució contínua** (o diverses
sessions més curtes, gràcies al fet que és reprenible). Açò és
deliberat: prioritza no saturar un servei públic per damunt de la
velocitat.

## Construcció del corpus per a estudi

Una vegada descarregats els PDF, `construir_corpus.py` construïx un
corpus en JSON llest per a analitzar, sense tornar a tocar la xarxa. Es
pot rellançar en qualsevol moment (p.ex. segons el scraper vaja
descarregant més parelles): recorre el que hi haja en disc i regenera
l'eixida sencera cada vegada.

```bash
python construir_corpus.py   # PDF -> ../dades/boe/corpus.json
```

### `corpus.json` (nivell document)

Un array amb un objecte per cada parella català/valencià (mateix ID base
`BOE-X-YYYY-NNNNN`, ja garantit pel scraper). Extrau el text dels dos PDF
amb PyMuPDF **a nivell de bloc** (`page.get_text("dict")`, amb la info de
font de cada tram de text), que en el BOE correspon a paràgrafs reals —
no a nivell de línia renderitzada. Açò importa: català i valencià
embolcallen cada paràgraf en un nombre de línies de PDF distint (la
traducció no ocupa el mateix espai), així que segmentar per línia en lloc
de per paràgraf desalineava les frases entre els dos idiomes més avant.
Cada `texto` guarda els seus paràgrafs separats per una línia en blanc
(`"\n\n"`); dins d'un paràgraf, els salts de línia del PDF ja s'han unit
en una sola frase contínua.

Un paràgraf tallat a mitja frase (típicament per un salt de pàgina) es
fusiona amb el següent si no acaba en puntuació de tancament — però
només si a més **coincidix la font** en el punt d'unió (mateixa
tipografia, p.ex. cursiva/redona) i el següent **no** és un encapçalament
estructural reconegut ("Article N.", "Disposició final/addicional...",
"CAPÍTOL..."). Van caldre les dos condicions perquè, mirant casos reals:
els títols d'article van en cursiva i el cos en redona, així que comparar
només la puntuació fusionava a vegades el títol amb el paràgraf següent
en un idioma sí i en l'altre no (el català i el valencià no sempre
coincidixen en si el títol porta punt final — una inconsistència real
dels PDF oficials, no un error d'extracció); i en un cas concret
("...article 149.1.25a" seguit de "Disposició final segona.") ni tan
sols hi havia diferència de tipografia, només de puntuació, així que va
caldre a més reconéixer el patró de l'encapçalament mateix. També neteja
les capçaleres/peus de pàgina que el BOE repetix en cada pàgina
(encapçalament "BOLETÍN OFICIAL DEL ESTADO", línia de suplement, data,
"Secc. X. Pàg. N", peu amb ISSN...) amb una llista de patrons
(`LINEAS_RUIDO`), línia a línia, abans de fusionar/segmentar res.

**Bug real trobat i corregit (02/10/2026)**: el patró de la línia de data
(`"Dimarts 27 d'octubre de 2009"`) només reconeixia `"de " + mes`, però el
català/valencià elidix "de" en `"d'"` davant de mes que comença en vocal
-- `abril`, `agost`, `octubre` (no en `gener`, `febrer`, `març`, `maig`,
`juny`, `juliol`, `setembre`, `novembre`, `desembre`, que comencen en
consonant). Per als documents datats en estos 3 mesos, la línia de data
mai es filtrava i es colava literalment enmig de la frase quan el salt de
página (una posició física fixa en el PDF) queia a mitjan frase —
`en primer lloc, davant` `Dimarts 28 d'abril de 2015` `l'enorme...` en
compte d'una frase contínua. Verificat abans/després sobre
`BOE-A-2015-4607` (abril) i `BOE-A-2009-17000` (octubre): la capçalera
desapareix i la frase es torna a fusionar correctament sola, gràcies a la
lògica de fusió per salt de pàgina que ja existia (vore paràgraf anterior)
-- no va caldre tocar-la, només que la capçalera deixara de colar-se-hi
pel mig. Patró corregit: `(?:de |d')\w+` en compte de `de \w+`.

De pas es va trobar i corregir un segon bug, independent, que impedia
relançar este script després de la reorganització de carpetes a
valencià (01-02/10/2026): `"archivo"` calculava la ruta relativa al
PDF respecte a `boe/` (`BOE_DIR`, la carpeta de l'script) en compte de
respecte a `dades/boe/` (`CORPUS_DIR`, on viuen els PDF ara) -- fallava
amb `ValueError` en qualsevol execució des que les dades es van moure.

```json
{
  "id": "BOE-A-2009-3022",
  "fecha": "2009-02-24",
  "anio": 2009,
  "catalan":    {"id": "BOE-A-2009-3022-C", "titulo": "...", "url": "...", "archivo": "...", "num_paginas": 5, "num_caracteres": 16000, "texto": "..."},
  "valenciano": {"id": "BOE-A-2009-3022-V", "titulo": "...", "url": "...", "archivo": "...", "num_paginas": 5, "num_caracteres": 16280, "texto": "..."}
}
```

Esquema d'IDs (decisió: sí es diferencia l'idioma, però com a sufix, no
en l'ID base): `id` és l'identificador BOE compartit per la parella,
sense idioma; `catalan.id`/`valenciano.id` afigen el sufix `-C`/`-V` (el
mateix que ja usa el nom de fitxer del PDF). Així es pot agrupar per
document o filtrar per idioma indistintament.

`segmentar_parrafo`/`segmentar_parrafos` (partir `texto` en paràgrafs
reals per `"\n\n"`, i cada paràgraf en frases per puntuació) viuen en
`texto_comun.py`, compartides per `analizar_corpus.py` i
`alinear_corpus_bleualign.py`. Ahí mateix viu `es_tabla()` (vore més
avall, secció de Bleualign). Va haver una versió anterior d'este corpus a
nivell de frase amb alineació per recompte exacte de posició
(`corpus_frases.jsonl`, generat per un `construir_frases.py` ja retirat)
— es va abandonar en favor de `alinear_corpus_bleualign.py`, que alinea
per similitud de text en lloc de per recompte i cobrix molts més casos
(vore més avall).

### `corpus_bleualign.jsonl` (alineació per similitud, no per posició)

Exigir coincidència exacta de recompte (mateix nombre de paràgrafs,
després mateix nombre de frases dins de cada un) descarta documents
sencers per una sola discrepància, encara que el 95% del document siga
perfectament paral·lel — va ser el primer enfocament d'este projecte i es
va abandonar per açò. Investigant eixos casos es va vore que la causa no
sempre és una fallada d'extracció — a vegades el preàmbul d'una versió
porta paràgrafs explicatius que l'altra senzillament no té (contingut
real distint, no una frase mal tallada; p.ex. una secció sencera, «TÍTOL
I bis», que només existix en la versió valenciana d'un document).
`alinear_corpus_bleualign.py` resol açò alineant per **similitud de
text** en lloc de per recompte, usant
[Bleualign](https://github.com/rsennrich/Bleualign) (Sennrich & Volk,
2010):

```bash
pip install -r requirements.txt   # instal·la pymupdf i bleualign
python alinear_corpus_bleualign.py   # corpus.json -> ../dades/boe/corpus_bleualign.jsonl
```

Bleualign està pensat per a parells d'idiomes *distints*: necessita una
traducció automàtica d'un costat cap a l'idioma de l'altre per a poder
comparar per solapament de n-grames (BLEU). Ací no cal traduir res de
veres — se li passa **el mateix text en català com si ja fóra la seua
traducció al valencià** (identitat), raonable únicament perquè
comparteixen la immensa majoria del vocabulari. Per dins, Bleualign
combina dos fases: una alineació per BLEU amb programació dinàmica (camí
monòton que maximitza similitud, permetent saltar frases sense parella),
i un reompliment de forats que prova d'agrupar diverses frases seguides
d'un costat contra una de l'altre, i com a últim recurs, per a forats
xicotets, aplica l'algorisme Gale-Church clàssic de 1993 (basat en
longitud, no en text).

```json
{"id": "BOE-A-2009-3022-0003", "documento_id": "BOE-A-2009-3022", "fecha": "2009-02-24", "texto_catalan": "Les principals economies desenvolupades...", "texto_valenciano": "Les principals economies desenrotllades...", "similitud": 0.77}
```

`similitud` no la dona Bleualign directament (no exposa la seua puntuació
BLEU interna per parell via la seua API senzilla) — es recalcula amb
solapament de paraules normalitzades (Jaccard) sobre el parell que
Bleualign decidix, per a poder filtrar per qualitat en usar-lo com a
dades d'entrenament. Ull: un parell amb `similitud: 0.0` no sempre és un
error — frases curtes com `"1."` o alternances dialectals sense arrel
comuna (`Vuit.`/`Huit.`, `Cinquanta-cinquè.`/`Cinquanta-cinc.`) donen
Jaccard 0 encara que l'emparellament siga correcte; comprovat a mà que la
immensa majoria dels parells amb similitud 0 són d'este tipus, no errors
reals.

**Filtre de paràgrafs tabulars:** abans de segmentar en frases i
passar-les-hi a Bleualign, es descarten els paràgrafs que
`texto_comun.es_tabla()` identifica com a pressupostos/aranzels/
formularis — no són prosa, i deixar-los entrar només donava a Bleualign
contingut quasi tot numèric on no té amb què emparellar bé (mirant els
parells de similitud més baixa, la majoria dels errors genuïns de veres
— no les alternances dialectals sense arrel comuna, que són correctes
encara que donen similitud 0 — es concentraven ahí: files de taules de
sous/coeficients/codis aranzelaris emparellades amb la fila equivocada).
Es detecta amb dos senyals: punts-guia (`". . . . . . ."`, el BOE els usa
per a alinear visualment una etiqueta amb un número) o menys de 55% de
lletres sobre caràcters no-espai. Calibrat sobre el corpus real: marca
~1,1% dels paràgrafs (concentrats en documents de pressupostos/aranzels/
formularis), zero falsos positius en una mostra de revisió de 20 a
l'atzar.

Resultats sobre el corpus de 521 documents (després d'excloure paràgrafs
tabulars): 520 amb almenys una frase alineada (l'únic sense cap,
`BOE-A-2010-11419`, és un cas a banda: l'extracció del PDF valencià dona
0 paràgrafs, probablement un PDF escanejat sense text, no un problema
d'alineació), **94,0% de totes les frases en català emparellades**
(322.300 frases totals, 302.977 parells; enfront del ~32% que passa
l'exigència de recompte exacte de paràgraf), similitud mitjana 0,71-0,72
(mediana 0,79). Ni el document pitjor alineat baixa de 0,62 de similitud
mitjana.

### `corpus_entrenamiento.jsonl` (subconjunt net per a entrenar)

```bash
python exportar_entrenamiento.py   # corpus_bleualign.jsonl -> ../dades/boe/corpus_entrenamiento.jsonl
```

Un únic llindar de similitud no separa bé "parell correcte de similitud
baixa" de "parell mal emparellat": comprovat amb casos reals, els
parells dialectals legítims sense arrel comuna (`Vuit.`/`Huit.`,
`Dinovena.`/`Dènou.`) tenen les dos frases de **longitud quasi idèntica**
(ràtio 1,0-1,5) encara que comparteixen zero paraules; el cas d'error
real que coneixíem (`FERRALLA` emparellat amb una llista de codis
aranzelaris) té una ràtio de longitud de **21x**. Regla de dos nivells en
lloc d'un tall únic:

1. `similitud >= 0.3`: es queda sempre (266.393 parells).
2. Si no, es rescata només si les dos frases tenen paraules reals (no són
   només números/marques de llista) **i** la seua longitud és pareguda
   (ràtio ≤ 2) — 2.342 parells rescatats. Es descarten 352 per longitud
   dispar (ací cau el cas `FERRALLA`) i 33.890 per no tindre cap paraula
   real en algun costat (parells tècnicament correctes però sense
   contingut que aprendre, tipus `"1."`/`"1."`).

Total: **268.735 parells (88,7%)**. Els llindars (`UMBRAL_SEGURO`,
`RATIO_LONGITUD_MAXIMO`) són constants al principi de l'script — canviar
de criteri és tocar un número i rellançar.

## Analítica del corpus (`analizar_corpus.py`)

Genera un informe HTML (sense dependències externes, mai necessita
internet) per a estudiar el corpus i, en concret, quant es sosté a la
pràctica la separació dialectal català/valencià. Totes les pestanyes
funcionen fent doble clic sobre el fitxer, **llevat del visor frase a
frase**, que necessita un servidor local trivial (vore baix, secció
"Visor frase a frase") perquè les seues dades viuen en fitxers a banda:

```bash
python analizar_corpus.py   # corpus.json + 02_regles_dialectals -> ../dades/boe/analitica_corpus.html
```

Requerix `corpus.json` ja generat (`construir_corpus.py`), opcionalment
`corpus_bleualign.jsonl` (`alinear_corpus_bleualign.py`, si no existix
eixa pestanya senzillament no apareix), i la carpeta
`../02_regles_dialectals` amb estos fitxers — `cargar_materiales()` els
busca primer a l'arrel d'eixa carpeta i si no hi són, en `lexic/` i
`fonts/` (la carpeta es va reorganitzar en subcarpetes per a un
pipeline distint que també l'usa; vore el seu propi `README.md` si vols
el detall d'eixa reorganització):

- `apertium-cat.cat.dix` (diccionari Apertium, font de `palabras_val.json`; en `fonts/`).
- `palabras_traducidas.json`: glossari curat valencià/català/castellà (en `lexic/`).
- `palabras_val.json`: formes marcades exclusivament `v="val_gva"` en el
  diccionari Apertium, sense equivalent `cat` en la mateixa entrada (en `fonts/`).
- `regles_cat_val.md`: 108 regles de terminació morfològica (verbs,
  pronoms, adjectius...), demostratius (est-/aquest-) i locucions (en `fonts/`).

L'informe té pestanyes: Resum (documents/any, grandària del corpus, %
de documents amb paràgrafs alineables), Lèxic dialectal, Formes
exclusives de valencià, Morfologia, Demostratius (amb evolució per any),
Locucions, Diff textual i Bleualign (esta última només si existix
`corpus_bleualign.jsonl`); totes les taules grans són interactives
(filtre de text + orde per columna). Per a cada marcador es calcula una
"fidelitat": quin %
de les seues aparicions en tot el corpus cauen en el costat dialectal on
s'esperarien (100% = separació neta; valors baixos indiquen que el text
etiquetat com a valencià usa en realitat la forma catalana, o al revés).
La pestanya "Metodologia" del propi informe explica les limitacions
(tokenització heurística, falsos positius per sufixos curts, etc.).

### Diff textual: què canvia paraula a paraula entre les dos versions

Alineació en dos nivells, no una única posició global de frase (
l'alineació per frase a soles va resultar massa fràgil — vore més avall):
primer per **paràgraf** (`indice.pares_parrafos_alineados`: documents amb
el mateix nombre de paràgrafs reals en els dos idiomes, la unitat de
traducció natural del BOE — cada article/paràgraf és 1 a 1). Dins de cada
paràgraf ja emparellat, si també té el mateix nombre de frases en els dos
idiomes es comparen frase a frase; si no, es compara el paràgraf sencer
com una sola unitat, per a no perdre eixe paràgraf de l'anàlisi. En tots
els casos, la comparació és `difflib` paraula a paraula, en lloc de
partir d'un glossari tancat.

Amb el corpus parcial ja provat açò va trobar automàticament, sense tocar
el glossari, parells com `estableix`/`establix` o `refereix`/`referix`
(terminació verbal -eix/-ix, un patró sistemàtic que no estava entre les
108 regles), lexemes nous com `perjudici`/`perjuí`, diferències de temps
verbal com `pot`/`podrà` o `és`/`serà`, i fins i tot un cas on la versió
"valenciana" d'un document usa la paraula castellana `estado` en lloc de
`estat` — justament el tipus de troballa que un glossari tancat no pot
traure per si sol.

Cada parell de substitució trobat es marca com a conegut (coincidix amb
el glossari o amb una regla morfològica) o "novetat"; la taula per
document permet vore en quins documents canvia més vocabulari.
L'exemple de cada parell (~44.000 files en total) mostra només un
fragment retallat al voltant del canvi (±8 paraules), no la frase
sencera -- amb eixe volum de files, guardar la frase completa de cada una
(a vegades un paràgraf legal llarguíssim) pesava 37,9 MB només eixa
taula; el fragment és alhora més lleuger i més ràpid de llegir d'un colp
d'ull que buscar el canvi dins d'una frase llarga.

**Senyals de confiança dialectal (02/10/2026)**: dos columnes noves a la
taula de parells, pensades per a distingir una substitució dialectal
neta d'una reescriptura d'estil del traductor -- arran de la conversa
sobre que este corpus és la mateixa norma traduïda dos vegades, de
vegades per persones distintes, i no tot el que canvia és dialecte:

- **Similitud mitjana de la frase**: la similitud (difflib) mitjana de
  totes les frases on apareix eixe parell, a banda del propi canvi. Alta
  (frases pràcticament idèntiques llevat del parell) és bon senyal;
  baixa (sol aparèixer en frases molt reescrites) és sospitós -- pot ser
  coincidència de paraules en frases que en realitat no tenen res a vore.
- **% de vegades que és l'únic canvi**: de totes les aparicions, en quin
  % eixe parell és l'ÚNIC canvi de la frase (ni inserció ni cap altra
  substitució a la vegada). Alt suggerix substitució puntual i neta;
  baix suggerix que sol anar acompanyat de més reescriptura al voltant.

A propòsit **no** es combinen en una sola puntuació: es deixen com a
columnes ordenables a banda perquè es puga jutjar a ull, cas a cas, si
cada senyal aporta de veres abans de confiar-hi (hi havia dubte explícit
sobre si la segona, la dispersió, calia). Pendent per a una pròxima
iteració: una tercera senyal de consistència temporal (si un parell és
estable al llarg de tots els anys del corpus o es concentra en un periode
concret, que apuntaria més a manies d'un traductor que a una regla
dialectal real).

Important: que dos versions tinguen el mateix nombre total de paràgrafs
no garantix que el paràgraf `i` d'una corresponga al paràgraf `i` de
l'altra en tot el document — la columna "similitud mitjana" d'eixa taula
servix per a detectar quan la correspondència és en realitat roïna
malgrat quadrar el total (a la pràctica, la majoria de documents alineats
per paràgraf ixen amb 90%+ de similitud mitjana; els que baixen d'ahí
solen ser lleis de pressupostos amb taules numèriques molt denses).

**Per què per paràgraf i no per frase a soles:** la primera versió d'açò
segmentava el text per línia de PDF renderitzada abans de buscar el punt
i seguit; com que català i valencià embolcallen la mateixa frase en un
nombre de línies distint (la traducció no ocupa el mateix espai), la
majoria de "frases" resultants eren en realitat fragments de línia que
no es corresponien entre idiomes, encara que el nombre total coincidira
per casualitat. En extraure el text per bloc de PyMuPDF (paràgraf real,
vore `corpus.json` més amunt) i alinear primer per paràgraf, la cobertura
va pujar de 57 a 168 documents comparables sobre el mateix corpus de 521
parelles, i els exemples que ixen ara són frases completes i coherents en
lloc de fragments tallats.

Ull, açò no va ser un arreglament d'una sola vegada: la primera versió
amb blocs de PyMuPDF seguia fusionant malament en casos concrets — el
títol d'un article (en cursiva, sense punt final en una de les dos
versions) es fusionava amb el paràgraf següent en un idioma sí i en
l'altre no, desplaçant la correspondència paràgraf a paràgraf de la resta
del document encara que el nombre total de paràgrafs seguira coincidint
per casualitat ("BOE-A-2009-3022", el document d'exemple del 24 de
febrer de 2009, tenia justament este problema). Es va corregir comparant
també la tipografia en el punt d'unió i reconeixent els encapçalaments
estructurals del BOE ("Article N.", "Disposició final/addicional...")
perquè mai es fusionen amb el paràgraf anterior — vore `construir_corpus.py`.

### Visor frase a frase (llegir les diferències, no només comptar-les)

Dins de la pestanya "Diff textual" hi ha un visor: tries un document en
un desplegable i llegixes les seues frases una a una, amb les paraules
que canvien ressaltades en color directament sobre el text real —

> Correcció d'errors i **errades** de la Llei 2/2008... (català)
> Correcció d'errors i **errates** de la Llei 2/2008... (valencià)

— en lloc de només vore la parella `errades`/`errates` solta en una
taula. Ambre = paraula substituïda, verd = paraula que només està en el
valencià, roig ratllat = paraula que només està en el català. Té casella
per a mostrar només les frases amb diferències, buscador de text, i
canvia de document sense recarregar la pàgina (cada document es pinta en
lots de 300 frases amb un botó "Carregar més", així que documents amb
milers de frases no bloquegen el navegador). És la forma de valorar a
ull la qualitat d'una traducció concreta del BOE, més enllà de les
xifres agregades.

**Cobertura ampliada amb Bleualign (02/10/2026)**: abans el visor només
cobria els ~169 documents amb el mateix nombre EXACTE de paràgrafs en els
dos idiomes (la resta desapareixia en silenci, encara que l'alineació a
nivell de frase de `corpus_bleualign.jsonl` cobrix 520 dels 521). Ara
cada document del desplegable indica el seu mètode —
**[parrafos]** (exacte) o **[bleualign]** (per similitud, menys fiable en
frases curtes o sense arrel lèxica comuna) — i hi ha una casella per a
quedar-se només amb els de mètode exacte si vols la màxima confiança.

**Arquitectura del fitxer (02/10/2026, canvi important)**: les 322.300
frases de tot el corpus NO viuen dins de `analitica_corpus.html` --
provat i revertit: embeure-les totes disparava el fitxer a més de
180 MB i el feia pràcticament inusable. En compte d'això, cada document
té el seu propi `.json` a `analitica_corpus_visor/<id>.json`, i el visor
el carrega amb `fetch()` NOMÉS quan el tries al desplegable (amb caché en
memòria mentre dures en la pàgina). Conseqüència pràctica: la majoria de
navegadors **bloquegen `fetch()` de fitxers locals** quan obris l'HTML
fent doble clic (`file://`) -- per a usar la pestanya del visor cal
arrancar un servidor estàtic trivial des de `dades/boe/`:

```bash
cd ../dades/boe
python -m http.server 8000
# obri http://localhost:8000/analitica_corpus.html
```

La resta de pestanyes (resum, lèxic, pares de substitució...) seguixen
funcionant igual fent doble clic, sense necessitat de servidor -- només
el visor frase a frase el necessita, i l'HTML ho explica amb un missatge
clar si el `fetch()` falla.

(Nota tècnica interna: en implementar açò es va detectar i corregir una
fallada real en l'HTML generat per versions anteriors de l'script — les
funcions JavaScript de les taules es definien al final de la pàgina però
es cridaven abans, així que cap taula arribava a pintar-se en un
navegador real. Ja corregit i verificat amb un navegador headless.)

Nota de neteja: `palabras_traducidas.json` porta, en algunes entrades,
restes de la notació "arrel/desinència" de gènere (p.ex. `Bonico/a`)
partits per `/` com si foren sinònims independents — queden com a ítems
solts d'1-2 lletres en minúscula ("a", "ja"...) que, comptats en el
corpus, no signifiquen res (són preposició/adverbi molt freqüents).
L'script els descarta automàticament (vore `_limpiar_entradas_vocabulario`
en `analizar_corpus.py`); es va verificar a mà que tot ítem curt legítim
del fitxer ve capitalitzat, així que el filtre no perd dades reals.

## `../dades/boe_net/` -- separar dialecte real d'estil del traductor

A partir de 02/10/2026, `depurar_ruido_estilistico.py` i
`generar_visor_diferencias.py` (en esta mateixa carpeta) generen una
versió depurada del corpus, a `../dades/boe_net/`, sense tocar cap
fitxer d'ací -- pensada específicament per a distingir diferència
dialectal real de diferència d'estil d'un traductor concret (mateix text
oficial, traduït dos vegades per equips distints). Vore
`../dades/boe_net/README.md` per al detall complet.

## Notes

- Abans de cada execució es descarrega i respecta `robots.txt` en temps
  real (no hi ha una còpia local que puga quedar desactualitzada).
- No es torna a descarregar un fitxer que ja existisca en disc o que ja
  conste en `progreso.json`.
- Si boe.es retorna 429/503 de forma persistent, el scraper pausa 10
  minuts abans d'un últim intent; si eixe intent també falla, es descarta
  eixe element (queda registrat en el log) i es continua amb el següent,
  sense avortar tota l'execució.
