# Corpus sintètic d'homògrafs — instruccions de generació (25/11/2026)

Prova a banda: NO forma part del sistema ni es barreja amb el corpus real
(MaCoCu/DOGV). Serveix per a entrenar/avaluar un classificador de sentit de
prova per als homògrafs que tenen poques frases reals.

## Format

Un fitxer JSONL per grup (`<grup>.jsonl`), una frase per línia:

```json
{"id": "FART-T-001", "grup": "fartanera", "classe": "tradueix", "forma_cat": "fartanera", "forma_val": "fartada", "sentit": "atracada de menjar", "catala": "...", "valencia": "..."}
```

- `classe`: `tradueix` (sentit en què el català es tradueix per la forma
  valenciana) o `es_queda` (sentit en què la paraula catalana es queda igual
  en valencià).
- `forma_cat` / `forma_val`: la forma exacta que apareix en cada frase
  (singular o plural). En `es_queda`, les dues són iguals.
- `catala`: frase en català central estàndard (aquest, -eix, subjuntiu en
  -i, avui, aquí, nen, sortir, tenir, meva/seva, servei...).
- `valencia`: la mateixa frase en valencià normatiu de l'AVL (este/eixe,
  -ix, subjuntiu en -e/-a, hui, ací, xiquet, eixir, tindre, meua/seua,
  servici...). "veure" és correcte (no cal "vore").
- La frase valenciana és la traducció fidel de la catalana: mateix
  significat, només canvien les formes dialectals i la paraula objectiu.

## Regles

1. 8-30 paraules, frase completa, amb punt final. Una sola aparició de la
   paraula objectiu per frase.
2. El context ha de deixar clar el sentit (una persona que la llija sense
   saber res ha d'entendre quin sentit és), però sense repetir sempre les
   mateixes pistes: varia el lèxic del voltant.
3. Varietat: registres (notícia, administració, conversa, literatura,
   receptes, esport, ciència, història...), posició en la frase (inici,
   mig, final), singular i plural, amb article, amb "un/una", amb
   demostratiu, amb possessiu, sense determinant, en títols de persona,
   davant d'adjectiu, en coordinació...
4. Concordança correcta en cada llengua (atenció als canvis de gènere: "la
   deu freda" → "el brollador fred"; "la nou" → "l'anou").
5. Cap altra paraula ambigua del lèxic en la mateixa frase: cop/cops,
   colp, vegada, deu/deus, nou/nous, manca/manques, calces, gandula,
   rentadora, reeixida, panotxa, fartanera (llevat de la paraula objectiu).
   Per a "moltes voltes" usa "sovint"; evita els números 9 i 10 en lletres.
6. Sense noms de persones reals ni marques. Frases originals: no copies
   frases de diccionari ni dels benchmarks del repositori.
7. Res de frases metalingüístiques ("la paraula X vol dir...").
