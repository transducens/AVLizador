*[Llegeix-ho en castellà](README.es.md)*

# Post-processat amb LLM dels casos marcats

**Estat (06/10/2026): un cas concret ja provat i documentat (vore baix),
la resta encara PENDENT.** El mecanisme general de marcatge a `Token`
(vore "El que falta decidir" més avall) encara no existix -- les proves
fetes fins ara són scripts autònoms fora de `traductor/`, no res
integrat en producció. No integrar res a `traductor/` fins que l'usuari
ho diga explícitament.

Esta carpeta documenta la decisió d'arquitectura
presa el 02/10/2026: en compte de forçar el motor de regles a resoldre
TOT (arriscat -- cada vegada que s'ha provat una heurística automàtica
massa àmplia en este projecte, de l'escaneig de gènere a
`flexio_genere_avl.json` a la distinció "per"/"per a", el resultat ha
sigut pitjor que no tocar-ho), el pla és dividir el problema en dos:

1. **El motor de regles (`traductor/`) tradueix i, de pas, marca** els
   punts on no té prou confiança -- sense intentar adivinar-los.
2. **Un LLM revisa NOMÉS eixos punts marcats**, amb el context de la
   frase i les guies de `../../02_regles_dialectals/docs_gramatica/`
   (GEIEC/GNV completes + les comparatives dialectals derivades) com a
   referència normativa -- no tota la frase de zero, com fan les etapes
   3-4 amb el corpus sintètic actual.

## Per què així i no d'una altra manera

L'alternativa (un LLM que revisa/corregix la frase sencera) ja existix en
este projecte: és exactament el que fan les etapes 3-4
(`03_seleccio_de_model/`, `04_corpus_sintetic/`) amb qwen2.5:14b. Eixe
enfocament funciona raonablement bé (BLEU ~93) però **al·lucina** -- la
revisió manual va trobar ~20% d'errors reals sense relació amb cap regla
dialectal (vore `../../documentacio/metodologia_i_resultats.md`, seccions
6 i 9). L'interés d'un motor de regles és precisament que no pot
al·lucinar: si no sap una paraula, no la toca. Mantindre eixa propietat
vol dir que el LLM només ha d'intervindre a on el motor ho demane
explícitament, no sobre el text sencer.

## Cas provat (06/10/2026): ambigüitat present indicatiu/subjuntiu de 1a persona

### Per què este cas i no un altre

Decisió explícita de l'usuari d'acotar el primer experiment a UN SOL
fenomen, deixant la resta de casos "problematica" de
`conjugacions_dialectals.json` (locucions fixes, col·lisions homògrafes
amb substantius...) fora: en valencià, la mateixa forma escrita servix
per al present d'indicatiu I el de subjuntiu en 1a persona singular
(p.ex. "plantege" -> "plantejo" indicatiu / "plantegi" subjuntiu).
`ConjugacionsDictRule` ja exclou estes formes del lookup (vore el seu
docstring), així que hui no es tradueixen mai -- l'objectiu és veure si
un LLM pot decidir el mode correcte mirant el context de la frase.

### Dades: 3.004 formes ambigües, filtrat de falsos positius nominals

`identifica_ambigues.py` calcula, des de les 4 fonts de Mauricio, totes
les formes valencianes amb EXACTAMENT 2 traduccions catalanes candidates
que comparteixen arrel i difereixen només en la vocal final (-o
indicatiu / -i subjuntiu): **3.004 formes**. Busca-les tal qual en un
corpus real dona MOLTS falsos positius: moltes d'eixes formes són MOLT
més freqüents com a substantiu ("compte", "objecte", "projecte",
"base"...) que com a conjugació d'un verb rar -- el mateix patró de
col·lisió homògrafa ja documentat a `traductor/README.md`. Filtre
aplicat: exigir que un dels dos candidats aparega literalment com a
paraula en la traducció catalana de referència -- açò descarta quasi
tots els substantius (que es queden igual en la referència) i, de pas,
dona una "veritat" automàtica sense anotar res a mà.

Resultat sobre el corpus del BOE (`dades/boe_net/`, 260.345 frases):
**17.785 frases amb forma ambigua i candidat confirmat**, 96% subjuntiu
/ 4% indicatiu (el BOE és registre legal, ple de subordinades "que").
Sobre el benchmark curat de 150 frases
(`03_seleccio_de_model/benchmark_corpus.json`): només **2 frases** amb
el patró confirmat -- eixe benchmark no és un bon corpus per a este
fenomen concret (cada frase hi està triada per a il·lustrar UN altre
fenomen dialectal). El script ja accepta qualsevol corpus amb
`--corpus --format --camp-valencia --camp-catala --camp-doc` per si cal
repetir açò sobre un altre conjunt.

El mostreig és ESTRATIFICAT per classe de veritat (no a l'atzar), perquè
amb 96%/4% una mostra a l'atzar eixiria quasi tota subjuntiu i amagaria
com es comporta cada via en la classe minoritària -- justament on més es
veu la diferència real entre vies.

### Les 3 vies comparades

| Via | Què fa el LLM | Risc principal |
|---|---|---|
| **A** -- frase sencera | Tradueix tota la frase de zero | Pot alterar o retallar parts que ja estaven bé (generació oberta sense restricció) |
| **B** -- nomes la paraula | Tradueix NOMÉS la paraula marcada, amb el context de la frase | Pot "inventar" una forma que no és cap dels dos candidats coneguts |
| **C** -- classificació | NOMÉS classifica indicatiu/subjuntiu; la forma final ix d'una taula ja coneguda | Cap -- mai genera text nou, nomes tria entre 2 opcions |

Prompt: `compara_postprocessat.py` fa servir `guia_traduccio_dialectal.md`
com a context (demanat explícitament), amb un avís honest: eixa guia NO
cobrix mode verbal (nomes determinants/pronoms/preposicions/adverbis),
així que el criteri real d'indicatiu/subjuntiu (subordinada amb "que"
depenent de voluntat/necessitat/dubte, etc.) s'afig a banda, al prompt.

### Resultats (17 frases reals del BOE, mateixa mostra, 2 models via Ollama/Abaco)

| Via | qwen2.5:14b | qwen3:8b |
|---|---|---|
| A -- frase sencera | 5/17 (29%) | 6/17 (35%) |
| B -- nomes la paraula | 11/17 (65%) | 10/17 (59%) |
| C -- classificació | **14/17 (82%)** | **13/17 (76%)** |

Desglossament per classe (important: nomes 4 de les 17 frases eren
indicatiu, la classe dificil i minoritaria):

| Via | subjuntiu (n=13) qwen2.5 | indicatiu (n=4) qwen2.5 | subjuntiu (n=13) qwen3:8b | indicatiu (n=4) qwen3:8b |
|---|---|---|---|---|
| A | 5/13 | 0/4 | 6/13 | 0/4 |
| B | 10/13 | 1/4 | 10/13 | 0/4 |
| C | 12/13 | 2/4 | 10/13 | **3/4** |

**Conclusions principals**:
1. **La via C guanya amb marge en els dos models** -- és l'única que mai
   pot "al·lucinar" una forma inexistent, perque la substitució final
   sempre ve d'una taula tancada de 2 opcions, mai del LLM.
2. **Cada model falla de manera distinta** en les vies A/B: qwen2.5:14b
   inventa paraules sense sentit ("oposiussenpt", "determineix",
   "maneu"); qwen3:8b sovint simplement deixa la paraula original sense
   traduir ("enquadre", "dispose", "licite", "mane") -- un fallo "mes
   honest" pero fallo igualment.
3. **Els casos d'indicatiu (la classe minoritària) són els mes dificils
   en general, pero NO igual als dos models**: qwen2.5:14b nomes l'encerta
   2/4 (es deixa portar pels verbs subjuntius veïns en formules solemnes
   com "jo la sancione" o "Mane a tots..."), mentre que qwen3:8b
   l'encerta 3/4 -- a canvi de perdre un poc de precisió en subjuntiu
   (10/13 enfront de 12/13). Amb nomes 4 exemples d'indicatiu, cal mes
   mostra abans de triar un model definitiu nomes per este criteri.
4. **Bug trobat, no corregit encara**: en un cas, qwen2.5:14b va
   respondre "subjuntivo" (castellà) en compte de "subjuntiu" (català) a
   la via C -- el parser actual no ho reconeix i ho compta com a fallo.
   Pendent d'ampliar el parser per a acceptar variants.

### Temps per frase (dades reals, 06/10/2026, GPU d'Abaco)

Des que `compara_postprocessat.py` mesura els segons de cada crida (camp
`segons` dins de cada `via_a`/`via_b`/`via_c`, i un resum al final de
l'execució), ja hi ha dades reals de 3 models sobre GPU (no nomes el
test trivial per CPU local de 65s d'abans, que no era representatiu):

| Model | Via A (frase sencera) | Via B (nomes paraula) | Via C (classificació) |
|---|---|---|---|
| qwen2.5:14b | 5,7s | 2,0s | **0,6s** |
| qwen3:8b | 4,1s | 1,2s | **0,4s** |
| qwen3:14b | 18,6s (un cas va pujar a 34s) | 1,9s | **0,6s** |

**La via C no nomes és la mes fiable -- també és, de llarg, la mes
rapida**: entre 7 i 50 vegades mes rapida que la via A, i 2-4 vegades mes
rapida que la B. Te sentit: la via C nomes genera una paraula d'eixida
("indicatiu"/"subjuntiu"), mentre que la A ha de regenerar la frase
sencera i la B almenys la forma catalana completa. Això reforça la
decisió de l'arquitectura C des de dos angles independents (precisió I
cost), no nomes un.

### Prova creuada amb 3 models sobre el benchmark (06/10/2026)

Mateixes 2 frases del benchmark (`base`/"quan el tractament es base..."
i `recupere`) provades amb qwen2.5:14b, qwen3:8b i qwen3:14b:

| Model | A | B | C |
|---|---|---|---|
| qwen2.5:14b | 0/2 | 0/2 | 1/2 |
| qwen3:8b | 0/2 | 0/2 | 1/2 |
| qwen3:14b | 0/2 | 1/2 | 0/2 |

Mostra massa xicoteta (n=2) per a traure conclusions de precisió, pero
revela una troballa interessant: **els 3 models, sense excepció, fallen
la via C en el cas "quan el tractament es base en el seu consentiment"**
(el trien com a indicatiu quan la referència diu "es basi", subjuntiu).
Pot ser un patró sistemàtic no cobert pel criteri actual del prompt:
"quan" + present pot exigir subjuntiu en català formal en según quin
tipus de clausula (condicional/generica), i el criteri explicit que es
dona hui al LLM (vore `CRITERI_MODE_VERBAL` en `compara_postprocessat.py`)
no ho menciona explícitament -- candidat clar per a ampliar el prompt
quan hi haja mes exemples d'este patró.

## Benchmark INTEGRAT (06/10/2026): motor + postprocessat mesurat sobre el benchmark real

Tot l'anterior mesurava l'encert AÏLLAT per paraula (compara els
candidats coneguts). Pas següent: mesurar l'efecte REAL sobre la
traducció completa, integrant el postprocessat dins del pipeline de
veres i avaluant amb BLEU/chrF/exacte -- les MATEIXES mètriques
d'`evalua_models.py`, directament comparables amb el 89/150 (59,3%) ja
conegut.

Nou script: `benchmark_integrat.py` -- aplica les 9 regles de
`RuleEngine` (replicades manualment per a poder intervindre abans de
`detokenize()`, mateix patró que `genera_muestra_test_dialectal.py`),
detecta tokens que casen amb el patró ambigu i que el motor ha deixat
sense traduir, crida el LLM (via B o C) i aplica la forma triada
DIRECTAMENT a la traducció final.

### Troballa 1 (abans de corregir): el detector sense filtre REGRESSIX el benchmark

Primera prova (qwen2.5:14b, via C, 150 frases, sense cap filtre
addicional):

| | Exacte | BLEU | chrF |
|---|---|---|---|
| Nomes regles (base) | 89/150 (59,3%) | 95,31 | 98,42 |
| Regles + postproc C | **78/150 (52,0%)** | 94,18 | 98,09 |

**Empitjora -11 frases.** Causa: de les 28 paraules detectades, nomes 2
eren verbs ambigus de veres (`base`->`basi`, `recupere`->`recuperi`, els
dos encertats). Les altres 26 son substantius/preposicions homògrafes
("entre", "sobre", "poble", "informe", "pacte", "contacte"...) que el
motor ja deixava CORRECTAMENT sense tocar, i que el LLM, obligat a
triar entre indicatiu/subjuntiu, va convertir en verbs inventats
("entre"->"entro", "poble"->"pobli", "informe"->"informo"...).

**Intentat i descartat**: restringir per llista de paraules o per font
(nomes els 156 verbs originals, abans de `conjugaciones_nuevo.json`).
No funciona -- comprovat directament sobre les dades: "base" ÉS alhora
un cas real (frase "quan el tractament es base en...") i un fals
positiu (altres 3 frases on es nomes el substantiu), **la mateixa
paraula, el mateix flag `problematica: true`, la mateixa font**. No hi
ha cap propietat estàtica que distinga els dos usos -- nomes el context
de la frase ho fa, que és justament el que decidix el LLM.

### Correcció aplicada: 3a opció "cap" (no és este verb ací)

`via_b` i `via_c` (`compara_postprocessat.py`) ara permeten una 3a
resposta explícita -- "CAP" (B) / "cap" (C) -- quan la paraula marcada
NO funciona com el verb ambigu en eixe context concret. Quan la
referència no confirma cap dels 2 candidats (probable substantiu), la
resposta CORRECTA ara es "cap" -- açò permet per fi avaluar també estos
casos (abans quedaven fora de l'encert, en la categoria "sense veritat
coneguda").

*(pendent: tornar a mesurar amb esta correcció i actualitzar la taula de
dalt -- en curs)*

### Baseline multi-model (06/10/2026, en curs)

Triats per l'usuari: `gemma4:12b`, `qwen3:8b`, `qwen3:14b`, vies B i C,
sobre el benchmark complet. Script de SLURM:
`slurm/benchmark_integrat_multimodel.sh` (3 GPUs en paral·lel, igual
patró que `rellanca_benchmark.sh`). *(resultats pendents)*

### Eines i on estan els resultats

- `identifica_ambigues.py` -- calcula les 3.004 formes i la mostra
  estratificada (ara reutilitzable sobre qualsevol corpus, vore dalt).
- `compara_postprocessat.py` -- executa les 3 vies amb el model triat.
- `slurm/compara_postprocessat.sh` -- job de SLURM per a Abaco (model i
  límit de frases com a arguments, vore capçalera del script).
- `resultats_comparativa_ABC_<model>.json` -- eixida de cada execució
  (no versionat encara al git, generat per sessió).
- Visualització: artifact HTML a Claude amb pestanyes per model i
  comparativa cap a cap -- demana l'enllaç si el necessites, o torna a
  pegar un JSON de resultats nou per a regenerar-lo.
- `benchmark_integrat.py` -- motor + postprocessat mesurat sobre
  `benchmark_corpus.json` amb BLEU/chrF/exacte reals (vore secció
  "Benchmark INTEGRAT" dalt). Necessita l'arrel del repo (`traductor/`,
  `02_regles_dialectals/`, `03_seleccio_de_model/`) -- vore
  `AVLIZADOR_ROOT` si es puja a un entorn amb estructura plana com Abaco.
- `slurm/benchmark_integrat_multimodel.sh` -- job de SLURM que corre
  `benchmark_integrat.py` amb 3 models en paral·lel (una GPU cada un),
  vies B i C.

## El que falta decidir abans d'escriure cap codi

- **Format de la marca**: a nivell de `Token` (afegir un camp com
  `necessita_revisio: bool` o `candidat_regla: str | None` a la classe
  `Token` de `traductor/rules/__init__.py`), a nivell de frase sencera, o
  tots dos. Encara no decidit -- no tocar `Token` fins que es decidisca.
- **Quines regles etiquegen i quan**: per exemple, una futura regla per a
  "per"/"per a" podria NO decidir, i en compte d'això marcar el token
  "per" com a candidat quan detecte el patró ambigu (vore
  `traductor/README.md`, secció "DECISIÓ D'ARQUITECTURA" 02/10/2026, per
  als 3 casos ja identificats com a massa arriscats per a una regla
  directa).
- **Quin model**: local via Ollama (coherent amb la resta del projecte,
  qwen2.5:14b ja en ús) o un altre -- pendent de provar cost/qualitat
  sobre una mostra xicoteta de casos marcats abans de triar.
- **El LLM proposa o nomes senyala**: si l'eixida del LLM substituïx
  directament el text marcat, o si nomes genera un informe per a revisió
  humana (més lent, però cap risc d'al·lucinació silenciosa sobre dades
  ja marcades com a dubtoses).

## Com continuar quan es retome

1. Decidir el format de marca i afegir-lo a `Token` + a, almenys, una
   regla real (candidat natural: la distinció "per"/"per a" documentada
   a `docs_gramatica/guia_traduccio_dialectal.md`, bloc C2).
2. Executar `../traduccio_massiva.py` sobre un corpus real i comptar
   quants punts queden marcats -- això dona una primera idea del volum
   real abans de triar model ni dissenyar el prompt.
3. Provar el LLM triat sobre una mostra xicoteta dels punts marcats,
   mateix mètode que la resta del projecte: evidència abans que
   implementació completa.
