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
