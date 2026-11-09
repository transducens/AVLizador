*[Leer en castellano](README.es.md)*

# MaCoCu-ca: frases amb formes valencianes (GD > 0,5)

Trau de **MaCoCu-ca 1.0** les frases amb formes valencianes: **GD > 0,5**
(més marcadors occidentals que orientals), per a tindre valencià real
del corpus (decisió de l'usuari, 09/11/2026). És el filtre simètric del
català ([`../catala/`](../catala/README.md)); compartix amb ell la
lectura del corpus ([`../comu.py`](../comu.py)).

- **Pas 1, `extreu`** (sense spaCy): els mateixos paràgrafs i frases que
  el filtre català (els paràgrafs en castellà queden fora: "este",
  "alcalde", "vos" hi serien marcadors) i un **prefiltre segur**: cota
  superior dels occidentals i inferior dels orientals; si no pot donar
  GD > 0,5, fora. Eixida: `dades/macocu/valencia/candidates.jsonl`.
- **Pas 2, `gd`** (spaCy, en paral·lel i reprenible): GD > `--min-gd`
  (0,5) amb almenys `--min-marcadors` (1). Eixida:
  `dades/macocu/valencia/valencia.jsonl`, amb els marcadors de cada frase.

```bash
python pipeline/08_traduccio_corpus/macocu/valencia/filtra_valencia.py extreu
python pipeline/08_traduccio_corpus/macocu/valencia/filtra_valencia.py gd --processos 6
sbatch filtra_valencia.sh        # en Abaco, des d'esta carpeta
```

Mesures (09/11/2026): el prefiltre no perd cap frase (26.412 provades);
els primers 100 MB donen 18.119 frases (6,9 % de les vàlides), ~3 M en
el corpus sencer. El 83 % tenen un sol marcador, sovint dels falsos
("vegada", "fem", "permet", "alcalde"); amb ≥2 marcadors queda el 17 %.
Detall en [README.es.md](README.es.md).
