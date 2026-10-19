# Fonts de dades del traductor — estat 19/10/2026

Este directori conté TOTS els fitxers font que `traductor/sync_data.py`
pot copiar a `traductor/data/` (el paquet `traductor/` mai llig ací
directament en temps d'execució — vore docstring de `sync_data.py`).
Hi conviuen dos generacions: la primera entrega de l'equip AVLizador
(29-30/09/2026, basada majoritàriament en l'apertium bilingüe
català-castellà) i la primera entrega amb categoria gramatical real del
proveïdor oficial, `diccionarios/` (16/10/2026). **L'objectiu declarat és
acabar depenent només de `diccionarios/`**, però hui per hui dos
peces (possessius i conjugacions) encara no tenen equivalent complet
ací — vore detall baix.

## Actives (`sync_data.py` les llig hui mateix)

- **`diccionarios/lexico_general.json`** (1.629 entrades) — entrega
  nova del proveïdor (16/10/2026). Lèxic general amb categoria gramatical
  real (camp `categoria`: n/adj/adv/cnjadv/pr/ij/prn/num/det) i resolució
  de col·lisions explícita (`canonica`, `problema`, `id_colision`).
  Alimenta `traductor/data/lexic_general.json`, consumit per `lexic.py`
  (lèxic general, les dos direccions) **i també** per `numerals.py`
  (categoria "num"). Ja substituïx del tot l'entrega vella de lèxic
  (`unificado.json`/`lexico_general_limpio.json`, ja eliminats) i els
  numerals que abans vivien en un fitxer a banda
  (`numerales_limpio.json`, ja eliminat). Detall complet de la migració:
  `documentacio/hoja_de_ruta_migracio_diccionarios_v1.md`.

- **Possessius, ara DINS de `diccionarios/lexico_general.json`** (12
  files, `categoria: "det"`, `tipo: "v:lexic_val_avl"`,
  `fuente: "avl_equip"`). Abans vivien a banda, en `posesivos_cat_val.json`
  (fitxer de l'equip AVLizador, NO del proveïdor oficial, 30/09/2026) --
  es va provar retirar-lo del tot el 19/10/2026 (objectiu: usar només
  fonts del proveïdor) i es va revertir pel cost mesurat (-18 frases val→cat i -21
  cat→val del benchmark de 151, totes per "seua/meua" sense convertir --
  `lexico_general.json` tenia 0% de cobertura real per a estes formes
  llavors). Més avant eixe mateix dia, l'usuari va enganxar les 12 files
  DIRECTAMENT dins de `lexico_general.json` i va esborrar el fitxer solt.
  És un producte cartesià sense filtrar (per cada arrel dona les 4
  combinacions singular/plural, incloent 2 que barregen número:
  "meua"→"meves"); `possessius.py`, en les dos direccions
  (`val_cat`/`cat_val`), llig ara `lexic_general.json` directament,
  filtrant per `fuente == "avl_equip"` (no només `categoria == "det"`,
  que també fan servir els demostratius dins del mateix fitxer -- cal
  distingir-los) i es queda només amb els 6 parells on el número casa
  als dos costats. `categoria: "det"` (mateixa família que els
  demostratius del proveïdor, no `"prn"`: un posessiu és un determinant,
  no un pronom feble com "vos"→"us"). **Nota important**: `sync_data.py`
  encara tenia un `FontSpec` apuntant al fitxer solt quan es va esborrar
  -- trencava `python -m traductor.sync_data` amb `FileNotFoundError` --
  ja corregit (llevat eixe `FontSpec`, esborrada la còpia òrfena
  `traductor/data/possessius_general.json`). Verificat amb doctests +
  benchmark: 0 canvis de comportament. Vore `CLAUDE.md` i
  `documentacio/hoja_de_ruta_migracio_diccionarios_v1.md`.

- **2 fonts que es fusionen en `traductor/data/conjugacions_dialectals.json`**
  (consumit per `conjugacions_dict.py`) — **des del 19/10/2026 ja no
  queda cap fitxer vell de l'equip AVLizador** (vore baix per què):
  1. **`diccionarios/verbos_diferentes_conjugados.json`** (912
     parells, arrel verbal distinta val/cat, p.ex. telefonar/trucar).
  2. **`diccionarios/conjugaciones_general.json`** (44.210 formes,
     43.242 originals + 968 fusionades a mà el 19/10/2026, vore baix).
     Cada fila té un camp `morfologia` (p.ex. `["pis", "p1", "pl"]`) que
     codifica temps/mode + persona + nombre — **descodificat amb
     evidència real el 19/10/2026** (cap falta d'explicació del proveïdor
     bloqueja ja esta font): `pri`=present indicatiu, `prs`=present
     subjuntiu, `pii`=imperfet indicatiu, `pis`=imperfet subjuntiu,
     `imp`=imperatiu, `pp`=participi, `inf`=infinitiu (99,7% de les
     43.242 files originals). Codis rars (`fti`, `prn`, `ij`, `vbmod`...)
     sense decodificar amb prou confiança es queden per davall de l'1% i
     ja van acompanyats del camp `problematica`/`problema: colision` que
     `conjugacions_dict.py` ja exclou -- **no calia esperar l'explicació
     per a integrar-la de forma segura**, el lookup mai ha triat traducció
     per temps/mode, nomes és informatiu. Detall complet del descodificat:
     `documentacio/hoja_de_ruta_migracio_diccionarios_v1.md`.

  `sync_data.py` marca automàticament `problematica: true` en qualsevol
  forma que, DINS D'UN SOL fitxer font, tinga més d'una traducció
  catalana distinta (ambigüitat real indicatiu/subjuntiu) — eixes formes
  queden excloses del lookup directe de `conjugacions_dict.py`.

  **Els 4 fitxers vells de l'equip AVLizector (29-30/09/2026) RETIRATS
  del tot (19/10/2026)**. Primer es van moure a `backup_pendent/`
  com a xarxa de seguretat; **eixa carpeta ja s'ha esborrat del tot**
  (mateix dia, més avant) perquè els seus 4 fitxers estaven o bé fusionats
  sencers en un altre lloc (`conjugaciones_limpio.json` dins de
  `conjugaciones_general.json`) o bé provats al 100% com a redundants
  (els altres 3) -- cap dels dos casos deixava res realment "pendent". El
  contingut es conserva igualment a l'historial de git
  (`git log -- <ruta>` sobre el commit d'eixe dia) per si mai calguera.
  - `verbos_no_ambiguos.json`, `verbos_todos_anotados.json` i
    `conjugaciones_nuevo.json`: mesurat verb a verb que els seus
    infinitius d'una sola paraula ja estaven TOTS coberts per les 2 fonts
    oficials -- l'únic que aportaven de més eren frases multi-paraula
    ("llançar la brossa", "fer cara de"...) que el motor mai ha pogut fer
    servir (no hi ha mecanisme de coincidència multi-paraula per a verbs
    encara -- mateix forat que les 103 entrades multi-paraula actives de
    `lexico_general.json`, vore secció "Pendent" baix). Confirmat amb els
    4 benchmarks: **zero diferència** al traure'ls.
  - `conjugaciones_limpio.json`: **SÍ tenia cobertura real** -- el
    paradigma complet de present de subjuntiu del verb "ser"
    (siga/sigues/siga/siguem/sigueu/siguen → sigui/siguis/sigui/siguem/
    sigueu/siguin, que `conjugaciones_general.json` nomes tenia amb 3
    formes soltes, cap de subjuntiu) i ~12 verbs sencers ("pertànyer",
    "aparèixer", "acréixer", "prémer", "sofrir"...). **Les seues 968
    files s'han fusionat SENCERES dins de `conjugaciones_general.json`**
    (IDs `LIMPIO_1`..`LIMPIO_968`, `morfologia` derivat a mà per a 95
    formes, `problematica` preservat tal qual en 55). Important: la
    primera temptativa nomes va fusionar 97 formes "noves" (les que
    faltaven al lookup val→cat) i això va trencar el doctest de
    `cat_val/conjugacions_dict.py` -- "sofrisquen"→"sofreixin" queda
    exclosa del lookup val→cat pel filtre de risc de 3a plural (per això
    no eixia com a "forma nova" des d'eixe costat), pero fa falta en brut
    perquè `carrega_conjugacions_invers()` detecte que "sofreixin" és
    ambigua (patisquen/sofrisquen) i l'excloga -- fusionar el fitxer
    SENCER evita este tipus de forat invisible des d'una sola direcció.
    Confirmat amb els 4 benchmarks: resultats IDÈNTICS a quan el fitxer
    vivia a banda. **Pendent d'informar al proveïdor**: el paradigma de
    "ser" seguix sent un forat real de la seua font, nomes apedaçat
    localment.

## Resum de l'estat de bloqueig (19/10/2026)

**Ja no hi ha cap font bloquejada per falta d'explicació, ni cap fitxer
solt de l'equip AVLizador fora de `diccionarios/`.** Possessius i
conjugacions (els 4 fitxers vells, vore amunt) ja estan tots fusionats o
retirats -- `diccionarios/` és ara, de veres, l'única font de
`traductor/`, exactament com volia l'objectiu original d'esta migració.

## Fora del sistema de traducció — NO el llig `sync_data.py`

- **`palabras_traducidas.json`** — glossari trilingüe (valencià/català/
  castellà) que usa directament `pipeline/05_corpus_boe/analizar_corpus.py`
  per a comptar aparicions al corpus del BOE (informe de puresa
  dialectal del corpus, NO traducció). Sense relació amb `traductor/`.
  **Regenerat el 19/10/2026** amb `regenera_palabras_traducidas.py`: les
  entrades `categoria: "palabra"` (1.348, abans 1.261) ara vénen de
  `diccionarios/lexico_general.json` (font oficial); les 115 entrades
  `categoria: "toponimo"/"nombre"` es mantenen tal qual del fitxer vell
  perquè `lexico_general.json` no en porta cap (0 entrades
  `tipo: "v:top_gva"` en esta entrega) -- decisió explícita de l'usuari,
  no una llacuna oblidada. Tornar a executar l'script si
  `lexico_general.json` canvia.

## Pendent (19/10/2026)

- **Expressions multi-paraula**: 103 entrades actives de
  `lexico_general.json` tenen el valencià en 2+ paraules (p.ex. "treball
  d'investigació"→"treball de recerca") -- hui es descarten SENCERES en
  `val_cat/lexic.py` (`" " in valenciano: continue`), no hi ha cap
  mecanisme de coincidència greedy com el que descriu
  `diccionarios/Funcionamiento listas de palabras.pdf`. La direcció
  `cat_val` ja en té una versió parcial (`carrega_frases_invers`, 7
  entrades, nomes frase catalana→paraula valenciana solta). Pendent
  d'acordar l'abast abans de construir-ho.
- **4 entrades `homonimia_lexica` sense resoldre** (categories
  solapades/iguals als `lemas`, fa falta un LLM segons la guia): "bes",
  "bragues"/"calces", "hamaca"/"gandula", "blanca"/"garsa".
- **6 entrades `homonimia_lexica` més, POS-resolubles però encara
  `_PENDENT`** (sense verificar a `lexico_general.json`): "falaguera(es)",
  "brollador", "brulla(es)", "panolla(es)", "fartada(es)". Afegir-les a
  `categoria_gramatical_lexic.json` quan deixen de ser `_PENDENT`.

Detall dia a dia de com es va arribar a este estat:
`CLAUDE_HISTORIAL.md` i `documentacio/hoja_de_ruta_migracio_diccionarios_v1.md`.
