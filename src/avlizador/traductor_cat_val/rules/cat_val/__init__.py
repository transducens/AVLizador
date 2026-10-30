"""
cat_val -- Direcció INVERSA del motor de reglas: català (oriental, norma
IEC) -> valencià (occidental, norma AVL/GVA). Companya de
`traductor/rules/*.py` (direcció original, val->cat), que es queda
exactament igual, sense tocar -- vore
`documentacio/hoja_de_ruta_traductor_invers.md` per al raonament complet
i `README.md`/`README.es.md` d'este paquet per a l'estat detallat.

Decisió de disseny (08/10/2026): esta direcció NO és "la mateixa regla
cap arrere" -- es construïx com a mòduls NOUS i independents (mai
movent ni reescrivint els de `rules/`), perquè la lògica de cada regla
sovint canvia de forma real (no és un simple flip de taula, vore la
hoja de ruta per als casos concrets: la col·lisió indicatiu/subjuntiu
de 3a plural desapareix en esta direcció, la de "persones"/"personis"
també, pero apareixen altres nos com "aquest"->"este"/"eixe"). El que SI
es reutilitza sense copiar: `Token`, `tokenize`/`detokenize` i tots els
helpers de `rules/__init__.py` (`separa_prefix_elidit`,
`aplica_amb_prefix_elidit`, `corregeix_determinant_abans`...),
`pos_tagger.py`, i els fitxers de dades de `traductor/data/*.json` --
cada un ja porta el camp `catalan` a mes del `valenciano`, així que no
calen fitxers nous, nomes carregadors nous que indexen per l'atre camp.
"""
