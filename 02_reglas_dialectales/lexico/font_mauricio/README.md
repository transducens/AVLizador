# Font: diccionari de Mauricio (equip AVLizador, 29/09/2026)

Estos 4 fitxers són el diccionari català-valencià que Mauricio va compartir
per correu el 29/09/2026, basat majoritàriament en l'apertium bilingüe
català-castellà. Es guarden ací sense modificar, tal com es van rebre (a
`por_colocar/` originalment), com a font d'evidència -- el mateix criteri
que la resta d'esta carpeta (`apertium_368_val_cat.json`,
`contrastius_paula_guerrero.json`...).

Estat de cada fitxer (què s'ha incorporat al motor i què no, i per què):

- **`conjugaciones_limpio.json`** (969 formes, 111 verbs) -- INCORPORAT
  quasi sencer: `traductor/data/conjugacions_dialectals.json` en conté una
  còpia amb metadades, i `traductor/rules/conjugacions_dict.py` fa el
  lookup en temps real. Les 65 formes marcades `problematica: true`
  s'exclouen del lookup (ambigües entre indicatiu i subjuntiu sense
  pos-tagging), però es queden documentades al JSON per si en el futur
  s'afig un mecanisme de desambiguació.

- **`lexico_general_limpio.json`** (611 entrades) -- INCORPORAT
  PARCIALMENT: 150 entrades noves (no-topònim, no `_PENDENT`, sense
  conflicte amb una entrada ja revisada a mà) es van afegir a
  `lexico_fiable.json` amb `"origen": "mauricio_apertium"`. Es van
  EXCLOURE:
  - 151 entrades `_PENDENT` (el propi fitxer les marca com a no
    verificades).
  - 73 topònims (`tipo: "v:top_gva"`, p.ex. "Ademuz"→"Ademús"): el motor
    protegix tots els noms propis de traducció (`is_proper_noun` a
    `rules/__init__.py`), així que encara que s'afigueren mai
    s'aplicarien. Cal decidir primer si els topònims han de traduir-se en
    absolut i com distingir-los d'altres noms propis -- pendent.
  - 9 entrades en conflicte amb `lexico_fiable.json` ja existent
    (`xicotet`, `prompte`, `despús-ahir`, `corder`, `abellir`,
    `espentar`, `pitxer`, `redonesa`; "xiquet" també aparixia com a
    conflicte aparent però en realitat ja hi havia l'entrada correcta
    `xiquet→nen`) -- l'entrada ja revisada a mà sempre guanya.
  - 11 entrades on `valenciano == catalan` (sense diferència real) i les
    que tenen el valencià en més d'una paraula (`"els dos"`), que
    `LexicRule` no pot tractar (fa lookup d'un sol token).

- **`acentuacion_limpio.json`** (694 entrades) -- NO incorporat com a
  dades noves, es va usar només com a VALIDACIÓ: confirma que les
  excepcions de `gentilicis.py` (`només`, `procés`, `congrés`, `accés`,
  `progrés`, `través`) NO apareixen ací (correcte, no seguixen el patró),
  i que `interés`/`després` sí ("després" ja estava exclosa a
  `gentilicis.py` per motiu propi -- vore eixe mòdul). La immensa majoria
  de la resta (414/693 amb diferència real) ja la cobrix la regla de
  sufix general `-és→-ès` existent, sense necessitat de llista.

- **`numerales_limpio.json`** (180 entrades) -- INCORPORAT PARCIALMENT:
  només les arrels "dinou"/"disset" i els seus 8 derivats (10 entrades en
  total, a `numerals.py`), perquè no comparteixen subcadena amb
  l'oriental i per tant no els cobria la substitució `huit→vuit`. La
  resta (família huit/vuit, 166 entrades) ja quedava coberta correctament
  per eixa substitució de subcadena -- comprovat una a una. Nota de
  qualitat de dades: 4 entrades de "vuitavat" semblen una extracció
  trencada (mateix català repetit per a 4 valencians diferents); no
  s'han incorporat explícitament, però ja contenen "huit" com a
  subcadena així que la substitució genèrica els tracta raonablement bé.
