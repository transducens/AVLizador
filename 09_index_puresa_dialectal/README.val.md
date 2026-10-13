*[Llig-ho en català](README.md)*

# `09_index_puresa_dialectal/` — Índex de Puresa Dialectal (IPD)

Novena etapa del projecte AVLizador (vore `README.es.md` de l'arrel):
mètrica per a saber, de qualsevol text, quin percentatge de les seues
paraules dialectalment marcades són formes **occidentals** (valencianes)
en compte de **orientals** (catalanes).

```
IPD = total_paraules_occidentals / (total_occidentals + total_orientals)
```

Un IPD d'1,0 vol dir que cap paraula catalana marcada apareix al text;
0,0 vol dir el contrari; i `None` (cap resultat) vol dir que el text no
conté cap paraula dialectalment marcada de les que coneix l'índex — no
es pot calcular un percentatge sobre zero.

## Per què un mòdul nou, si ja hi havia una mètrica pareguda

`01_extraccio_i_neteja/estudi_dialectal.py` ja calculava una cosa molt
pareguda (`ratio_occ`, a la seua tasca 1), pero contra dos llistes
curades a mà d'una huitantena de paraules cadascuna
(`OCCIDENTAL_MARKERS`/`ORIENTAL_MARKERS`, dins del mateix fitxer).
Este mòdul calcula el mateix índex, pero contra l'índex de parells
dialectals que `traductor/` ja manté per a traduir de veres:

| | Llistes antigues (`estudi_dialectal.py`) | Índex de l'IPD (`traductor/data/*.json`) |
|---|---|---|
| Grandària | ~70 paraules per dialecte | ~53.000 parells (1.471 de lèxic general + ~52.000 formes verbals conjugades + demostratius/possessius/numerals) |
| Font de veritat | Llista a banda, mantinguda a mà | La MATEIXA que fa servir el traductor per a traduir |
| Abast | Només documents ya carregats a `unified.jsonl` | Qualsevol text — una frase solta, un fitxer, un corpus JSONL |

No es reinventa cap dada nova: es reutilitzen directament els
carregadors (`carrega_lexic`, `carrega_conjugacions`,
`carrega_demostratius`, `carrega_numerals`, `carrega_possessius`...) de
`traductor/rules/val_cat/` i `traductor/rules/cat_val/`, en les dos
direccions (cada direcció resol l'ambigüitat pel seu costat, aixina que
fusionar-les dona mes cobertura que qualsevol de les dos soles).

## Limitació coneguda, acceptada de moment

Només compta paraules que apareixen LITERALMENT a algun diccionari de
lookup exacte. Els patrons PRODUCTIUS de sufix del motor (p.ex.
`-és`(occ)/`-ès`(or) d'`accentuacio.py`, o l'alternança incoativa
d'`incoatius.py`) encara no hi estan inclosos — cobrixen un patró obert
(qualsevol paraula que acabe aixina), no una llista tancada, i
barrejar-ho amb el lookup exacte en esta primera versió complicava el
disseny sense evidència encara de quant canviaria el resultat. Es queda
documentat com a ampliació pendent, no com un oblit.

## Ús

Com a script:

```bash
python ipd.py --text "Este xiquet vol vindre hui."
python ipd.py --fitxer un_document.txt
python ipd.py --corpus ../dades/avl/final/unified.jsonl --camp text --sortida resultat.json
```

Com a mòdul, des d'un atre script del projecte:

```python
from ipd import calcula_ipd

calcula_ipd("Este xiquet vol vindre hui.")["ipd"]  # -> 1.0
```

## Validació feta (13/10/2026)

Contra el benchmark de 151 frases de `03_seleccio_de_model/benchmark_corpus.json`
(el mateix que fa servir el traductor per a mesurar-se): el costat
valencià dona **IPD 0,9121** (353 marcadors occidentals, 34 orientals) i
el costat català **IPD 0,2062** (80 occidentals, 308 orientals) —
distinguix clarament els dos dialectes, tal com calia esperar.

## Relació amb la resta del projecte

Pendent documentat a `CLAUDE.md` (secció "Pendiente") i detallat a
`documentacio/hoja_de_ruta_ipd_y_proxima_fase.md`: este era el primer
pas a fer abans de seguir ampliant el motor de regles amb mes casos del
benchmark, i abans d'intentar una capa de model (LLM) nova per a
cat→val o de provar amb un corpus distint (el BOE).
