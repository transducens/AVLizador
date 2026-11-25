# Jutge «valencia2»: anàlisi (qwen3.6-35b-a3b_pensa)

## homografs

### Trossos amb error

#### Prompt «valencia2»

| Sistema | Trossos | En forma valenciana | En forma catalana | Neutres | No són en la frase | Formes valencianes més marcades |
|---|---|---|---|---|---|---|
| Referència | 42 | 29 (69 %) | 0 (0 %) | 12 (29 %) | 1 (2 %) | colp 5, bragues 4, colps 3, anou 3, ensenyança 2, espentar 1, teuladins 1, ségol 1, galletes 1, sigut 1, francés 1, vosté 1 |
| AVLizador 2.0.1 | 49 | 30 (61 %) | 0 (0 %) | 17 (35 %) | 2 (4 %) | colp 5, ensenyança 3, colps 3, bragues 2, anou 2, llavar 1, espentar 1, teuladins 1, avena 1, ségol 1, galletes 1, sigut 1 |
| Motor sol | 67 | 46 (69 %) | 0 (0 %) | 19 (28 %) | 2 (3 %) | anou 9, bragues 9, hamaca 4, hamaques 4, ensenyança 3, anous 2, llavar 1, espentar 1, teuladins 1, avena 1, ségol 1, galletes 1 |

### Categories dels errors

| Sistema | Part | Frases | accuracy | fluency | style | terminology | altres | Majors |
|---|---|---|---|---|---|---|---|---|
| Referència | — | 248 | 8 | 31 | 0 | 0 | 3 | 7 |
| AVLizador 2.0.1 | — | 248 | 14 | 31 | 0 | 1 | 3 | 9 |
| Motor sol | — | 248 | 28 | 35 | 0 | 1 | 3 | 25 |

### Frases distintes de la referència

«Marca alguna paraula canviada» = algun tros amb error del sistema toca una paraula que no és en la referència. Detall en `analisi_detall.md`.

| Sistema | Frases distintes | Marca alguna paraula canviada | Guanya la ref. | Empat | Guanya el sistema |
|---|---|---|---|---|---|
| AVLizador 2.0.1 | 21 | 6 | 6 | 10 | 5 |
| Motor sol | 70 | 29 | 30 | 31 | 9 |

Per canvi (referència → sistema; quantes frases guanya la referència / empat / el sistema):

| Sistema | Canvi | Guanya la ref. | Empat | Guanya el sistema |
|---|---|---|---|---|
| AVLizador 2.0.1 | bragues→calces | 0 | 1 | 2 |
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
| AVLizador 2.0.1 | mentres→mentre | 0 | 1 | 0 |
| AVLizador 2.0.1 | oferides→ofertes | 0 | 1 | 0 |
| AVLizador 2.0.1 | rentar→llavar | 1 | 0 | 0 |
| AVLizador 2.0.1 | valencià→valenciana | 1 | 0 | 0 |
| Motor sol | colp→cop | 0 | 6 | 5 |
| Motor sol | nou→anou | 6 | 1 | 0 |
| Motor sol | vegada→cop | 0 | 7 | 0 |
| Motor sol | colps→cops | 0 | 3 | 3 |
| Motor sol | calces→bragues | 5 | 0 | 0 |
| Motor sol | gandula→hamaca | 4 | 0 | 0 |
| Motor sol | gandules→hamaques | 3 | 0 | 0 |
| Motor sol | manca→falta | 2 | 1 | 0 |
| Motor sol | fartanera→fartada | 2 | 0 | 0 |
| Motor sol | manques→faltes | 0 | 2 | 0 |
| Motor sol | nous→anous | 2 | 0 | 0 |
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
| Motor sol | mentres→mentre | 0 | 1 | 0 |
| Motor sol | moltes vegades→molts cops | 0 | 1 | 0 |
| Motor sol | oferides→ofertes | 0 | 1 | 0 |
| Motor sol | primera vegada→primer cop | 0 | 1 | 0 |
| Motor sol | quantes vegades→quants cops | 0 | 1 | 0 |
| Motor sol | rentar→llavar | 1 | 0 | 0 |
| Motor sol | valencià→valenciana | 1 | 0 | 0 |

## homografs_v2

### Trossos amb error

#### Prompt «valencia2»

| Sistema | Trossos | En forma valenciana | En forma catalana | Neutres | No són en la frase | Formes valencianes més marcades |
|---|---|---|---|---|---|---|
| Referència | 21 | 18 (86 %) | 0 (0 %) | 3 (14 %) | 0 (0 %) | anou 3, llavadores 3, faltes 2, bragues 2, ensalada 1, anous 1, llavadora 1, hamaca 1, panolles 1, fartades 1, depén 1, exitoses 1 |
| AVLizador 2.0.1 | 13 | 10 (77 %) | 0 (0 %) | 3 (23 %) | 0 (0 %) | anou 3, ensalada 1, llavadores 1, hamaca 1, panolles 1, fartades 1, depén 1, exitoses 1 |
| Motor sol | 63 | 53 (84 %) | 0 (0 %) | 10 (16 %) | 0 (0 %) | anou 10, faltes 6, bragues 6, hamaca 5, anous 4, llavadores 4, hamaques 4, panolles 4, llavadora 3, falta 2, ensalada 1, panolla 1 |

### Categories dels errors

| Sistema | Part | Frases | accuracy | fluency | style | terminology | altres | Majors |
|---|---|---|---|---|---|---|---|---|
| Referència | — | 144 | 10 | 4 | 0 | 6 | 1 | 10 |
| AVLizador 2.0.1 | — | 144 | 6 | 3 | 0 | 3 | 1 | 6 |
| Motor sol | — | 144 | 36 | 16 | 0 | 9 | 2 | 36 |

### Frases distintes de la referència

«Marca alguna paraula canviada» = algun tros amb error del sistema toca una paraula que no és en la referència. Detall en `analisi_detall.md`.

| Sistema | Frases distintes | Marca alguna paraula canviada | Guanya la ref. | Empat | Guanya el sistema |
|---|---|---|---|---|---|
| AVLizador 2.0.1 | 31 | 1 | 1 | 19 | 11 |
| Motor sol | 69 | 44 | 45 | 22 | 2 |

Per canvi (referència → sistema; quantes frases guanya la referència / empat / el sistema):

| Sistema | Canvi | Guanya la ref. | Empat | Guanya el sistema |
|---|---|---|---|---|
| AVLizador 2.0.1 | bragues→calces | 0 | 1 | 3 |
| AVLizador 2.0.1 | faltes→manques | 0 | 2 | 2 |
| AVLizador 2.0.1 | hamaques→gandules | 0 | 2 | 1 |
| AVLizador 2.0.1 | llavadora→rentadora | 0 | 2 | 1 |
| AVLizador 2.0.1 | llavadores→rentadores | 0 | 1 | 2 |
| AVLizador 2.0.1 | anous→nous | 0 | 1 | 1 |
| AVLizador 2.0.1 | exitosa→reeixida | 0 | 2 | 0 |
| AVLizador 2.0.1 | falta→manca | 0 | 2 | 0 |
| AVLizador 2.0.1 | panolles→panotxes | 0 | 2 | 0 |
| AVLizador 2.0.1 | exitoses→reeixides | 0 | 1 | 0 |
| AVLizador 2.0.1 | fartada→fartanera | 0 | 1 | 0 |
| AVLizador 2.0.1 | fartades→fartaneres | 0 | 0 | 1 |
| AVLizador 2.0.1 | fartades→fartaneres; síndria→meló alger | 1 | 0 | 0 |
| AVLizador 2.0.1 | freda→fred | 0 | 1 | 0 |
| AVLizador 2.0.1 | panolla→panotxa | 0 | 1 | 0 |
| Motor sol | manques→faltes | 3 | 5 | 0 |
| Motor sol | nou→anou | 7 | 1 | 0 |
| Motor sol | manca→falta | 3 | 3 | 1 |
| Motor sol | calces→bragues | 4 | 0 | 0 |
| Motor sol | fartanera→fartada | 4 | 0 | 0 |
| Motor sol | fartaneres→fartades | 3 | 1 | 0 |
| Motor sol | gandula→hamaca | 4 | 0 | 0 |
| Motor sol | gandules→hamaques | 4 | 0 | 0 |
| Motor sol | nous→anous | 4 | 0 | 0 |
| Motor sol | panotxa→panolla | 1 | 3 | 0 |
| Motor sol | panotxes→panolles | 3 | 1 | 0 |
| Motor sol | rentadora→llavadora | 2 | 2 | 0 |
| Motor sol | rentadores→llavadores | 1 | 3 | 0 |
| Motor sol | reeixides→exitoses | 1 | 1 | 0 |
| Motor sol | brollador→deu | 0 | 1 | 0 |
| Motor sol | exitoses→reeixides | 0 | 0 | 1 |
| Motor sol | freda→fred | 0 | 1 | 0 |
| Motor sol | síndria→meló alger | 1 | 0 | 0 |
