# Font: diccionari de Mauricio (equip AVLizador)

Estos fitxers són el diccionari català-valencià que Mauricio va compartir
per correu (4 fitxers, 29/09/2026, basats majoritàriament en l'apertium
bilingüe català-castellà) més dos que va afegir l'endemà
(`posesivos_cat_val.json` i `verbos_no_ambiguos.json`, 30/09/2026). Es
guarden ací sense modificar, tal com es van rebre, com a font d'evidència.

**Canvi important (30/09/2026, vesprada)**: `traductor/rules/` ara és
**pur lookup de diccionari de Mauricio** -- s'han retirat totes les fonts
externes (`apertium_368_val_cat.json`, `contrastius_paula_guerrero.json`,
`lexico_fiable.json`) i totes les regles de sufix/patró morfològic
(`demostratius.py`, `gentilicis.py`, `morfologia_verbal.py`, `perfet.py`,
`locucions.py`, `elisio.py`). Estos 6 fitxers de `font_mauricio/` són ara
**l'ÚNICA font de dades del traductor**. Vore `traductor/README.md`,
secció "DECISIÓ D'ARQUITECTURA", per l'impacte mesurat en el benchmark
(89/150 → 27/150 exactes) i el raonament complet.

Estat de cada fitxer (tots actius, tots INCORPORATS):

- **`conjugaciones_limpio.json`** (968 formes, 111 verbs) + **`verbos_no_ambiguos.json`**
  (261 formes, 45 verbs, afegit 30/09/2026, totes `ambigu: false`) --
  fusionats a `traductor/data/conjugacions_dialectals.json`
  (`traductor/sync_data.py`), consumits per `conjugacions_dict.py`.
  `verbos_no_ambiguos.json` va PRIMER en la fusió: 16 formes de "eixir"
  apareixen a totes dos fitxers amb traducció diferent (`isca->ixi` al
  fitxer vell, `isca->surti` ací), i guanya "surti" per coherència amb
  `eixir->sortir` ja decidit al lèxic general. Les formes
  `problematica: true` (ambigües indicatiu/subjuntiu) s'exclouen del
  lookup -- només "haja"/"hagen" es queden sense traduir per això (tota
  la conjugació de "haver" és `problematica`).

- **`lexico_general_limpio.json`** (611 entrades) -- alimenta
  `traductor/data/lexic_mauricio.json`, filtrat per
  `lexic.py::_carrega_mauricio_lexic`: exclou `_PENDENT` (151, sense
  verificar), topònims (73, `tipo: "v:top_gva"` -- el motor protegix tots
  els noms propis, mai s'aplicarien), multi-paraula, i
  `valenciano == catalan`. Quan una paraula té més d'una traducció
  possible, prioritza `canonica: true`; si cap ho és (com "xiquet" ->
  "noi"/"nen", totes dos `false`), guanya la primera del fitxer -- vore
  la nota de regressió a `traductor/README.md`.

- **`acentuacion_limpio.json`** (694 entrades) -- alimenta
  `traductor/data/lexic_acentuacio_mauricio.json`, 2a font de `lexic.py`.
  **Bug de dades conegut**: el fitxer llista `després→desprès` com si
  seguira el patró general d'accentuació, però "després" mai canvia en
  cap dels dos dialectes (confirmat empíricament, afectava 10 de les 150
  frases del benchmark) -- `lexic.py` ho exclou a mà amb un comentari
  explicant per què.

- **`numerales_limpio.json`** (180 entrades) -- alimenta
  `traductor/data/numerals_mauricio.json`, lookup exacte únic a
  `numerals.py` que cobrix tota la família huit/vuit I les arrels
  "dinou"/"disset" + derivats, inclosa "díhuit" (lookup exacte, sense cap
  cas especial a mà). S'exclouen 4 files de "vuitavat" (mateix català
  repetit per a 4 valencians diferents, extracció trencada al fitxer
  font). Numerals compostos NO enumerats literalment ("numeració
  combinatòria") ja no es cobrixen -- es va llevar el fallback de
  subcadena `huit→vuit` en passar a pur lookup (30/09/2026).

- **`posesivos_cat_val.json`** (12 files, afegit 30/09/2026) -- alimenta
  `traductor/data/possessius_mauricio.json`. El fitxer és un producte
  cartesià sense filtrar (per cada arrel dona les 4 combinacions
  singular/plural, incloent 2 que barregen número: "meua"→"meves").
  `possessius.py::_carrega_possessius` es queda només amb els 6 parells
  on el número casa als dos costats (meua→meva, meues→meves, seua→seva,
  seues→seves, teua→teva, teues→teves).

## Coses que abans venien d'altres fonts i ara ja no es cobrixen

Al retirar Apertium-368, Paula Guerrero i la majoria de les regles de
sufix, esta cobertura es va perdre (documentada ací perquè no quede
oblidada, no perquè s'haja d'arreglar sense que algú ho demane):

- Present d'indicatiu 1a conjugació (`parle→parlo`...), i pretèrit perfet
  simple → perifràstic (`celebrà→va celebrar`) (abans
  `morfologia_verbal.py`/`perfet.py`).
- Locucions fixes (`cap a on→cap on`, `dalt de→a dalt de`) i elisió
  automàtica general (`de escola→d'escola`) (abans
  `locucions.py`/`elisio.py`).

**Recuperat el mateix dia, més tard**: el patró general de gentilicis
`-és→-ès` per a QUALSEVOL paraula (no només les 695 enumerades a
`acentuacion_limpio.json`) i els incoatius `-ix→-eix` per a QUALSEVOL
verb (no només els enumerats a les conjugacions) van tornar com a regles
de sufix a `traductor/rules/accentuacio.py`/`incoatius.py` -- un pur
diccionari mai pot cobrir un patró obert i productiu.

**Recuperat el mateix dia, encara més tard**: `este/esta/estos/estes`,
`eixe/eixa/eixos/eixes`, `aqueix/aqueixa/aqueixos/aqueixes` (tots cap a
`aquest`) i el neutre `açò→això` van tornar a `traductor/rules/demostratius.py`,
sourced de `demostratius_avl.json` -- cap fitxer de `font_mauricio/` els
llista (són un paradigma gramatical tancat, no lèxic obert), però
retirar-los havia sigut un error: eren el patró MÉS FREQÜENT del corpus,
i el benchmark ho va confirmar de seguida (28/150 → 83/150 exactes en
recuperar-los).

**Afegit el mateix dia, més tard encara**: `flexio_genere_avl.json`
(dins de `lexic.py`) deriva gènere/nombre per a un grapat CURAT de
paraules amb variació real (`xiquet→nen` dona també `xiqueta→nena`,
`xiquets→nens`, `xiquetes→nenes`), més formes irregulars a mà
(`menut→menuda`, no "menuta" -- irregularitat participial). No és un
escaneig automàtic de `lexic_mauricio.json`: es va provar i la majoria
del lèxic són verbs/adverbis sense gènere, que haurien donat formes
absurdes. Benchmark: 83/150 → 92/150. Vore `traductor/README.md`, secció
"DECISIÓ D'ARQUITECTURA", per la cronologia completa de tota la sessió.
