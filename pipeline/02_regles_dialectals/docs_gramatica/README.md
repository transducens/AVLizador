# Gramàtiques oficials: GEIEC (IEC) i GNV (AVL)

Les dos gramàtiques normatives completes, en text pla, que es fan servir
com a font d'autoritat per a derivar regles dialectals morfològiques
(més enllà del lèxic diferencial d'Apertium/Mauricio que ja cobrixen
`lexic/` i `font_mauricio/`). Mentre `regles_dialectals_amb_evidencia.md`
i `lexic/` documenten diferències **lèxiques** confirmades paraula a
paraula, esta carpeta documenta diferències **gramaticals** (articles,
demostratius, pronoms febles, preposicions...) citant el paràgraf exacte
de cada normativa.

## Estructura

```
docs_gramatica/
├── baixar_geiec.py              scraper (Playwright) de la GEIEC
├── geiec_complet.txt            GEIEC consolidada, 204 seccions
├── geiec_scraper.log            log de l'última execució del scraper
├── gnv_complet.txt              GNV consolidada, 43 capítols
├── guia_dialectal_morfologia.md comparativa GEIEC↔GNV, per temes gramaticals
└── guia_traduccio_dialectal.md  regles de traducció pràctiques, amb exemples abans/després
```

## Les dos fonts primàries

### GEIEC — Gramàtica Essencial de la Llengua Catalana (IEC, 2018)

`geiec_complet.txt` és el resultat de **`baixar_geiec.py`**, un scraper
fet amb Playwright (geiec.iec.cat carrega el contingut via JavaScript, no
servix amb una petició HTTP normal). Visita les 204 seccions de l'índex
real de la gramàtica (llista `SECCIONS`, capítols 1-35, codificada a mà
al script perquè el lloc no exposa un índex navegable per codi), neteja
la pàgina (llevant nav/header/footer/botons via JS) i guarda cada secció
amb una capçalera (`SECCIÓ`/`TÍTOL`/`URL`/`DATA`) abans de consolidar-ho
tot en un únic fitxer.

Scraping respectuós: espera aleatòria de 3-7s entre peticions, pausa
llarga (25-45s) cada 20 seccions descarregades, és **reprenible**
(`already_done()` salta seccions ja guardades si cal tornar a executar-lo
després d'un tall), i usa un User-Agent realista + sessió iniciada per
`/inici` abans de demanar cap secció.

```bash
pip install playwright
playwright install chromium
python baixar_geiec.py
```

### GNV — Gramàtica Normativa Valenciana (AVL, 2016)

`gnv_complet.txt` **no ve d'un scraper nou**: es genera a partir de
`../../dades/avl/clean/avl_gnv.jsonl`, que ja conté la GNV completa
escrapejada de avl.gva.es per l'etapa 1 (`01_extraccio_i_neteja/`). Es
va reformatar a text pla amb el mateix estil de capçalera que la GEIEC
(`CAPÍTOL`/`TÍTOL`/`URL`/`DATA`, un per cada un dels 43 capítols) per a
poder llegir i citar totes dos gramàtiques de la mateixa manera. L'script
puntual que va fer esta conversió ja ha complit la seua faena i s'ha
llevat -- si el `.jsonl` d'origen canvia, el patró per a regenerar
`gnv_complet.txt` és llegir eixe fitxer, ordenar per `capitol_num`, i
escriure la mateixa capçalera per registre.

## Els documents derivats

Les dos gramàtiques consolidades són la font; estos dos documents són
l'anàlisi, fets llegint totes dos i parant esment específicament a on
**divergixen**:

- **`guia_dialectal_morfologia.md`** — document de referència organitzat
  per tema gramatical (article definit, demostratius, possessius, pronoms
  febles bàsics i en combinació, pronom partitiu, adverbis de lloc),
  cada un amb quadre comparatiu GEIEC↔GNV i cita del paràgraf exacte
  (`GEIEC §10.3`, `GNV §15.2`...). Acaba amb una taula de conversió ràpida
  en tots dos sentits.
- **`guia_traduccio_dialectal.md`** — versió orientada a l'aplicació
  pràctica: regles numerades per blocs (A. determinants i pronoms, B.
  pronoms febles, C. preposicions, D. adverbis de lloc, E. advertències i
  zones grises), cada una amb l'exemple abans/després en els dos sentits
  de traducció i la font normativa. Pensat per a llegir's regla a regla
  en comptes de tema a tema.

**Relació amb el motor `traductor/`**: estes guies documenten diferències
gramaticals (sistema de demostratius en 3 graus, *lo/los* com a pronom
feble, l'orde datiu+acusatiu...) que avui el motor NOMÉS cobrix
parcialment -- `traductor/rules/demostratius.py` i `possessius.py` ja
apliquen una part (vore `traductor/README.md`), però els pronoms febles
en combinació (bloc B) i les preposicions (bloc C) encara no tenen cap
regla al motor. Abans d'implementar-ne cap, verificar primer quina
cobertura real té cada regla al corpus (mateix criteri que la resta del
projecte: evidència abans que heurística).

## Com regenerar

```bash
# GEIEC: torna a executar el scraper (reprenible, salta el que ja existix)
python baixar_geiec.py

# GNV: si avl_gnv.jsonl canvia, cal tornar a escriure gnv_complet.txt
# a mà amb el mateix format de capçalera (vore secció anterior)
```

Els documents derivats (`guia_dialectal_morfologia.md`,
`guia_traduccio_dialectal.md`) són treball d'anàlisi manual sobre les
dos gramàtiques consolidades -- no hi ha cap script que els regenere
automàticament.
