# Meta-avaluació del jutge en els homògrafs

Veritat: el benchmark diu, per a cada frase, la paraula catalana (`paraula`) i la
correcta (`esperat`). Per a cada eixida (referència, AVLizador, motor) es busca
quina paraula hi ha en eixe lloc (alineant amb l'original català) i es classifica:
  correcta_val  esperat ≠ paraula i l'eixida diu esperat (p. ex. «anou» fruit)
  correcta_cat  esperat = paraula i l'eixida la deixa (p. ex. «nou» adjectiu)
  deixa_cat     esperat ≠ paraula i l'eixida deixa la catalana (error lleu)
  error_sentit  l'eixida posa una altra paraula (error greu)
El jutge «marca» el lloc si algun tros amb error conté la paraula de l'eixida.

## Prompt «valencia» (v1 + v2, referència + AVLizador + motor)

| Classe | Llocs | El jutge marca la paraula | Nota mitjana | Frases amb nota < 100 |
|---|---|---|---|---|
| Correcta, forma valenciana (anou fruit, colp, llavadora…) | 306 | 33/306 (11 %) | 94.4 | 62/306 (20 %) |
| Correcta, paraula catalana mantinguda (nou adjectiu, calces de vestir…) | 237 | 2/237 (1 %) | 99.6 | 14/237 (6 %) |
| Deixa el català on calia traduir (lleu) | 75 | 1/75 (1 %) | 99.2 | 2/75 (3 %) |
| Error de sentit (cotxe anou, bragues per calces…) | 90 | 47/90 (52 %) | 78.7 | 54/90 (60 %) |

- **Exhaustivitat** (errors de sentit que marca): 47/90 (52 %)
- **Precisió** (de les paraules correctes o errònies que marca, quantes són errors): 47/82 (57 %)
- **Falsos positius en formes valencianes correctes**: 33/306 (11 %)
- **AUC de la nota** (error de sentit vs. correcta; 0,5 = a l'atzar, 1 = perfecte): 0.74

Per paraula (paraula catalana → esperada; marca / total):

| Paraula | Error de sentit marcat | Forma valenciana correcta marcada | Catalana correcta marcada |
|---|---|---|---|
| calces | 8/9 (89 %) | 8/20 (40 %) | 0/18 (0 %) |
| cop | — | 0/64 (0 %) | — |
| deu | — | 0/20 (0 %) | 0/33 (0 %) |
| fartanera | 8/10 (80 %) | 3/27 (11 %) | 0/20 (0 %) |
| gandula | 15/15 (100 %) | 11/40 (28 %) | 0/30 (0 %) |
| manca | 8/20 (40 %) | 2/32 (6 %) | 0/40 (0 %) |
| nou | 1/18 (6 %) | 3/38 (8 %) | 2/36 (6 %) |
| panotxa | 1/8 (12 %) | 6/21 (29 %) | 0/16 (0 %) |
| reeixida | 1/2 (50 %) | 0/26 (0 %) | 0/28 (0 %) |
| rentadora | 5/8 (62 %) | 0/18 (0 %) | 0/16 (0 %) |

- Referència: correcta_val 127, correcta_cat 109, deixa_cat 0, error_sentit 0
- AVLizador 2.0.1: correcta_val 86, correcta_cat 109, deixa_cat 41, error_sentit 0
- Motor sol: correcta_val 93, correcta_cat 19, deixa_cat 34, error_sentit 90

## Prompt «valencia2» (v1 + v2, referència + AVLizador + motor)

| Classe | Llocs | El jutge marca la paraula | Nota mitjana | Frases amb nota < 100 |
|---|---|---|---|---|
| Correcta, forma valenciana (anou fruit, colp, llavadora…) | 306 | 80/306 (26 %) | 92.4 | 108/306 (35 %) |
| Correcta, paraula catalana mantinguda (nou adjectiu, calces de vestir…) | 237 | 4/237 (2 %) | 98.9 | 12/237 (5 %) |
| Deixa el català on calia traduir (lleu) | 75 | 0/75 (0 %) | 99.3 | 1/75 (1 %) |
| Error de sentit (cotxe anou, bragues per calces…) | 90 | 64/90 (71 %) | 78.1 | 68/90 (76 %) |

- **Exhaustivitat** (errors de sentit que marca): 64/90 (71 %)
- **Precisió** (de les paraules correctes o errònies que marca, quantes són errors): 64/148 (43 %)
- **Falsos positius en formes valencianes correctes**: 80/306 (26 %)
- **AUC de la nota** (error de sentit vs. correcta; 0,5 = a l'atzar, 1 = perfecte): 0.78

Per paraula (paraula catalana → esperada; marca / total):

| Paraula | Error de sentit marcat | Forma valenciana correcta marcada | Catalana correcta marcada |
|---|---|---|---|
| calces | 9/9 (100 %) | 14/20 (70 %) | 0/18 (0 %) |
| cop | — | 14/64 (22 %) | — |
| deu | — | 3/20 (15 %) | 0/33 (0 %) |
| fartanera | 9/10 (90 %) | 6/27 (22 %) | 0/20 (0 %) |
| gandula | 15/15 (100 %) | 6/40 (15 %) | 0/30 (0 %) |
| manca | 7/20 (35 %) | 4/32 (12 %) | 4/40 (10 %) |
| nou | 16/18 (89 %) | 19/38 (50 %) | 0/36 (0 %) |
| panotxa | 4/8 (50 %) | 3/21 (14 %) | 0/16 (0 %) |
| reeixida | 1/2 (50 %) | 2/26 (8 %) | 0/28 (0 %) |
| rentadora | 3/8 (38 %) | 9/18 (50 %) | 0/16 (0 %) |

- Referència: correcta_val 127, correcta_cat 109, deixa_cat 0, error_sentit 0
- AVLizador 2.0.1: correcta_val 86, correcta_cat 109, deixa_cat 41, error_sentit 0
- Motor sol: correcta_val 93, correcta_cat 19, deixa_cat 34, error_sentit 90

## Prompt «valencia3» (v1 + v2, referència + AVLizador + motor)

| Classe | Llocs | El jutge marca la paraula | Nota mitjana | Frases amb nota < 100 |
|---|---|---|---|---|
| Correcta, forma valenciana (anou fruit, colp, llavadora…) | 306 | 3/306 (1 %) | 96.5 | 43/306 (14 %) |
| Correcta, paraula catalana mantinguda (nou adjectiu, calces de vestir…) | 237 | 107/237 (45 %) | 93.6 | 100/237 (42 %) |
| Deixa el català on calia traduir (lleu) | 75 | 64/75 (85 %) | 94.5 | 63/75 (84 %) |
| Error de sentit (cotxe anou, bragues per calces…) | 90 | 40/90 (44 %) | 81.4 | 48/90 (53 %) |

- **Exhaustivitat** (errors de sentit que marca): 40/90 (44 %)
- **Precisió** (de les paraules correctes o errònies que marca, quantes són errors): 40/150 (27 %)
- **Falsos positius en formes valencianes correctes**: 3/306 (1 %)
- **AUC de la nota** (error de sentit vs. correcta; 0,5 = a l'atzar, 1 = perfecte): 0.67

Per paraula (paraula catalana → esperada; marca / total):

| Paraula | Error de sentit marcat | Forma valenciana correcta marcada | Catalana correcta marcada |
|---|---|---|---|
| calces | 0/9 (0 %) | 0/20 (0 %) | 16/18 (89 %) |
| cop | — | 0/64 (0 %) | — |
| deu | — | 0/20 (0 %) | 3/33 (9 %) |
| fartanera | 1/10 (10 %) | 0/27 (0 %) | 16/20 (80 %) |
| gandula | 15/15 (100 %) | 0/40 (0 %) | 2/30 (7 %) |
| manca | 4/20 (20 %) | 0/32 (0 %) | 30/40 (75 %) |
| nou | 18/18 (100 %) | 3/38 (8 %) | 2/36 (6 %) |
| panotxa | 0/8 (0 %) | 0/21 (0 %) | 16/16 (100 %) |
| reeixida | 1/2 (50 %) | 0/26 (0 %) | 16/28 (57 %) |
| rentadora | 1/8 (12 %) | 0/18 (0 %) | 6/16 (38 %) |

- Referència: correcta_val 127, correcta_cat 109, deixa_cat 0, error_sentit 0
- AVLizador 2.0.1: correcta_val 86, correcta_cat 109, deixa_cat 41, error_sentit 0
- Motor sol: correcta_val 93, correcta_cat 19, deixa_cat 34, error_sentit 90

## Casos on el jutge s'equivoca (error no marcat o paraula correcta marcada)

| Prompt | Sistema | Id | Classe | Paraula | Nota | Frase | Trossos |
|---|---|---|---|---|---|---|---|
| valencia | referencia | HG034 | correcta_val | bragues | 95.0 | Ha comprat unes bragues de cotó al mercat. | bragues |
| valencia | referencia | HG043 | correcta_val | hamaca | 65.0 | Este estiu he comprat una hamaca per a la terrassa. | hamaca |
| valencia | referencia | HG051 | correcta_val | hamaques | 65.0 | L'hotel lloga hamaques i para-sols a la platja. | hamaques |
| valencia | avlizador | HG043 | correcta_val | hamaca | 65.0 | Este estiu he comprat una hamaca per a la terrassa. | hamaca |
| valencia | avlizador | HG051 | correcta_val | hamaques | 65.0 | L'hotel lloga hamaques i para-sols a la platja. | hamaques |
| valencia | motor | HG034 | correcta_val | bragues | 95.0 | Ha comprat unes bragues de cotó al mercat. | bragues |
| valencia | motor | HG043 | correcta_val | hamaca | 65.0 | Este estiu he comprat una hamaca per a la terrassa. | hamaca |
| valencia | motor | HG051 | correcta_val | hamaques | 65.0 | L'hotel lloga hamaques i para-sols a la platja. | hamaques |
| valencia | motor | HG061 | error_sentit | anou | 100.0 | Hem comprat un cotxe anou. |  |
| valencia | motor | HG062 | error_sentit | anou | 100.0 | Tinc anou germans. |  |
| valencia | motor | HG063 | error_sentit | anou | 100.0 | És un projecte anou de l'ajuntament. |  |
| valencia | motor | HG064 | error_sentit | anou | 100.0 | Arribarem a les anou del matí. |  |
| valencia | motor | HG067 | error_sentit | anous | 95.0 | Els llibres anous són a la taula. |  |
| valencia | motor | HG068 | error_sentit | anous | 100.0 | Hi ha anous casos de grip. |  |
| valencia | motor | HG072 | error_sentit | falta | 95.0 | Li falta experiència per a esta faena. |  |
| valencia | motor | HG073 | error_sentit | falta | 100.0 | Encara falta una setmana per a les vacacions. |  |
| valencia | motor | HG077 | error_sentit | faltes | 100.0 | Tu faltes de paciència. |  |
| valencia | motor | HG078 | error_sentit | faltes | 100.0 | Si faltes a la reunió, avisa'ns. |  |
| valencia | referencia | HG2-004 | correcta_val | anou | 45.0 | Afig una anou picada a l'ensalada. | anou; ensalada |
| valencia | referencia | HG2-020 | correcta_cat | nous | 95.0 | Els veïns nous són molt amables. | nous |
| valencia | referencia | HG2-036 | correcta_val | faltes | 65.0 | Les faltes alimentàries afecten molts infants. | faltes |
| valencia | referencia | HG2-089 | correcta_val | bragues | 95.0 | Ha comprat unes bragues de cotó. | bragues |
| valencia | referencia | HG2-090 | correcta_val | bragues | 45.0 | Les bragues són al calaix de la roba interior. | bragues |
| valencia | referencia | HG2-092 | correcta_val | bragues | 45.0 | Al paquet hi ha tres bragues de colors. | bragues |
| valencia | referencia | HG2-097 | correcta_val | l hamaca | 45.0 | S'ha estirat a l'hamaca de la piscina. | hamaca |
| valencia | referencia | HG2-105 | correcta_val | hamaques | 45.0 | Han posat hamaques noves a la platja. | hamaques |
| valencia | referencia | HG2-121 | correcta_val | panolles | 95.0 | Hem collit vint panolles de l'hort. | panolles |
| valencia | referencia | HG2-123 | correcta_val | panolles | 95.0 | Venen panolles torrades a la fira. | panolles |
| valencia | referencia | HG2-139 | correcta_val | estes fartades | 65.0 | No són bones estes fartades de dolços. | fartades |
| valencia | avlizador | HG2-004 | correcta_val | anou | 45.0 | Afig una anou picada a l'ensalada. | anou; ensalada |
| valencia | avlizador | HG2-020 | correcta_cat | nous | 95.0 | Els veïns nous són molt amables. | nous |
| valencia | avlizador | HG2-067 | deixa_cat | rentadores | 95.0 | A la bugaderia hi ha deu rentadores. | rentadores |
| valencia | avlizador | HG2-097 | correcta_val | l hamaca | 45.0 | S'ha estirat a l'hamaca de la piscina. | hamaca |
| valencia | avlizador | HG2-121 | correcta_val | panolles | 95.0 | Hem collit vint panolles de l'hort. | panolles |
| valencia | avlizador | HG2-123 | correcta_val | panolles | 95.0 | Venen panolles torrades a la fira. | panolles |
| valencia | motor | HG2-004 | correcta_val | anou | 45.0 | Afig una anou picada a l'ensalada. | anou; ensalada |
| valencia | motor | HG2-005 | error_sentit | anou | 95.0 | Hem estrenat un ordinador anou a l'oficina. |  |
| valencia | motor | HG2-006 | error_sentit | l anou | 95.0 | L'anou director començarà a treballar dilluns. |  |
| valencia | motor | HG2-007 | error_sentit | anou | 100.0 | Este abric encara sembla anou. |  |
| valencia | motor | HG2-008 | error_sentit | anou | 95.0 | Han obert un camí anou entre els dos pobles. |  |
| valencia | motor | HG2-009 | error_sentit | anou | 100.0 | La reunió començarà a les anou en punt. |  |
| valencia | motor | HG2-010 | error_sentit | anou | 100.0 | El seu fill xicotet té anou anys. |  |
| valencia | motor | HG2-011 | error_sentit | anou | 100.0 | Hi havia anou persones a la cua. |  |
| valencia | motor | HG2-012 | error_sentit | anou | 100.0 | Viu al número anou d'este carrer. |  |
| valencia | motor | HG2-017 | error_sentit | anous | 100.0 | Els alumnes anous arriben la setmana que ve. |  |
| valencia | motor | HG2-018 | error_sentit | anous | 100.0 | Necessite uns pantalons anous per a la festa. |  |
| valencia | motor | HG2-019 | error_sentit | anous | 100.0 | Han aparegut anous casos de grip a l'escola. |  |
| valencia | motor | HG2-025 | error_sentit | falta | 100.0 | Encara falta una setmana per a les vacacions. |  |
| valencia | motor | HG2-026 | error_sentit | falta | 100.0 | A la sopa li falta una mica de sal. |  |
| valencia | motor | HG2-027 | error_sentit | falta | 100.0 | A l'equip li falta un jugador per a poder començar. |  |
| valencia | motor | HG2-031 | error_sentit | nàixer falta | 95.0 | Va nàixer falta d'una mà però toca el piano. |  |
| valencia | motor | HG2-036 | correcta_val | faltes | 65.0 | Les faltes alimentàries afecten molts infants. | faltes |
| valencia | motor | HG2-037 | error_sentit | faltes | 100.0 | Tu ens faltes molt des que te'n vas anar. |  |
| valencia | motor | HG2-038 | error_sentit | faltes | 100.0 | Si tu faltes a la reunió, no podrem votar. |  |
| valencia | motor | HG2-040 | error_sentit | faltes | 100.0 | Quan tu faltes, la casa sembla buida. |  |
| valencia | motor | HG2-044 | error_sentit | faltes | 95.0 | Les figures faltes del pesebre s'han de reparar. |  |
| valencia | motor | HG2-062 | error_sentit | llavadora | 100.0 | Una dona llavadora portava la roba al riu. |  |
| valencia | motor | HG2-069 | error_sentit | llavadores | 100.0 | Les llavadores del poble es trobaven al safareig. |  |
| valencia | motor | HG2-070 | error_sentit | llavadores | 100.0 | Antigament les llavadores feien la bugada al riu. |  |
| valencia | motor | HG2-089 | correcta_val | bragues | 95.0 | Ha comprat unes bragues de cotó. | bragues |
| valencia | motor | HG2-090 | correcta_val | bragues | 45.0 | Les bragues són al calaix de la roba interior. | bragues |
| valencia | motor | HG2-092 | correcta_val | bragues | 45.0 | Al paquet hi ha tres bragues de colors. | bragues |
| valencia | motor | HG2-093 | error_sentit | bragues | 100.0 | En esta casa, qui porta les bragues és la mare. |  |
| valencia | motor | HG2-097 | correcta_val | l hamaca | 45.0 | S'ha estirat a l'hamaca de la piscina. | hamaca |
| valencia | motor | HG2-105 | correcta_val | hamaques | 45.0 | Han posat hamaques noves a la platja. | hamaques |
| valencia | motor | HG2-117 | error_sentit | panolla | 100.0 | La seua àvia era panolla, de l'horta de Múrcia. |  |
| valencia | motor | HG2-118 | error_sentit | panolla | 100.0 | Una dona panolla venia hortalisses al mercat. |  |
| valencia | motor | HG2-119 | error_sentit | panolla | 100.0 | La cultura panolla de l'horta té moltes festes. |  |
| valencia | motor | HG2-120 | error_sentit | panolla | 100.0 | Cantava una cançó panolla tradicional. |  |
| valencia | motor | HG2-121 | correcta_val | panolles | 95.0 | Hem collit vint panolles de l'hort. | panolles |
| valencia | motor | HG2-123 | correcta_val | panolles | 95.0 | Venen panolles torrades a la fira. | panolles |
| valencia | motor | HG2-125 | error_sentit | panolles | 100.0 | Les dones panolles portaven el vestit tradicional de l'horta. |  |
| valencia | motor | HG2-126 | error_sentit | panolles | 100.0 | Les cançons panolles parlen de la vida al camp. |  |
| valencia | motor | HG2-127 | error_sentit | panolles | 100.0 | Les famílies panolles celebren la festa de l'horta. |  |
| valencia | motor | HG2-135 | error_sentit | sigues fartada | 100.0 | No sigues fartada i deixa'n per als altres. |  |
| valencia | motor | HG2-137 | correcta_val | fartades | 45.0 | A l'estiu fèiem fartades de meló d'Alger. | fartades; meló d'Alger |
| valencia | motor | HG2-139 | correcta_val | estes fartades | 65.0 | No són bones estes fartades de dolços. | fartades |
| valencia | motor | HG2-143 | error_sentit | xiques fartades | 100.0 | Eren unes xiques fartades i alegres. |  |
| valencia | motor | HG2-158 | error_sentit | seues exitoses | 100.0 | Les seues exitoses professionals la van fer famosa. |  |
| valencia2 | referencia | HG003 | correcta_val | colp | 95.0 | La porta es va tancar de colp. | colp |
| valencia2 | referencia | HG006 | correcta_val | colp | 95.0 | La mort del seu pare va ser un colp molt dur per a la família. | colp |
| valencia2 | referencia | HG007 | correcta_val | colp | 95.0 | Un colp de sort li va canviar la vida. | colp |
| valencia2 | referencia | HG010 | correcta_val | colp | 95.0 | L'actriu no es va recuperar mai d'aquell colp. | colp |
| valencia2 | referencia | HG021 | correcta_val | colps | 95.0 | Va sentir uns colps forts a la porta. | colps |
| valencia2 | referencia | HG023 | correcta_val | colps | 95.0 | Els colps de vent van tombar diversos arbres. | colps |
| valencia2 | referencia | HG025 | correcta_val | colps | 95.0 | La fruita tenia colps i no es podia vendre. | colps |
| valencia2 | referencia | HG033 | correcta_val | bragues | 65.0 | Les bragues de la xiqueta estan brutes. | bragues |
| valencia2 | referencia | HG034 | correcta_val | bragues | 95.0 | Ha comprat unes bragues de cotó al mercat. | bragues |
| valencia2 | referencia | HG035 | correcta_val | bragues | 85.0 | Porta les bragues i el sostenidor a la bossa del gimnàs. | bragues |
| valencia2 | referencia | HG037 | correcta_val | bragues | 65.0 | Al calaix guarda les bragues i els calcetins. | bragues |
| valencia2 | referencia | HG051 | correcta_val | hamaques | 65.0 | L'hotel lloga hamaques i para-sols a la platja. | hamaques |
| valencia2 | referencia | HG057 | correcta_val | anou | 85.0 | Va trencar una anou amb les dents. | anou |
| valencia2 | referencia | HG058 | correcta_val | anou | 85.0 | El pastís porta anou i panses. | anou |
| valencia2 | referencia | HG059 | correcta_val | anou | 85.0 | Es va menjar una anou del calaix. | anou |
| valencia2 | referencia | HG080 | correcta_val | el brollador | 85.0 | El brollador de la font s'ha assecat. | brollador |
| valencia2 | avlizador | HG003 | correcta_val | colp | 95.0 | La porta es va tancar de colp. | colp |
| valencia2 | avlizador | HG006 | correcta_val | colp | 95.0 | La mort del seu pare va ser un colp molt dur per a la família. | colp |
| valencia2 | avlizador | HG007 | correcta_val | colp | 95.0 | Un colp de sort li va canviar la vida. | colp |
| valencia2 | avlizador | HG010 | correcta_val | colp | 95.0 | L'actriu no es va recuperar mai d'aquell colp. | colp |
| valencia2 | avlizador | HG021 | correcta_val | colps | 95.0 | Va sentir uns colps forts a la porta. | colps |
| valencia2 | avlizador | HG023 | correcta_val | colps | 95.0 | Els colps de vent van tombar diversos arbres. | colps |
| valencia2 | avlizador | HG025 | correcta_val | colps | 95.0 | La fruita tenia colps i no es podia vendre. | colps |
| valencia2 | avlizador | HG035 | correcta_val | bragues | 85.0 | Porta les bragues i el sostenidor a la bossa del gimnàs. | bragues |
| valencia2 | avlizador | HG037 | correcta_val | bragues | 65.0 | Al calaix guarda les bragues i els calcetins. | bragues |
| valencia2 | avlizador | HG051 | correcta_val | hamaques | 65.0 | L'hotel lloga hamaques i para-sols a la platja. | hamaques |
| valencia2 | avlizador | HG057 | correcta_val | anou | 85.0 | Va trencar una anou amb les dents. | anou |
| valencia2 | avlizador | HG059 | correcta_val | anou | 85.0 | Es va menjar una anou del calaix. | anou |
| valencia2 | avlizador | HG080 | correcta_val | el brollador | 85.0 | El brollador de la font s'ha assecat. | brollador |
| valencia2 | motor | HG033 | correcta_val | bragues | 65.0 | Les bragues de la xiqueta estan brutes. | bragues |
| valencia2 | motor | HG034 | correcta_val | bragues | 95.0 | Ha comprat unes bragues de cotó al mercat. | bragues |
| valencia2 | motor | HG035 | correcta_val | bragues | 85.0 | Porta les bragues i el sostenidor a la bossa del gimnàs. | bragues |
| valencia2 | motor | HG037 | correcta_val | bragues | 65.0 | Al calaix guarda les bragues i els calcetins. | bragues |
| valencia2 | motor | HG051 | correcta_val | hamaques | 65.0 | L'hotel lloga hamaques i para-sols a la platja. | hamaques |
| valencia2 | motor | HG057 | correcta_val | anou | 85.0 | Va trencar una anou amb les dents. | anou |
| valencia2 | motor | HG058 | correcta_val | anou | 85.0 | El pastís porta anou i panses. | anou |
| valencia2 | motor | HG059 | correcta_val | anou | 85.0 | Es va menjar una anou del calaix. | anou |
| valencia2 | motor | HG072 | error_sentit | falta | 95.0 | Li falta experiència per a esta faena. |  |
| valencia2 | motor | HG073 | error_sentit | falta | 100.0 | Encara falta una setmana per a les vacacions. |  |
| valencia2 | motor | HG077 | error_sentit | faltes | 100.0 | Tu faltes de paciència. |  |
| valencia2 | motor | HG078 | error_sentit | faltes | 100.0 | Si faltes a la reunió, avisa'ns. |  |
| valencia2 | motor | HG080 | correcta_val | el brollador | 85.0 | El brollador de la font s'ha assecat. | brollador |
| valencia2 | referencia | HG2-001 | correcta_val | anou | 85.0 | Ha caigut una anou de l'arbre del pati. | anou |
| valencia2 | referencia | HG2-002 | correcta_val | anou | 85.0 | Per a esmorzar es menja una anou i un tros de formatge. | anou |
| valencia2 | referencia | HG2-004 | correcta_val | anou | 65.0 | Afig una anou picada a l'ensalada. | anou; ensalada |
| valencia2 | referencia | HG2-013 | correcta_val | d anous | 95.0 | Ha comprat un quilo d'anous al mercat. | anous |
| valencia2 | referencia | HG2-030 | correcta_cat | manca | 45.0 | La dona manca escrivia amb la mà esquerra. | manca |
| valencia2 | referencia | HG2-035 | correcta_val | faltes | 95.0 | Hem detectat diverses faltes en el pressupost. | faltes |
| valencia2 | referencia | HG2-036 | correcta_val | faltes | 65.0 | Les faltes alimentàries afecten molts infants. | faltes |
| valencia2 | referencia | HG2-042 | correcta_cat | manques | 45.0 | Les estàtues manques del museu són romanes. | manques |
| valencia2 | referencia | HG2-057 | correcta_val | llavadora | 85.0 | Posa els llençols a la llavadora. | llavadora |
| valencia2 | referencia | HG2-065 | correcta_val | llavadores | 85.0 | La botiga ven llavadores i assecadores. | llavadores |
| valencia2 | referencia | HG2-066 | correcta_val | llavadores | 65.0 | Les llavadores modernes gasten poca aigua. | llavadores |
| valencia2 | referencia | HG2-068 | correcta_val | llavadores | 65.0 | Totes les llavadores de l'edifici són al soterrani. | llavadores |
| valencia2 | referencia | HG2-089 | correcta_val | bragues | 95.0 | Ha comprat unes bragues de cotó. | bragues |
| valencia2 | referencia | HG2-092 | correcta_val | bragues | 45.0 | Al paquet hi ha tres bragues de colors. | bragues |
| valencia2 | referencia | HG2-097 | correcta_val | l hamaca | 45.0 | S'ha estirat a l'hamaca de la piscina. | hamaca |
| valencia2 | referencia | HG2-123 | correcta_val | panolles | 95.0 | Venen panolles torrades a la fira. | panolles |
| valencia2 | referencia | HG2-139 | correcta_val | estes fartades | 65.0 | No són bones estes fartades de dolços. | fartades |
| valencia2 | referencia | HG2-140 | correcta_val | fartades | 85.0 | Recorde les fartades de castanyes de la tardor. | fartades |
| valencia2 | referencia | HG2-154 | correcta_val | exitoses | 85.0 | Les dos últimes temporades van ser exitoses. | exitoses |
| valencia2 | avlizador | HG2-001 | correcta_val | anou | 85.0 | Ha caigut una anou de l'arbre del pati. | anou |
| valencia2 | avlizador | HG2-002 | correcta_val | anou | 85.0 | Per a esmorzar es menja una anou i un tros de formatge. | anou |
| valencia2 | avlizador | HG2-004 | correcta_val | anou | 65.0 | Afig una anou picada a l'ensalada. | anou; ensalada |
| valencia2 | avlizador | HG2-030 | correcta_cat | manca | 45.0 | La dona manca escrivia amb la mà esquerra. | manca |
| valencia2 | avlizador | HG2-042 | correcta_cat | manques | 45.0 | Les estàtues manques del museu són romanes. | manques |
| valencia2 | avlizador | HG2-065 | correcta_val | llavadores | 85.0 | La botiga ven llavadores i assecadores. | llavadores |
| valencia2 | avlizador | HG2-097 | correcta_val | l hamaca | 45.0 | S'ha estirat a l'hamaca de la piscina. | hamaca |
| valencia2 | avlizador | HG2-123 | correcta_val | panolles | 95.0 | Venen panolles torrades a la fira. | panolles |
| valencia2 | avlizador | HG2-140 | correcta_val | fartades | 85.0 | Recorde les fartades de castanyes de la tardor. | fartades |
| valencia2 | avlizador | HG2-154 | correcta_val | exitoses | 85.0 | Les dos últimes temporades van ser exitoses. | exitoses |
| valencia2 | motor | HG2-001 | correcta_val | anou | 85.0 | Ha caigut una anou de l'arbre del pati. | anou |
| valencia2 | motor | HG2-002 | correcta_val | anou | 85.0 | Per a esmorzar es menja una anou i un tros de formatge. | anou |
| valencia2 | motor | HG2-004 | correcta_val | anou | 65.0 | Afig una anou picada a l'ensalada. | anou; ensalada |
| valencia2 | motor | HG2-010 | error_sentit | anou | 100.0 | El seu fill xicotet té anou anys. |  |
| valencia2 | motor | HG2-013 | correcta_val | d anous | 95.0 | Ha comprat un quilo d'anous al mercat. | anous |
| valencia2 | motor | HG2-020 | error_sentit | anous | 95.0 | Els veïns anous són molt amables. |  |
| valencia2 | motor | HG2-025 | error_sentit | falta | 100.0 | Encara falta una setmana per a les vacacions. |  |
| valencia2 | motor | HG2-026 | error_sentit | falta | 100.0 | A la sopa li falta una mica de sal. |  |
| valencia2 | motor | HG2-027 | error_sentit | falta | 100.0 | A l'equip li falta un jugador per a poder començar. |  |
| valencia2 | motor | HG2-030 | error_sentit | falta | 95.0 | La dona falta escrivia amb la mà esquerra. |  |
| valencia2 | motor | HG2-031 | error_sentit | nàixer falta | 95.0 | Va nàixer falta d'una mà però toca el piano. |  |
| valencia2 | motor | HG2-035 | correcta_val | faltes | 95.0 | Hem detectat diverses faltes en el pressupost. | faltes |
| valencia2 | motor | HG2-036 | correcta_val | faltes | 65.0 | Les faltes alimentàries afecten molts infants. | faltes |
| valencia2 | motor | HG2-038 | error_sentit | faltes | 100.0 | Si tu faltes a la reunió, no podrem votar. |  |
| valencia2 | motor | HG2-039 | error_sentit | faltes | 100.0 | Ara ja només hi faltes tu. |  |
| valencia2 | motor | HG2-040 | error_sentit | faltes | 100.0 | Quan tu faltes, la casa sembla buida. |  |
| valencia2 | motor | HG2-044 | error_sentit | faltes | 95.0 | Les figures faltes del pesebre s'han de reparar. |  |
| valencia2 | motor | HG2-057 | correcta_val | llavadora | 85.0 | Posa els llençols a la llavadora. | llavadora |
| valencia2 | motor | HG2-062 | error_sentit | llavadora | 100.0 | Una dona llavadora portava la roba al riu. |  |
| valencia2 | motor | HG2-063 | error_sentit | llavadora | 100.0 | És una crema llavadora per a pells greixoses. |  |
| valencia2 | motor | HG2-065 | correcta_val | llavadores | 85.0 | La botiga ven llavadores i assecadores. | llavadores |
| valencia2 | motor | HG2-066 | correcta_val | llavadores | 65.0 | Les llavadores modernes gasten poca aigua. | llavadores |
| valencia2 | motor | HG2-068 | correcta_val | llavadores | 65.0 | Totes les llavadores de l'edifici són al soterrani. | llavadores |
| valencia2 | motor | HG2-069 | error_sentit | llavadores | 100.0 | Les llavadores del poble es trobaven al safareig. |  |
| valencia2 | motor | HG2-070 | error_sentit | llavadores | 100.0 | Antigament les llavadores feien la bugada al riu. |  |
| valencia2 | motor | HG2-072 | error_sentit | llavadores | 100.0 | Les dones llavadores cantaven mentre treballaven. |  |
| valencia2 | motor | HG2-089 | correcta_val | bragues | 95.0 | Ha comprat unes bragues de cotó. | bragues |
| valencia2 | motor | HG2-092 | correcta_val | bragues | 45.0 | Al paquet hi ha tres bragues de colors. | bragues |
| valencia2 | motor | HG2-097 | correcta_val | l hamaca | 45.0 | S'ha estirat a l'hamaca de la piscina. | hamaca |
| valencia2 | motor | HG2-117 | error_sentit | panolla | 100.0 | La seua àvia era panolla, de l'horta de Múrcia. |  |
| valencia2 | motor | HG2-118 | error_sentit | panolla | 100.0 | Una dona panolla venia hortalisses al mercat. |  |
| valencia2 | motor | HG2-119 | error_sentit | panolla | 100.0 | La cultura panolla de l'horta té moltes festes. |  |
| valencia2 | motor | HG2-123 | correcta_val | panolles | 95.0 | Venen panolles torrades a la fira. | panolles |
| valencia2 | motor | HG2-128 | error_sentit | panolles | 100.0 | Les tradicions panolles de Múrcia són molt antigues. |  |
| valencia2 | motor | HG2-137 | correcta_val | fartades | 45.0 | A l'estiu fèiem fartades de meló d'Alger. | fartades; meló d'Alger |
| valencia2 | motor | HG2-139 | correcta_val | estes fartades | 65.0 | No són bones estes fartades de dolços. | fartades |
| valencia2 | motor | HG2-140 | correcta_val | fartades | 85.0 | Recorde les fartades de castanyes de la tardor. | fartades |
| valencia2 | motor | HG2-143 | error_sentit | xiques fartades | 100.0 | Eren unes xiques fartades i alegres. |  |
| valencia2 | motor | HG2-158 | error_sentit | seues exitoses | 100.0 | Les seues exitoses professionals la van fer famosa. |  |
| valencia3 | referencia | HG038 | correcta_cat | calces | 95.0 | Els cavallers medievals portaven calces de seda fins als genolls. | calces |
| valencia3 | referencia | HG039 | correcta_cat | calces | 95.0 | Les calces dels soldats del segle XVI eren de colors vius. | calces |
| valencia3 | referencia | HG040 | correcta_cat | calces | 95.0 | Al segle XV els homes portaven calces ajustades a les cames. | calces |
| valencia3 | referencia | HG041 | correcta_cat | calces | 95.0 | El sastre cosia calces i gipons per als nobles. | calces |
| valencia3 | referencia | HG072 | correcta_cat | manca | 95.0 | Li manca experiència per a esta faena. | manca |
| valencia3 | referencia | HG074 | correcta_cat | manca | 95.0 | Esta regió manca de grans ciutats. | manca |
| valencia3 | referencia | HG077 | correcta_cat | manques | 95.0 | Tu manques de paciència. | manques |
| valencia3 | referencia | HG078 | correcta_cat | manques | 95.0 | Si manques a la reunió, avisa'ns. | manques |
| valencia3 | referencia | HG095 | correcta_cat | fartanera | 95.0 | La seua germana és molt fartanera. | fartanera |
| valencia3 | referencia | HG096 | correcta_cat | fartanera | 95.0 | Esta gossa és molt fartanera. | fartanera |
| valencia3 | avlizador | HG033 | deixa_cat | calces | 95.0 | Les calces de la xiqueta estan brutes. | calces |
| valencia3 | avlizador | HG034 | deixa_cat | calces | 95.0 | Ha comprat unes calces de cotó al mercat. | calces |
| valencia3 | avlizador | HG036 | deixa_cat | calces | 95.0 | Es va posar unes calces netes després de la dutxa. | calces |
| valencia3 | avlizador | HG038 | correcta_cat | calces | 95.0 | Els cavallers medievals portaven calces de seda fins als genolls. | calces |
| valencia3 | avlizador | HG039 | correcta_cat | calces | 95.0 | Les calces dels soldats del segle XVI eren de colors vius. | calces |
| valencia3 | avlizador | HG040 | correcta_cat | calces | 95.0 | Al segle XV els homes portaven calces ajustades a les cames. | calces |
| valencia3 | avlizador | HG041 | correcta_cat | calces | 95.0 | El sastre cosia calces i gipons per als nobles. | calces |
| valencia3 | avlizador | HG052 | deixa_cat | gandules | 95.0 | Vam plegar les gandules abans que començara a ploure. | gandules |
| valencia3 | avlizador | HG053 | deixa_cat | gandules | 95.0 | Han posat gandules al voltant de la piscina. | gandules |
| valencia3 | avlizador | HG058 | deixa_cat | nou | 95.0 | El pastís porta nou i panses. | nou |
| valencia3 | avlizador | HG066 | deixa_cat | nous | 95.0 | Ha collit un sac de nous. | nous |
| valencia3 | avlizador | HG070 | deixa_cat | manca | 95.0 | La manca de pluja afecta els cultius. | manca |
| valencia3 | avlizador | HG071 | deixa_cat | manca | 95.0 | Patix una gran manca afectiva. | manca |
| valencia3 | avlizador | HG072 | correcta_cat | manca | 95.0 | Li manca experiència per a esta faena. | manca |
| valencia3 | avlizador | HG074 | correcta_cat | manca | 95.0 | Esta regió manca de grans ciutats. | manca |
| valencia3 | avlizador | HG075 | deixa_cat | manques | 95.0 | Les manques del sistema educatiu són evidents. | manques |
| valencia3 | avlizador | HG076 | deixa_cat | manques | 95.0 | L'informe detalla les manques del servici. | manques |
| valencia3 | avlizador | HG077 | correcta_cat | manques | 95.0 | Tu manques de paciència. | manques |
| valencia3 | avlizador | HG078 | correcta_cat | manques | 95.0 | Si manques a la reunió, avisa'ns. | manques |
| valencia3 | avlizador | HG095 | correcta_cat | fartanera | 95.0 | La seua germana és molt fartanera. | fartanera |
| valencia3 | avlizador | HG096 | correcta_cat | fartanera | 95.0 | Esta gossa és molt fartanera. | fartanera |
| valencia3 | motor | HG001 | deixa_cat | cop | 95.0 | Li va donar un cop al cap amb un bastó. | cop |
| valencia3 | motor | HG004 | deixa_cat | cop | 95.0 | Amb un cop de martell va clavar el clau. | cop |
| valencia3 | motor | HG005 | deixa_cat | cop | 95.0 | El cotxe va rebre un cop fort al lateral. | cop |
| valencia3 | motor | HG006 | deixa_cat | cop | 95.0 | La mort del seu pare va ser un cop molt dur per a la família. | cop |
| valencia3 | motor | HG007 | deixa_cat | cop | 95.0 | Un cop de sort li va canviar la vida. | cop |
| valencia3 | motor | HG008 | deixa_cat | cop | 95.0 | Es va fer un cop al genoll jugant a futbol. | cop |
| valencia3 | motor | HG010 | deixa_cat | cop | 95.0 | L'actriu no es va recuperar mai d'aquell cop. | cop |
| valencia3 | motor | HG012 | deixa_cat | cop | 100.0 | Cada cop hi ha més gent a la platja. | cop |
| valencia3 | motor | HG013 | deixa_cat | cop | 95.0 | Ho he intentat un cop i no ha funcionat. | un cop |
| valencia3 | motor | HG014 | deixa_cat | cop | 95.0 | Un altre cop has arribat tard. | cop |
| valencia3 | motor | HG015 | deixa_cat | cop | 95.0 | Un cop transcorregut el termini, es resoldrà la sol·licitud. | cop |
| valencia3 | motor | HG016 | deixa_cat | cop | 95.0 | Este cop no em deixaré enganyar. | cop |
| valencia3 | motor | HG017 | deixa_cat | cop | 95.0 | Per primer cop, l'equip ha guanyat la lliga. | cop |
| valencia3 | motor | HG018 | deixa_cat | cop | 95.0 | Cada cop que el veig, em saluda. | cop |
| valencia3 | motor | HG021 | deixa_cat | cops | 95.0 | Va sentir uns cops forts a la porta. | cops |
| valencia3 | motor | HG022 | deixa_cat | cops | 95.0 | El boxejador va rebre molts cops a la cara. | cops |
| valencia3 | motor | HG024 | deixa_cat | cops | 95.0 | Li van donar cops amb un pal. | cops |
| valencia3 | motor | HG025 | deixa_cat | cops | 95.0 | La fruita tenia cops i no es podia vendre. | cops |
| valencia3 | motor | HG026 | deixa_cat | cops | 95.0 | A cops de destral van obrir la porta. | cops |
| valencia3 | motor | HG028 | deixa_cat | cops | 95.0 | Molts cops no sabem què fer. | cops |
| valencia3 | motor | HG030 | deixa_cat | cops | 95.0 | Alguns cops arriba tard a la faena. | cops |
| valencia3 | motor | HG031 | deixa_cat | cops | 95.0 | Ho he repetit diversos cops. | cops |
| valencia3 | motor | HG032 | deixa_cat | cops | 100.0 | Quants cops t'ho he de dir? | cops |
| valencia3 | motor | HG038 | error_sentit | bragues | 100.0 | Els cavallers medievals portaven bragues de seda fins als genolls. |  |
| valencia3 | motor | HG039 | error_sentit | bragues | 100.0 | Les bragues dels soldats del segle XVI eren de colors vius. |  |
| valencia3 | motor | HG040 | error_sentit | bragues | 100.0 | Al segle XV els homes portaven bragues ajustades a les cames. |  |
| valencia3 | motor | HG041 | error_sentit | bragues | 100.0 | El sastre cosia bragues i gipons per als nobles. |  |
| valencia3 | motor | HG042 | error_sentit | bragues | 100.0 | Els patges duien bragues de dos colors. |  |
| valencia3 | motor | HG072 | error_sentit | falta | 95.0 | Li falta experiència per a esta faena. |  |
| valencia3 | motor | HG073 | error_sentit | falta | 100.0 | Encara falta una setmana per a les vacacions. |  |
| valencia3 | motor | HG074 | error_sentit | falta | 95.0 | Esta regió falta de grans ciutats. |  |
| valencia3 | motor | HG077 | error_sentit | faltes | 100.0 | Tu faltes de paciència. |  |
| valencia3 | motor | HG078 | error_sentit | faltes | 100.0 | Si faltes a la reunió, avisa'ns. |  |
| valencia3 | motor | HG095 | error_sentit | fartada | 100.0 | La seua germana és molt fartada. |  |
| valencia3 | motor | HG096 | error_sentit | fartada | 95.0 | Esta gossa és molt fartada. |  |
| valencia3 | referencia | HG2-004 | correcta_val | anou | 45.0 | Afig una anou picada a l'ensalada. | una anou; picada |
| valencia3 | referencia | HG2-020 | correcta_cat | nous | 95.0 | Els veïns nous són molt amables. | nous |
| valencia3 | referencia | HG2-026 | correcta_cat | manca | 100.0 | A la sopa li manca una mica de sal. | manca; una mica |
| valencia3 | referencia | HG2-027 | correcta_cat | manca | 95.0 | A l'equip li manca un jugador per a poder començar. | manca |
| valencia3 | referencia | HG2-029 | correcta_cat | manca | 95.0 | Després de l'accident es va quedar manca del braç dret. | manca |
| valencia3 | referencia | HG2-030 | correcta_cat | manca | 45.0 | La dona manca escrivia amb la mà esquerra. | manca |
| valencia3 | referencia | HG2-031 | correcta_cat | manca | 95.0 | Va nàixer manca d'una mà però toca el piano. | manca |
| valencia3 | referencia | HG2-037 | correcta_cat | manques | 100.0 | Tu ens manques molt des que te'n vas anar. | manques |
| valencia3 | referencia | HG2-038 | correcta_cat | manques | 95.0 | Si tu manques a la reunió, no podrem votar. | manques |
| valencia3 | referencia | HG2-039 | correcta_cat | manques | 100.0 | Ara ja només hi manques tu. | manques |
| valencia3 | referencia | HG2-040 | correcta_cat | manques | 95.0 | Quan tu manques, la casa sembla buida. | manques |
| valencia3 | referencia | HG2-041 | correcta_cat | manques | 85.0 | Les dos germanes van quedar manques després de la guerra. | manques |
| valencia3 | referencia | HG2-042 | correcta_cat | manques | 65.0 | Les estàtues manques del museu són romanes. | manques |
| valencia3 | referencia | HG2-056 | correcta_cat | deu | 85.0 | La factura es deu pagar abans de divendres. | es deu |
| valencia3 | referencia | HG2-062 | correcta_cat | rentadora | 65.0 | Una dona rentadora portava la roba al riu. | rentadora |
| valencia3 | referencia | HG2-069 | correcta_cat | rentadores | 65.0 | Les rentadores del poble es trobaven al safareig. | rentadores |
| valencia3 | referencia | HG2-072 | correcta_cat | rentadores | 85.0 | Les dones rentadores cantaven mentre treballaven. | rentadores |
| valencia3 | referencia | HG2-093 | correcta_cat | calces | 95.0 | En esta casa, qui porta les calces és la mare. | calces |
| valencia3 | referencia | HG2-094 | correcta_cat | calces | 95.0 | El patge duia unes calces vermelles i una gorra. | calces |
| valencia3 | referencia | HG2-095 | correcta_cat | calces | 95.0 | Al segle XVI els nobles vestien calces i jubó. | calces |
| valencia3 | referencia | HG2-096 | correcta_cat | calces | 95.0 | L'armadura del cavaller cobria les calces de llana. | calces |
| valencia3 | referencia | HG2-112 | correcta_cat | gandules | 95.0 | Les gates de casa són molt gandules. | gandules |
| valencia3 | referencia | HG2-117 | correcta_cat | panotxa | 95.0 | La seua àvia era panotxa, de l'horta de Múrcia. | panotxa |
| valencia3 | referencia | HG2-118 | correcta_cat | panotxa | 65.0 | Una dona panotxa venia hortalisses al mercat. | panotxa |
| valencia3 | referencia | HG2-119 | correcta_cat | panotxa | 65.0 | La cultura panotxa de l'horta té moltes festes. | panotxa |
| valencia3 | referencia | HG2-120 | correcta_cat | panotxa | 65.0 | Cantava una cançó panotxa tradicional. | panotxa |
| valencia3 | referencia | HG2-125 | correcta_cat | panotxes | 65.0 | Les dones panotxes portaven el vestit tradicional de l'horta. | panotxes |
| valencia3 | referencia | HG2-126 | correcta_cat | panotxes | 65.0 | Les cançons panotxes parlen de la vida al camp. | panotxes |
| valencia3 | referencia | HG2-127 | correcta_cat | panotxes | 65.0 | Les famílies panotxes celebren la festa de l'horta. | panotxes |
| valencia3 | referencia | HG2-128 | correcta_cat | panotxes | 65.0 | Les tradicions panotxes de Múrcia són molt antigues. | panotxes |
| valencia3 | referencia | HG2-133 | correcta_cat | fartanera | 95.0 | La meua gossa és molt fartanera i s'ho menja tot. | fartanera |
| valencia3 | referencia | HG2-135 | correcta_cat | fartanera | 95.0 | No sigues fartanera i deixa'n per als altres. | fartanera |
| valencia3 | referencia | HG2-141 | correcta_cat | fartaneres | 95.0 | Les meues nebodes són molt fartaneres. | fartaneres |
| valencia3 | referencia | HG2-142 | correcta_cat | fartaneres | 65.0 | Les gates fartaneres s'han menjat el peix. | fartaneres |
| valencia3 | referencia | HG2-143 | correcta_cat | fartaneres | 95.0 | Eren unes xiques fartaneres i alegres. | fartaneres |
| valencia3 | referencia | HG2-144 | correcta_cat | fartaneres | 95.0 | Les oques fartaneres no paren de menjar. | fartaneres |
| valencia3 | referencia | HG2-151 | correcta_cat | reeixida | 100.0 | La clau de la seua reeixida és la constància. | reeixida |
| valencia3 | referencia | HG2-152 | correcta_cat | reeixida | 95.0 | Ningú no esperava una reeixida tan gran. | reeixida |
| valencia3 | referencia | HG2-157 | correcta_cat | reeixides | 65.0 | Les reeixides de l'equip omplin el palmarés. | reeixides; omplin |
| valencia3 | referencia | HG2-158 | correcta_cat | reeixides | 95.0 | Les seues reeixides professionals la van fer famosa. | reeixides |
| valencia3 | referencia | HG2-159 | correcta_cat | reeixides | 85.0 | Totes les reeixides tenen un preu. | reeixides |
| valencia3 | referencia | HG2-160 | correcta_cat | reeixides | 65.0 | Ha acumulat moltes reeixides al llarg de la carrera. | reeixides |
| valencia3 | avlizador | HG2-004 | correcta_val | anou | 45.0 | Afig una anou picada a l'ensalada. | una anou; picada |
| valencia3 | avlizador | HG2-013 | deixa_cat | nous | 95.0 | Ha comprat un quilo de nous al mercat. | nous |
| valencia3 | avlizador | HG2-015 | deixa_cat | nous | 65.0 | Posa unes quantes nous al pastís de poma. | nous |
| valencia3 | avlizador | HG2-020 | correcta_cat | nous | 95.0 | Els veïns nous són molt amables. | nous |
| valencia3 | avlizador | HG2-021 | deixa_cat | manca | 95.0 | La manca de pluja ha arruïnat la collita. | manca |
| valencia3 | avlizador | HG2-023 | deixa_cat | manca | 95.0 | La seua manca d'experiència es nota molt. | manca |
| valencia3 | avlizador | HG2-026 | correcta_cat | manca | 100.0 | A la sopa li manca una mica de sal. | manca; una mica |
| valencia3 | avlizador | HG2-027 | correcta_cat | manca | 95.0 | A l'equip li manca un jugador per a poder començar. | manca |
| valencia3 | avlizador | HG2-029 | correcta_cat | manca | 95.0 | Després de l'accident es va quedar manca del braç dret. | manca |
| valencia3 | avlizador | HG2-030 | correcta_cat | manca | 45.0 | La dona manca escrivia amb la mà esquerra. | manca |
| valencia3 | avlizador | HG2-031 | correcta_cat | manca | 95.0 | Va nàixer manca d'una mà però toca el piano. | manca |
| valencia3 | avlizador | HG2-034 | deixa_cat | manques | 95.0 | Les manques de l'escola són evidents per a tothom. | manques |
| valencia3 | avlizador | HG2-035 | deixa_cat | manques | 95.0 | Hem detectat diverses manques en el pressupost. | manques |
| valencia3 | avlizador | HG2-036 | deixa_cat | manques | 65.0 | Les manques alimentàries afecten molts infants. | manques |
| valencia3 | avlizador | HG2-037 | correcta_cat | manques | 100.0 | Tu ens manques molt des que te'n vas anar. | manques |
| valencia3 | avlizador | HG2-038 | correcta_cat | manques | 95.0 | Si tu manques a la reunió, no podrem votar. | manques |
| valencia3 | avlizador | HG2-039 | correcta_cat | manques | 100.0 | Ara ja només hi manques tu. | manques |
| valencia3 | avlizador | HG2-040 | correcta_cat | manques | 95.0 | Quan tu manques, la casa sembla buida. | manques |
| valencia3 | avlizador | HG2-041 | correcta_cat | manques | 85.0 | Les dos germanes van quedar manques després de la guerra. | manques |
| valencia3 | avlizador | HG2-042 | correcta_cat | manques | 65.0 | Les estàtues manques del museu són romanes. | manques |
| valencia3 | avlizador | HG2-056 | correcta_cat | deu | 85.0 | La factura es deu pagar abans de divendres. | es deu |
| valencia3 | avlizador | HG2-057 | deixa_cat | rentadora | 95.0 | Posa els llençols a la rentadora. | rentadora |
| valencia3 | avlizador | HG2-058 | deixa_cat | rentadora | 95.0 | Hem comprat una rentadora que gasta poca aigua. | rentadora |
| valencia3 | avlizador | HG2-060 | deixa_cat | rentadora | 95.0 | El tècnic ha arreglat la rentadora del pis. | rentadora |
| valencia3 | avlizador | HG2-062 | correcta_cat | rentadora | 65.0 | Una dona rentadora portava la roba al riu. | rentadora |
| valencia3 | avlizador | HG2-066 | deixa_cat | rentadores | 95.0 | Les rentadores modernes gasten poca aigua. | rentadores |
| valencia3 | avlizador | HG2-067 | deixa_cat | rentadores | 95.0 | A la bugaderia hi ha deu rentadores. | rentadores |
| valencia3 | avlizador | HG2-068 | deixa_cat | rentadores | 85.0 | Totes les rentadores de l'edifici són al soterrani. | rentadores |
| valencia3 | avlizador | HG2-069 | correcta_cat | rentadores | 65.0 | Les rentadores del poble es trobaven al safareig. | rentadores |
| valencia3 | avlizador | HG2-072 | correcta_cat | rentadores | 85.0 | Les dones rentadores cantaven mentre treballaven. | rentadores |
| valencia3 | avlizador | HG2-089 | deixa_cat | calces | 95.0 | Ha comprat unes calces de cotó. | calces |
| valencia3 | avlizador | HG2-090 | deixa_cat | calces | 95.0 | Les calces són al calaix de la roba interior. | calces |
| valencia3 | avlizador | HG2-091 | deixa_cat | calces | 95.0 | Es va posar unes calces netes després de la dutxa. | calces |
| valencia3 | avlizador | HG2-092 | deixa_cat | calces | 65.0 | Al paquet hi ha tres calces de colors. | calces |
| valencia3 | avlizador | HG2-093 | correcta_cat | calces | 95.0 | En esta casa, qui porta les calces és la mare. | calces |
| valencia3 | avlizador | HG2-094 | correcta_cat | calces | 95.0 | El patge duia unes calces vermelles i una gorra. | calces |
| valencia3 | avlizador | HG2-095 | correcta_cat | calces | 95.0 | Al segle XVI els nobles vestien calces i jubó. | calces |
| valencia3 | avlizador | HG2-096 | correcta_cat | calces | 95.0 | L'armadura del cavaller cobria les calces de llana. | calces |
| valencia3 | avlizador | HG2-105 | deixa_cat | gandules | 95.0 | Han posat gandules noves a la platja. | gandules |
| valencia3 | avlizador | HG2-107 | deixa_cat | gandules | 95.0 | Al jardí hi ha dos gandules i una taula. | gandules |
| valencia3 | avlizador | HG2-108 | deixa_cat | gandules | 95.0 | Hem de plegar les gandules abans que ploga. | gandules |
| valencia3 | avlizador | HG2-112 | correcta_cat | gandules | 95.0 | Les gates de casa són molt gandules. | gandules |
| valencia3 | avlizador | HG2-114 | deixa_cat | panotxa | 95.0 | Cada panotxa té centenars de grans de dacsa. | panotxa |
| valencia3 | avlizador | HG2-117 | correcta_cat | panotxa | 95.0 | La seua àvia era panotxa, de l'horta de Múrcia. | panotxa |
| valencia3 | avlizador | HG2-118 | correcta_cat | panotxa | 65.0 | Una dona panotxa venia hortalisses al mercat. | panotxa |
| valencia3 | avlizador | HG2-119 | correcta_cat | panotxa | 65.0 | La cultura panotxa de l'horta té moltes festes. | panotxa |
| valencia3 | avlizador | HG2-120 | correcta_cat | panotxa | 65.0 | Cantava una cançó panotxa tradicional. | panotxa |
| valencia3 | avlizador | HG2-122 | deixa_cat | panotxes | 95.0 | Les panotxes es posen a assecar al sol. | panotxes |
| valencia3 | avlizador | HG2-124 | deixa_cat | panotxes | 95.0 | Els porcs mengen panotxes seques. | panotxes |
| valencia3 | avlizador | HG2-125 | correcta_cat | panotxes | 65.0 | Les dones panotxes portaven el vestit tradicional de l'horta. | panotxes |
| valencia3 | avlizador | HG2-126 | correcta_cat | panotxes | 65.0 | Les cançons panotxes parlen de la vida al camp. | panotxes |
| valencia3 | avlizador | HG2-127 | correcta_cat | panotxes | 65.0 | Les famílies panotxes celebren la festa de l'horta. | panotxes |
| valencia3 | avlizador | HG2-128 | correcta_cat | panotxes | 65.0 | Les tradicions panotxes de Múrcia són molt antigues. | panotxes |
| valencia3 | avlizador | HG2-131 | deixa_cat | fartanera | 95.0 | Quina fartanera de pastissos que es van fer! | fartanera |
| valencia3 | avlizador | HG2-133 | correcta_cat | fartanera | 95.0 | La meua gossa és molt fartanera i s'ho menja tot. | fartanera |
| valencia3 | avlizador | HG2-135 | correcta_cat | fartanera | 95.0 | No sigues fartanera i deixa'n per als altres. | fartanera |
| valencia3 | avlizador | HG2-139 | deixa_cat | fartaneres | 95.0 | No són bones estes fartaneres de dolços. | fartaneres |
| valencia3 | avlizador | HG2-141 | correcta_cat | fartaneres | 95.0 | Les meues nebodes són molt fartaneres. | fartaneres |
| valencia3 | avlizador | HG2-142 | correcta_cat | fartaneres | 65.0 | Les gates fartaneres s'han menjat el peix. | fartaneres |
| valencia3 | avlizador | HG2-143 | correcta_cat | fartaneres | 95.0 | Eren unes xiques fartaneres i alegres. | fartaneres |
| valencia3 | avlizador | HG2-144 | correcta_cat | fartaneres | 95.0 | Les oques fartaneres no paren de menjar. | fartaneres |
| valencia3 | avlizador | HG2-147 | deixa_cat | reeixida | 95.0 | Va fer una carrera reeixida com a advocada. | reeixida |
| valencia3 | avlizador | HG2-148 | deixa_cat | reeixida | 95.0 | És una adaptació reeixida de la novel·la. | reeixida |
| valencia3 | avlizador | HG2-151 | correcta_cat | reeixida | 100.0 | La clau de la seua reeixida és la constància. | reeixida |
| valencia3 | avlizador | HG2-152 | correcta_cat | reeixida | 95.0 | Ningú no esperava una reeixida tan gran. | reeixida |
| valencia3 | avlizador | HG2-156 | deixa_cat | reeixides | 95.0 | Hem fet campanyes reeixides arreu del país. | reeixides |
| valencia3 | avlizador | HG2-157 | correcta_cat | reeixides | 65.0 | Les reeixides de l'equip omplin el palmarés. | reeixides; omplin |
| valencia3 | avlizador | HG2-158 | correcta_cat | reeixides | 95.0 | Les seues reeixides professionals la van fer famosa. | reeixides |
| valencia3 | avlizador | HG2-159 | correcta_cat | reeixides | 85.0 | Totes les reeixides tenen un preu. | reeixides |
| valencia3 | avlizador | HG2-160 | correcta_cat | reeixides | 65.0 | Ha acumulat moltes reeixides al llarg de la carrera. | reeixides |
| valencia3 | motor | HG2-004 | correcta_val | anou | 45.0 | Afig una anou picada a l'ensalada. | una anou; picada |
| valencia3 | motor | HG2-025 | error_sentit | falta | 100.0 | Encara falta una setmana per a les vacacions. |  |
| valencia3 | motor | HG2-026 | error_sentit | falta | 95.0 | A la sopa li falta una mica de sal. | una mica |
| valencia3 | motor | HG2-027 | error_sentit | falta | 100.0 | A l'equip li falta un jugador per a poder començar. |  |
| valencia3 | motor | HG2-029 | error_sentit | falta | 100.0 | Després de l'accident es va quedar falta del braç dret. |  |
| valencia3 | motor | HG2-031 | error_sentit | nàixer falta | 95.0 | Va nàixer falta d'una mà però toca el piano. |  |
| valencia3 | motor | HG2-037 | error_sentit | faltes | 100.0 | Tu ens faltes molt des que te'n vas anar. |  |
| valencia3 | motor | HG2-038 | error_sentit | faltes | 100.0 | Si tu faltes a la reunió, no podrem votar. |  |
| valencia3 | motor | HG2-039 | error_sentit | faltes | 100.0 | Ara ja només hi faltes tu. |  |
| valencia3 | motor | HG2-040 | error_sentit | faltes | 100.0 | Quan tu faltes, la casa sembla buida. |  |
| valencia3 | motor | HG2-041 | error_sentit | faltes | 100.0 | Les dos germanes van quedar faltes després de la guerra. |  |
| valencia3 | motor | HG2-044 | error_sentit | faltes | 95.0 | Les figures faltes del pesebre s'han de reparar. |  |
| valencia3 | motor | HG2-048 | deixa_cat | deu | 95.0 | El poble es proveïa d'aigua d'una deu natural. | deu |
| valencia3 | motor | HG2-056 | correcta_cat | deu | 85.0 | La factura es deu pagar abans de divendres. | es deu |
| valencia3 | motor | HG2-061 | error_sentit | llavadora | 50.0 | Treballava de llavadora de plats en un restaurant. |  |
| valencia3 | motor | HG2-062 | error_sentit | llavadora | 100.0 | Una dona llavadora portava la roba al riu. |  |
| valencia3 | motor | HG2-063 | error_sentit | llavadora | 100.0 | És una crema llavadora per a pells greixoses. |  |
| valencia3 | motor | HG2-064 | error_sentit | llavadora | 100.0 | La planta llavadora de carbó va tancar fa anys. |  |
| valencia3 | motor | HG2-069 | error_sentit | llavadores | 100.0 | Les llavadores del poble es trobaven al safareig. |  |
| valencia3 | motor | HG2-070 | error_sentit | llavadores | 100.0 | Antigament les llavadores feien la bugada al riu. |  |
| valencia3 | motor | HG2-072 | error_sentit | llavadores | 100.0 | Les dones llavadores cantaven mentre treballaven. |  |
| valencia3 | motor | HG2-093 | error_sentit | bragues | 100.0 | En esta casa, qui porta les bragues és la mare. |  |
| valencia3 | motor | HG2-094 | error_sentit | bragues | 100.0 | El patge duia unes bragues vermelles i una gorra. |  |
| valencia3 | motor | HG2-095 | error_sentit | bragues | 100.0 | Al segle XVI els nobles vestien bragues i jubó. |  |
| valencia3 | motor | HG2-096 | error_sentit | bragues | 100.0 | L'armadura del cavaller cobria les bragues de llana. |  |
| valencia3 | motor | HG2-117 | error_sentit | panolla | 100.0 | La seua àvia era panolla, de l'horta de Múrcia. |  |
| valencia3 | motor | HG2-118 | error_sentit | panolla | 100.0 | Una dona panolla venia hortalisses al mercat. |  |
| valencia3 | motor | HG2-119 | error_sentit | panolla | 100.0 | La cultura panolla de l'horta té moltes festes. |  |
| valencia3 | motor | HG2-120 | error_sentit | panolla | 100.0 | Cantava una cançó panolla tradicional. |  |
| valencia3 | motor | HG2-125 | error_sentit | panolles | 100.0 | Les dones panolles portaven el vestit tradicional de l'horta. |  |
| valencia3 | motor | HG2-126 | error_sentit | panolles | 100.0 | Les cançons panolles parlen de la vida al camp. |  |
| valencia3 | motor | HG2-127 | error_sentit | panolles | 100.0 | Les famílies panolles celebren la festa de l'horta. |  |
| valencia3 | motor | HG2-128 | error_sentit | panolles | 100.0 | Les tradicions panolles de Múrcia són molt antigues. |  |
| valencia3 | motor | HG2-133 | error_sentit | fartada | 100.0 | La meua gossa és molt fartada i s'ho menja tot. |  |
| valencia3 | motor | HG2-135 | error_sentit | sigues fartada | 100.0 | No sigues fartada i deixa'n per als altres. |  |
| valencia3 | motor | HG2-136 | error_sentit | fartada | 100.0 | Una persona fartada no sap dir que no al menjar. |  |
| valencia3 | motor | HG2-141 | error_sentit | fartades | 95.0 | Les meues nebodes són molt fartades. |  |
| valencia3 | motor | HG2-142 | error_sentit | fartades | 100.0 | Les gates fartades s'han menjat el peix. |  |
| valencia3 | motor | HG2-143 | error_sentit | xiques fartades | 100.0 | Eren unes xiques fartades i alegres. |  |
| valencia3 | motor | HG2-144 | error_sentit | fartades | 100.0 | Les oques fartades no paren de menjar. |  |
| valencia3 | motor | HG2-151 | correcta_cat | reeixida | 100.0 | La clau de la seua reeixida és la constància. | reeixida |
| valencia3 | motor | HG2-152 | correcta_cat | reeixida | 95.0 | Ningú no esperava una reeixida tan gran. | reeixida |
| valencia3 | motor | HG2-154 | deixa_cat | reeixides | 95.0 | Les dos últimes temporades van ser reeixides. | reeixides |
| valencia3 | motor | HG2-157 | correcta_cat | reeixides | 65.0 | Les reeixides de l'equip omplin el palmarés. | reeixides; omplin |
| valencia3 | motor | HG2-158 | error_sentit | seues exitoses | 100.0 | Les seues exitoses professionals la van fer famosa. |  |
| valencia3 | motor | HG2-159 | correcta_cat | reeixides | 85.0 | Totes les reeixides tenen un preu. | reeixides |
