*[Leer en castellano](README.es.md)*

# MaCoCu-ca: corpus web català, filtrat per Grau Dialectal

Treball amb **MaCoCu-ca 1.0** (CLARIN.SI, `hdl 11356/1837`, CC0; web de
2022, 5,9 M documents) per a tindre dades d'entrenament: frases
catalanes pures traduïdes a valencià (corpus paral·lel), frases
valencianes reals del mateix corpus i un primer KenLM amb tot el corpus
per a substituir FLOR (decisions de l'usuari, 06/11 i 09/11/2026).

| Carpeta / fitxer | Què hi ha |
|---|---|
| [`comu.py`](comu.py) | Lectura del XML (o del `.zip`), paràgrafs, frases, frase vàlida i paràgraf bo |
| [`catala/`](catala/README.md) | `filtra_macocu.py` (GD 0, català pur) i `tradueix_macocu.py` (traducció amb AVLizador) |
| [`valencia/`](valencia/README.md) | `filtra_valencia.py` (GD > 0,5, formes valencianes) |
| [`analitza_macocu.py`](analitza_macocu.py) | Anàlisi del corpus sencer sense filtrar |
| [`kenlm/`](kenlm/README.md) | KenLM amb tot MaCoCu sense filtrar |

Dades (fora de git): `dades/macocu/` (corpus i eixides del català),
`dades/macocu/valencia/` i `dades/macocu/kenlm/`.

**Anàlisi del corpus sencer sense filtrar (`analitza_macocu.py`,
09/11/2026)**: 1.772,5 M de paraules; GD d'una mostra del 2 % dels
documents (1,8 M de frases): GD global 0,185, 63 % de frases sense
marcadors, 28 % catalanes pures, 5,1 % amb GD 1, però només el 58 %
d'estes amb algun marcador valencià fort (la resta són "vegada",
"permet", "alcalde"...): el valencià real ronda el 3 % de les frases.
Les formes valencianes que decidix FLOR són rarissimes ("colp" 6.789
davant de 596.367 "cop"; "anou" 237 davant d'1,2 M de "nou"). Detall en
[README.es.md](README.es.md).
