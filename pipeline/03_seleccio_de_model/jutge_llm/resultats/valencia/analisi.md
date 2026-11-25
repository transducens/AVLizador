# Jutge «valencia»: anàlisi (qwen3.6-35b-a3b_pensa)

## manual

### Trossos amb error

#### Prompt «valencia»

| Sistema | Trossos | En forma valenciana | En forma catalana | Neutres | No són en la frase | Formes valencianes més marcades |
|---|---|---|---|---|---|---|
| Referència | 245 | 70 (29 %) | 0 (0 %) | 159 (65 %) | 16 (7 %) | interés 7, comité 3, perjuí 3, este 3, díhuit 3, obri 2, establida 2, servicis 2, ferramenta 2, estés 2, ferramentes 2, depén 2 |
| AVLizador 2.0.1 | 125 | 66 (53 %) | 0 (0 %) | 49 (39 %) | 10 (8 %) | interés 6, comité 3, perjuí 3, díhuit 3, ferramenta 3, valdre 2, servicis 2, estés 2, bou 2, ferramentes 2, depén 2, vostés 2 |
| Sense traduir | 31 | 1 (3 %) | 12 (39 %) | 18 (58 %) | 0 (0 %) | abelleix 1 |
| gemma3:12b | 221 | 8 (4 %) | 6 (3 %) | 198 (90 %) | 9 (4 %) | suspés 2, influïsca 1, servici 1, reba 1, siga 1, vosté 1, valdre 1 |

#### Prompt del 04/11 (sense original), mateixes frases

| Sistema | Trossos | En forma valenciana | En forma catalana | Neutres | No són en la frase | Formes valencianes més marcades |
|---|---|---|---|---|---|---|
| AVLizador 2.0.0 | 924 | 449 (49 %) | 0 (0 %) | 416 (45 %) | 59 (6 %) | esta 55, este 34, seua 26, servicis 24, estos 14, seues 13, estes 12, tindre 11, sigut 10, haja 8, desenrotllament 8, servici 8 |
| Sense traduir | 641 | 5 (1 %) | 203 (32 %) | 395 (62 %) | 38 (6 %) | falta 2, abelleix 1, subjau 1, naixement 1 |
| gemma3:12b | 710 | 162 (23 %) | 97 (14 %) | 414 (58 %) | 37 (5 %) | seua 28, seues 18, siga 13, haja 12, ací 8, esta 8, hui 6, sigut 6, xiquets 3, naix 3, faça 3, mantindre 2 |
| Referència | 893 | 426 (48 %) | 0 (0 %) | 426 (48 %) | 41 (5 %) | esta 54, este 25, servicis 23, seua 18, sigut 13, seues 11, haja 10, tindre 10, estos 10, estes 9, siga 9, servici 8 |

### Categories dels errors

| Sistema | Part | Frases | accuracy | fluency | style | terminology | altres | Majors |
|---|---|---|---|---|---|---|---|---|
| Referència | AVL | 212 | 4 | 23 | 0 | 5 | 4 | 2 |
| Referència | BOE | 245 | 86 | 96 | 6 | 9 | 12 | 53 |
| AVLizador 2.0.1 | AVL | 212 | 3 | 25 | 0 | 6 | 5 | 2 |
| AVLizador 2.0.1 | BOE | 246 | 7 | 61 | 0 | 9 | 9 | 10 |
| Sense traduir | AVL | 212 | 2 | 17 | 0 | 0 | 4 | 1 |
| Sense traduir | BOE | 246 | 0 | 6 | 0 | 1 | 1 | 1 |
| gemma3:12b | AVL | 212 | 42 | 39 | 2 | 3 | 5 | 31 |
| gemma3:12b | BOE | 246 | 40 | 71 | 1 | 14 | 4 | 31 |

### Frases distintes de la referència

«Marca alguna paraula canviada» = algun tros amb error del sistema toca una paraula que no és en la referència. Detall en `analisi_detall.md`.

| Sistema | Frases distintes | Marca alguna paraula canviada | Guanya la ref. | Empat | Guanya el sistema |
|---|---|---|---|---|---|
| AVLizador 2.0.1 | 225 | 7 | 22 | 100 | 103 |
| Sense traduir | 456 | 14 | 18 | 263 | 175 |
| gemma3:12b | 446 | 144 | 120 | 202 | 124 |

## homografs

### Trossos amb error

#### Prompt «valencia»

| Sistema | Trossos | En forma valenciana | En forma catalana | Neutres | No són en la frase | Formes valencianes més marcades |
|---|---|---|---|---|---|---|
| Referència | 34 | 19 (56 %) | 0 (0 %) | 11 (32 %) | 4 (12 %) | sigut 3, portugués 2, espentar 1, ségol 1, francés 1, este 1, aragonés 1, vosté 1, ensenyança 1, interés 1, mentres 1, huit 1 |
| AVLizador 2.0.1 | 43 | 24 (56 %) | 0 (0 %) | 15 (35 %) | 4 (9 %) | sigut 3, portugués 2, llavar 1, espentar 1, avena 1, ségol 1, francés 1, este 1, aragonés 1, vosté 1, interés 1, huit 1 |
| Motor sol | 59 | 39 (66 %) | 0 (0 %) | 16 (27 %) | 4 (7 %) | bragues 6, hamaca 5, hamaques 4, sigut 3, portugués 2, llavar 1, espentar 1, avena 1, ségol 1, francés 1, anou 1, este 1 |

### Categories dels errors

| Sistema | Part | Frases | accuracy | fluency | style | terminology | altres | Majors |
|---|---|---|---|---|---|---|---|---|
| Referència | — | 248 | 6 | 27 | 0 | 0 | 1 | 4 |
| AVLizador 2.0.1 | — | 248 | 11 | 31 | 0 | 0 | 1 | 11 |
| Motor sol | — | 248 | 27 | 31 | 0 | 0 | 1 | 27 |

### Frases distintes de la referència

«Marca alguna paraula canviada» = algun tros amb error del sistema toca una paraula que no és en la referència. Detall en `analisi_detall.md`.

| Sistema | Frases distintes | Marca alguna paraula canviada | Guanya la ref. | Empat | Guanya el sistema |
|---|---|---|---|---|---|
| AVLizador 2.0.1 | 21 | 6 | 5 | 11 | 5 |
| Motor sol | 70 | 22 | 24 | 44 | 2 |

Per canvi (referència → sistema; quantes frases guanya la referència / empat / el sistema):

| Sistema | Canvi | Guanya la ref. | Empat | Guanya el sistema |
|---|---|---|---|---|
| AVLizador 2.0.1 | bragues→calces | 0 | 2 | 1 |
| AVLizador 2.0.1 | falta→manca | 0 | 2 | 0 |
| AVLizador 2.0.1 | faltes→manques | 0 | 1 | 1 |
| AVLizador 2.0.1 | hamaques→gandules | 0 | 1 | 1 |
| AVLizador 2.0.1 | anous→nous | 0 | 1 | 0 |
| AVLizador 2.0.1 | anou→nou | 0 | 0 | 1 |
| AVLizador 2.0.1 | cinqué sisé→quint sext | 1 | 0 | 0 |
| AVLizador 2.0.1 | civada→avena | 1 | 0 | 0 |
| AVLizador 2.0.1 | confinis→confines; finis→fines | 1 | 0 | 0 |
| AVLizador 2.0.1 | ensenyament→ensenyança | 1 | 0 | 0 |
| AVLizador 2.0.1 | esmentat→mencionat | 0 | 1 | 0 |
| AVLizador 2.0.1 | llavadora→rentadora | 0 | 1 | 0 |
| AVLizador 2.0.1 | mentres→mentre | 0 | 0 | 1 |
| AVLizador 2.0.1 | oferides→ofertes | 0 | 1 | 0 |
| AVLizador 2.0.1 | rentar→llavar | 1 | 0 | 0 |
| AVLizador 2.0.1 | valencià→valenciana | 0 | 1 | 0 |
| Motor sol | colp→cop | 0 | 11 | 0 |
| Motor sol | nou→anou | 2 | 5 | 0 |
| Motor sol | vegada→cop | 0 | 7 | 0 |
| Motor sol | colps→cops | 0 | 6 | 0 |
| Motor sol | calces→bragues | 5 | 0 | 0 |
| Motor sol | gandula→hamaca | 4 | 0 | 0 |
| Motor sol | gandules→hamaques | 3 | 0 | 0 |
| Motor sol | manca→falta | 2 | 1 | 0 |
| Motor sol | fartanera→fartada | 2 | 0 | 0 |
| Motor sol | manques→faltes | 0 | 2 | 0 |
| Motor sol | nous→anous | 1 | 1 | 0 |
| Motor sol | vegades→cops | 0 | 2 | 0 |
| Motor sol | algunes vegades→alguns cops | 0 | 0 | 1 |
| Motor sol | altra vegada→altre cop | 0 | 1 | 0 |
| Motor sol | cinqué sisé→quint sext | 1 | 0 | 0 |
| Motor sol | civada→avena | 1 | 0 | 0 |
| Motor sol | confinis→confines; finis→fines | 1 | 0 | 0 |
| Motor sol | diverses vegades→diversos cops | 0 | 1 | 0 |
| Motor sol | ensenyament→ensenyança | 1 | 0 | 0 |
| Motor sol | esmentat→mencionat | 0 | 1 | 0 |
| Motor sol | esta vegada→este cop | 0 | 1 | 0 |
| Motor sol | mentres→mentre | 0 | 0 | 1 |
| Motor sol | moltes vegades→molts cops | 0 | 1 | 0 |
| Motor sol | oferides→ofertes | 0 | 1 | 0 |
| Motor sol | primera vegada→primer cop | 0 | 1 | 0 |
| Motor sol | quantes vegades→quants cops | 0 | 1 | 0 |
| Motor sol | rentar→llavar | 1 | 0 | 0 |
| Motor sol | valencià→valenciana | 0 | 1 | 0 |

## homografs_v2

### Trossos amb error

#### Prompt «valencia»

| Sistema | Trossos | En forma valenciana | En forma catalana | Neutres | No són en la frase | Formes valencianes més marcades |
|---|---|---|---|---|---|---|
| Referència | 17 | 11 (65 %) | 0 (0 %) | 5 (29 %) | 1 (6 %) | bragues 3, panolles 2, anou 1, ensalada 1, faltes 1, hamaca 1, hamaques 1, depén 1 |
| AVLizador 2.0.1 | 12 | 6 (50 %) | 0 (0 %) | 5 (42 %) | 1 (8 %) | panolles 2, anou 1, ensalada 1, hamaca 1, depén 1 |
| Motor sol | 48 | 37 (77 %) | 0 (0 %) | 11 (23 %) | 0 (0 %) | bragues 6, faltes 5, hamaca 5, hamaques 5, falta 3, llavadora 3, panolles 3, llavadores 2, anou 1, ensalada 1, anous 1, depén 1 |

### Categories dels errors

| Sistema | Part | Frases | accuracy | fluency | style | terminology | altres | Majors |
|---|---|---|---|---|---|---|---|---|
| Referència | — | 144 | 8 | 4 | 0 | 3 | 2 | 9 |
| AVLizador 2.0.1 | — | 144 | 5 | 2 | 0 | 3 | 2 | 6 |
| Motor sol | — | 144 | 37 | 3 | 0 | 6 | 2 | 40 |

### Frases distintes de la referència

«Marca alguna paraula canviada» = algun tros amb error del sistema toca una paraula que no és en la referència. Detall en `analisi_detall.md`.

| Sistema | Frases distintes | Marca alguna paraula canviada | Guanya la ref. | Empat | Guanya el sistema |
|---|---|---|---|---|---|
| AVLizador 2.0.1 | 31 | 2 | 2 | 22 | 7 |
| Motor sol | 69 | 33 | 38 | 29 | 2 |

Per canvi (referència → sistema; quantes frases guanya la referència / empat / el sistema):

| Sistema | Canvi | Guanya la ref. | Empat | Guanya el sistema |
|---|---|---|---|---|
| AVLizador 2.0.1 | bragues→calces | 0 | 1 | 3 |
| AVLizador 2.0.1 | faltes→manques | 0 | 3 | 1 |
| AVLizador 2.0.1 | hamaques→gandules | 0 | 2 | 1 |
| AVLizador 2.0.1 | llavadora→rentadora | 0 | 3 | 0 |
| AVLizador 2.0.1 | llavadores→rentadores | 1 | 2 | 0 |
| AVLizador 2.0.1 | anous→nous | 0 | 2 | 0 |
| AVLizador 2.0.1 | exitosa→reeixida | 0 | 2 | 0 |
| AVLizador 2.0.1 | falta→manca | 0 | 2 | 0 |
| AVLizador 2.0.1 | panolles→panotxes | 0 | 2 | 0 |
| AVLizador 2.0.1 | exitoses→reeixides | 0 | 1 | 0 |
| AVLizador 2.0.1 | fartada→fartanera | 0 | 1 | 0 |
| AVLizador 2.0.1 | fartades→fartaneres | 0 | 0 | 1 |
| AVLizador 2.0.1 | fartades→fartaneres; síndria→meló alger | 1 | 0 | 0 |
| AVLizador 2.0.1 | freda→fred | 0 | 0 | 1 |
| AVLizador 2.0.1 | panolla→panotxa | 0 | 1 | 0 |
| Motor sol | manques→faltes | 5 | 3 | 0 |
| Motor sol | nou→anou | 3 | 5 | 0 |
| Motor sol | manca→falta | 4 | 3 | 0 |
| Motor sol | calces→bragues | 3 | 1 | 0 |
| Motor sol | fartanera→fartada | 3 | 1 | 0 |
| Motor sol | fartaneres→fartades | 3 | 1 | 0 |
| Motor sol | gandula→hamaca | 4 | 0 | 0 |
| Motor sol | gandules→hamaques | 4 | 0 | 0 |
| Motor sol | nous→anous | 1 | 3 | 0 |
| Motor sol | panotxa→panolla | 0 | 4 | 0 |
| Motor sol | panotxes→panolles | 1 | 3 | 0 |
| Motor sol | rentadora→llavadora | 3 | 1 | 0 |
| Motor sol | rentadores→llavadores | 2 | 1 | 1 |
| Motor sol | reeixides→exitoses | 1 | 1 | 0 |
| Motor sol | brollador→deu | 0 | 1 | 0 |
| Motor sol | exitoses→reeixides | 0 | 1 | 0 |
| Motor sol | freda→fred | 0 | 0 | 1 |
| Motor sol | síndria→meló alger | 1 | 0 | 0 |
