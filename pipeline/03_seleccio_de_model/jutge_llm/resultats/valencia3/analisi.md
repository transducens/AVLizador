# Jutge «valencia3»: anàlisi (qwen3.6-35b-a3b_pensa)

## homografs

### Trossos amb error

#### Prompt «valencia3»

| Sistema | Trossos | En forma valenciana | En forma catalana | Neutres | No són en la frase | Formes valencianes més marcades |
|---|---|---|---|---|---|---|
| Referència | 26 | 4 (15 %) | 0 (0 %) | 21 (81 %) | 1 (4 %) | llavar 1, espentar 1, ségol 1, sigut 1 |
| AVLizador 2.0.1 | 41 | 3 (7 %) | 0 (0 %) | 37 (90 %) | 1 (2 %) | espentar 1, avena 1, sigut 1 |
| Motor sol | 57 | 19 (33 %) | 23 (40 %) | 14 (25 %) | 1 (2 %) | anou 7, hamaca 4, hamaques 3, anous 2, espentar 1, avena 1, sigut 1 |

### Categories dels errors

| Sistema | Part | Frases | accuracy | fluency | style | terminology | altres | Majors |
|---|---|---|---|---|---|---|---|---|
| Referència | — | 248 | 6 | 12 | 0 | 6 | 2 | 2 |
| AVLizador 2.0.1 | — | 248 | 12 | 12 | 0 | 15 | 2 | 7 |
| Motor sol | — | 248 | 27 | 17 | 0 | 8 | 5 | 14 |

### Frases distintes de la referència

«Marca alguna paraula canviada» = algun tros amb error del sistema toca una paraula que no és en la referència. Detall en `analisi_detall.md`.

| Sistema | Frases distintes | Marca alguna paraula canviada | Guanya la ref. | Empat | Guanya el sistema |
|---|---|---|---|---|---|
| AVLizador 2.0.1 | 21 | 15 | 12 | 7 | 2 |
| Motor sol | 70 | 42 | 39 | 23 | 8 |

Per canvi (referència → sistema; quantes frases guanya la referència / empat / el sistema):

| Sistema | Canvi | Guanya la ref. | Empat | Guanya el sistema |
|---|---|---|---|---|
| AVLizador 2.0.1 | bragues→calces | 3 | 0 | 0 |
| AVLizador 2.0.1 | falta→manca | 2 | 0 | 0 |
| AVLizador 2.0.1 | faltes→manques | 1 | 1 | 0 |
| AVLizador 2.0.1 | hamaques→gandules | 1 | 0 | 1 |
| AVLizador 2.0.1 | anous→nous | 1 | 0 | 0 |
| AVLizador 2.0.1 | anou→nou | 0 | 1 | 0 |
| AVLizador 2.0.1 | cinqué sisé→quint sext | 0 | 1 | 0 |
| AVLizador 2.0.1 | civada→avena | 1 | 0 | 0 |
| AVLizador 2.0.1 | confinis→confines; finis→fines | 1 | 0 | 0 |
| AVLizador 2.0.1 | ensenyament→ensenyança | 0 | 1 | 0 |
| AVLizador 2.0.1 | esmentat→mencionat | 0 | 1 | 0 |
| AVLizador 2.0.1 | llavadora→rentadora | 1 | 0 | 0 |
| AVLizador 2.0.1 | mentres→mentre | 0 | 1 | 0 |
| AVLizador 2.0.1 | oferides→ofertes | 0 | 1 | 0 |
| AVLizador 2.0.1 | rentar→llavar | 0 | 0 | 1 |
| AVLizador 2.0.1 | valencià→valenciana | 1 | 0 | 0 |
| Motor sol | colp→cop | 7 | 4 | 0 |
| Motor sol | nou→anou | 7 | 0 | 0 |
| Motor sol | vegada→cop | 3 | 4 | 0 |
| Motor sol | colps→cops | 5 | 1 | 0 |
| Motor sol | calces→bragues | 0 | 1 | 4 |
| Motor sol | gandula→hamaca | 4 | 0 | 0 |
| Motor sol | gandules→hamaques | 3 | 0 | 0 |
| Motor sol | manca→falta | 0 | 3 | 0 |
| Motor sol | fartanera→fartada | 0 | 1 | 1 |
| Motor sol | manques→faltes | 0 | 0 | 2 |
| Motor sol | nous→anous | 2 | 0 | 0 |
| Motor sol | vegades→cops | 0 | 2 | 0 |
| Motor sol | algunes vegades→alguns cops | 0 | 1 | 0 |
| Motor sol | altra vegada→altre cop | 1 | 0 | 0 |
| Motor sol | cinqué sisé→quint sext | 0 | 1 | 0 |
| Motor sol | civada→avena | 1 | 0 | 0 |
| Motor sol | confinis→confines; finis→fines | 1 | 0 | 0 |
| Motor sol | diverses vegades→diversos cops | 1 | 0 | 0 |
| Motor sol | ensenyament→ensenyança | 0 | 1 | 0 |
| Motor sol | esmentat→mencionat | 0 | 1 | 0 |
| Motor sol | esta vegada→este cop | 1 | 0 | 0 |
| Motor sol | mentres→mentre | 0 | 1 | 0 |
| Motor sol | moltes vegades→molts cops | 1 | 0 | 0 |
| Motor sol | oferides→ofertes | 0 | 1 | 0 |
| Motor sol | primera vegada→primer cop | 1 | 0 | 0 |
| Motor sol | quantes vegades→quants cops | 0 | 1 | 0 |
| Motor sol | rentar→llavar | 0 | 0 | 1 |
| Motor sol | valencià→valenciana | 1 | 0 | 0 |

## homografs_v2

### Trossos amb error

#### Prompt «valencia3»

| Sistema | Trossos | En forma valenciana | En forma catalana | Neutres | No són en la frase | Formes valencianes més marcades |
|---|---|---|---|---|---|---|
| Referència | 46 | 2 (4 %) | 2 (4 %) | 42 (91 %) | 0 (0 %) | anou 1, omplin 1 |
| AVLizador 2.0.1 | 74 | 2 (3 %) | 5 (7 %) | 67 (91 %) | 0 (0 %) | anou 1, omplin 1 |
| Motor sol | 39 | 28 (72 %) | 0 (0 %) | 11 (28 %) | 0 (0 %) | anou 9, anous 4, hamaca 4, hamaques 4, falta 2, faltes 2, llavadores 1, omplin 1, exitoses 1 |

### Categories dels errors

| Sistema | Part | Frases | accuracy | fluency | style | terminology | altres | Majors |
|---|---|---|---|---|---|---|---|---|
| Referència | — | 144 | 13 | 7 | 0 | 26 | 0 | 5 |
| AVLizador 2.0.1 | — | 144 | 17 | 7 | 0 | 50 | 0 | 10 |
| Motor sol | — | 144 | 24 | 9 | 0 | 6 | 0 | 18 |

### Frases distintes de la referència

«Marca alguna paraula canviada» = algun tros amb error del sistema toca una paraula que no és en la referència. Detall en `analisi_detall.md`.

| Sistema | Frases distintes | Marca alguna paraula canviada | Guanya la ref. | Empat | Guanya el sistema |
|---|---|---|---|---|---|
| AVLizador 2.0.1 | 31 | 28 | 27 | 3 | 1 |
| Motor sol | 69 | 29 | 30 | 12 | 27 |

Per canvi (referència → sistema; quantes frases guanya la referència / empat / el sistema):

| Sistema | Canvi | Guanya la ref. | Empat | Guanya el sistema |
|---|---|---|---|---|
| AVLizador 2.0.1 | bragues→calces | 3 | 1 | 0 |
| AVLizador 2.0.1 | faltes→manques | 3 | 1 | 0 |
| AVLizador 2.0.1 | hamaques→gandules | 2 | 0 | 1 |
| AVLizador 2.0.1 | llavadora→rentadora | 3 | 0 | 0 |
| AVLizador 2.0.1 | llavadores→rentadores | 3 | 0 | 0 |
| AVLizador 2.0.1 | anous→nous | 2 | 0 | 0 |
| AVLizador 2.0.1 | exitosa→reeixida | 2 | 0 | 0 |
| AVLizador 2.0.1 | falta→manca | 2 | 0 | 0 |
| AVLizador 2.0.1 | panolles→panotxes | 2 | 0 | 0 |
| AVLizador 2.0.1 | exitoses→reeixides | 1 | 0 | 0 |
| AVLizador 2.0.1 | fartada→fartanera | 1 | 0 | 0 |
| AVLizador 2.0.1 | fartades→fartaneres | 1 | 0 | 0 |
| AVLizador 2.0.1 | fartades→fartaneres; síndria→meló alger | 1 | 0 | 0 |
| AVLizador 2.0.1 | freda→fred | 0 | 1 | 0 |
| AVLizador 2.0.1 | panolla→panotxa | 1 | 0 | 0 |
| Motor sol | manques→faltes | 2 | 3 | 3 |
| Motor sol | nou→anou | 8 | 0 | 0 |
| Motor sol | manca→falta | 2 | 3 | 2 |
| Motor sol | calces→bragues | 0 | 0 | 4 |
| Motor sol | fartanera→fartada | 1 | 1 | 2 |
| Motor sol | fartaneres→fartades | 0 | 1 | 3 |
| Motor sol | gandula→hamaca | 4 | 0 | 0 |
| Motor sol | gandules→hamaques | 4 | 0 | 0 |
| Motor sol | nous→anous | 4 | 0 | 0 |
| Motor sol | panotxa→panolla | 0 | 0 | 4 |
| Motor sol | panotxes→panolles | 0 | 0 | 4 |
| Motor sol | rentadora→llavadora | 1 | 2 | 1 |
| Motor sol | rentadores→llavadores | 1 | 1 | 2 |
| Motor sol | reeixides→exitoses | 0 | 0 | 2 |
| Motor sol | brollador→deu | 1 | 0 | 0 |
| Motor sol | exitoses→reeixides | 1 | 0 | 0 |
| Motor sol | freda→fred | 0 | 1 | 0 |
| Motor sol | síndria→meló alger | 1 | 0 | 0 |
