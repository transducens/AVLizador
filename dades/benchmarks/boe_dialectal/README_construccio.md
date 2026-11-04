# Benchmarks del BOE per al traductor

Tres benchmarks construïts a partir del BOE alineat català/valencià
(267.963 parells). Servixen per a mesurar el traductor `traductor/` sobre
text oficial real, sobretot en la direcció cat→val. Versió en castellà, amb
el detall complet: [README.es.md](README.es.md).

Format: llista de `{"id", "oriental", "occidental"}` (`oriental` = català,
`occidental` = valencià). Es generen tots amb una sola ordre, des de
l'arrel del repo (uns minuts; llavor 21, ixen idèntics):

```
python pipeline/05_corpus_boe/construeix_boe_dialectal.py
```

Esta carpeta està fora de git (`dades/`): si es perd, es torna a generar.

| Fitxer | Parells | Per a què servix |
|---|---|---|
| `benchmark_boe_mostra_2000.json` | 2.000 | Mostra general, sense filtrar (amb tot el soroll d'estil). |
| `benchmark_boe_dialectal_estricte.json` | 2.000 (de 9.453) | **Regressions.** Totes les diferències són dialectals segures. |
| `benchmark_boe_dialectal_ampli.json` | 2.000 (de 73.705) | **Buits.** Parells sense reformulació. |
| `*_complet.json` | 9.453 / 73.705 | Els conjunts sencers, per a anàlisi. |

**Ampli**: parells idèntics o amb només substitucions paraula per paraula
(blocs 1:1 de fins a 2 paraules; s'admet la "a" de "per a"). Sense
diccionari.

**Estricte**: de l'ampli, els parells amb almenys una diferència on totes
són dialectals segures: (a) parell dels diccionaris; (b) mateix lema i
mateixos trets segons spaCy, amb els mateixos clítics; (c) només canvia
l'accent ("entès"/"entés"); (d) "per a" + infinitiu; (e) incoatiu, amb la
mateixa transformació de `cat_val/incoatius.py`. Com que (a) usa el
diccionari, mesura regressions, no buits.

Ús, des de `pipeline/03_seleccio_de_model/`:

```
python evalua_models.py --model traductor --direccio cat-val --benchmark ../../dades/boe/benchmarks/benchmark_boe_dialectal_estricte.json
```

Resultats del motor cat→val (21/10/2026, camp `exactes` del JSON):
estricte **1.677/2.000 (83,9%)**, BLEU 96,87; ampli **1.177/2.000
(58,9%)**, BLEU 87,91; mostra general 458/2.000.
