*[Leer en castellano](README.es.md)*

# MaCoCu-ca: frases en català pur (filtrades per Grau Dialectal)

Trau de **MaCoCu-ca 1.0** les frases en català **pur** (GD 0 amb almenys
2 marcadors orientals), per a traduir-les després a valencià amb
AVLizador i tindre un corpus paral·lel català/valencià per a ajustar
algun model (decisió de l'usuari, 06/11/2026). **De moment no es
traduïx res**: només es filtra.

- Corpus: MaCoCu-ca 1.0, CLARIN.SI, `hdl 11356/1837`, CC0; web de 2022,
  5,9 M documents. Va en `dades/macocu/` (en el `.gitignore`).
- **Pas 1, `extreu`** (sense spaCy, ~1 hora): paràgrafs `good`, en
  català, no títols, no sensibles, `lm_score >= 0,7`; frases de 8 a 40
  paraules sense repetides; **prefiltre de GD segur** (spaCy només lleva
  marcadors, mai n'afig: el que no arriba a 2 possibles marcadors
  catalans o té un marcador valencià que no depén d'spaCy no pot eixir
  pur). Eixida: `candidates.jsonl`.
- **Pas 2, `gd`** (spaCy, en paral·lel i reprenible): `calcula_gd(...,
  dialecte="cat")`; es queden les de GD 0 amb almenys 2 marcadors.
  `--fraccio` per a una mostra uniforme i `--maxim` per a parar a N.
  Eixida: `catala_pur.jsonl`.

```bash
python pipeline/08_traduccio_corpus/macocu/filtra_macocu.py extreu
python pipeline/08_traduccio_corpus/macocu/filtra_macocu.py gd --processos 6 --fraccio 0.2
```

Mesures (06/11/2026): el prefiltre deixa passar el 13 % de les frases
vàlides, el 88 % de les quals són catalanes pures, i no en perd cap; el
pas 1 fa 200 MB en 49 s (~5 M candidates en total); el pas 2, ~90-100
candidates/s amb 6 processos (totes: ~13-15 h; el 20 %: ~3 h). Detall en
[README.es.md](README.es.md).
