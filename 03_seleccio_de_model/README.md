*[Llegeix-ho en castellà](README.es.md)*

# Etapa 3 — Selecció del model de traducció

Amb les regles dialectals ja definides (etapa 2), esta etapa decidix **quin
model** tradueix el corpus, comparant diverses opcions sobre un benchmark
de 150 frases amb referència humana (`03_seleccio_de_model/benchmark_corpus.json`,
tret del mateix corpus net de l'etapa 1).

## Ferramenta

`03_seleccio_de_model/evalua_models.py` — fa benchmark del model que li indiques
contra les 150 frases, calculant BLEU/chrF/chrF++ i % de traduccions
exactes. Ús:

```bash
python evalua_models.py --model ollama --ollama-model qwen2.5:14b
```

## Resultat final (amb les regles i el lèxic ja madurs)

| Model | BLEU | chrF | chrF++ | Exactes |
|---|---|---|---|---|
| **qwen2.5:14b** (triat) | **91,08** | **95,34** | **95,06** | **30/60 (50,0%)** |
| salamandra-7b-instruct (BSC) | 86,29 | 93,62 | 93,17 | 19/60 (31,7%) |
| Sistema de regles deterministes (sense LLM) | 80,5-85,9 | 91,3-95,5 | 90,3-94,5 | — |
| NLLB-200-distilled-600M | 53,13 | 76,67 | 75,00 | 0/60 |
| llama3.1:8b | 57,2-73,6 | 69,3-85,7 | 68,2-84,7 | — |
| qwen2.5:7b | 72,0-77,8 | 85,7-89,0 | 84,8-88,1 | — |

**Per què qwen2.5:14b**: millor qualitat i més consistent entre
execucions, amb marge de millora clar segons s'afinava el prompt (va pujar
de 84,02 a 91,08 BLEU sense canviar mai de model — tot el guany va vindre
de millorar el prompt i el lèxic a partir d'analitzar els errors reals). Es
va provar també salamandra-7b-instruct per ser la mitat de paràmetres (més
barat d'executar); va arribar a estar quasi empatada en un punt intermedi,
però va resultar ser un model més fràgil davant de canvis de prompt — de
vegades empitjorava en lloc de millorar en afegir-li més regles explícites.

Vore `../documentacio/metodologia_i_resultats.md` seccions 3, 5 i 6 per
a l'evolució completa, la comparativa detallada i els problemes trobats
amb cada model.
