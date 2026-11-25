# Jutge LLM obert, només amb la traducció (04/11/2026)

XCOMET-XL no veu el dialecte: el català sense traduir n'ix primer (vore
`../comet/README.md`). El supervisor va proposar provar un dels millors
sistemes de la tasca d'avaluació de la qualitat del **WMT26** (Lavie et
al. 2026, *Findings of the WMT26 Shared Task on Automated Translation
Quality Evaluation Systems*) que:

1. faça estimació de la qualitat **només amb la traducció** (sense origen
   ni referència),
2. use un **model obert**,
3. tinga **suport per al català**,

i mirar-lo també amb **parells contrastius** valencià–català.

## Elecció del sistema

Al WMT26 els primers llocs són de LLM sense ajust amb el prompt
**GEMBA-ESA** (dues fases: trossos amb error i nota 0-100). xCOMET queda
l'últim en la tasca 1 (taula 4) i molt avall en la 2 (taula 8). Els
oberts:

| Model | WMT26 (8 direccions prioritàries) | Català | En Ollama |
|---|---|---|---|
| Gemma 4 31B-IT | tasca 1: llocs 5-13 (F1 ~32, sense referència 32,0); tasca 2: 6-16 | No apareix a la fitxa (diu "140+ idiomes en el preentrenament, 35+ amb suport directe") | `gemma4:31b`, ~20 GB |
| Qwen 3.6 35B-A3B (MoE, 3B actius) | tasca 1: 14-21 (29,8 amb raonament, 24,6 sense); tasca 2: 11-18 | Sí: el català és a la llista oficial de 119 idiomes de Qwen3 | `qwen3.6:35b-a3b`, ~23 GB |

Criteri de l'usuari: obert i amb català → **Qwen 3.6** (`--array=0`).
Gemma 4 quedava preparat (`--array=1`) perquè és el millor obert del WMT26,
però **es descarta** (decisió de l'usuari, 04/11/2026): Qwen 3.6 ja dona
la resposta i no s'espera que Gemma la canvie. Cap dels dos es va avaluar en català al WMT26 (no hi havia cap
direcció cap al català).

## Què s'hi fa

`jutge_gemba.py` aplica GEMBA-ESA (el prompt de l'apèndix E del WMT26)
**només amb la traducció**. Canvis mínims respecte de l'original:

- sense blocs d'origen ni de referència;
- fora les categories d'*accuracy* (sense origen no es poden jutjar);
- escala de la fase 2 amb punts de referència de fluïdesa (no hi ha
  significat amb què comparar);
- en *Domain requirements* (on el WMT posa el registre de cada domini)
  es diu que el text ha de ser **valencià segons la norma de l'AVL**,
  formal en el BOE.

Es puntuen els 13 sistemes del baseline (`../baseline_llm/resultats/`),
AVLizador 1.1.0 (`../comet/entrades/`) i la **referència valenciana** com
un sistema més. **Parells contrastius**: per a cada frase del manual
(458), la versió valenciana (referència) i la catalana ("sense traduir");
el resum diu en quantes el jutge prefereix el valencià. Es donen dues
notes: la de la fase 2 i la que ix dels errors (100 − 10 per major − 2,5
per minor, la conversió del WMT26).

Temperatura 0 i sense raonament (al WMT26, amb Gemma, raonar quasi no
canvia res; amb Qwen sí que ajuda, `PENSA=1`, però és molt més lent).
Els textos repetits es puntuen una vegada (3.506 textos diferents en
total; primer els 1.173 de referència, sense traduir, AVLizador i motor)
i hi ha una memòria cau (`resultats/<model>/cache.jsonl`, amb les
respostes crues) per a reprendre si el job s'acaba per temps.

## Com llançar-ho en Abaco

```bash
cd ~/scrapeo/AVLizador && git pull && git checkout comet
cd pipeline/03_seleccio_de_model/jutge_llm
LIMIT=10 sbatch --array=0 jutge_llm.sh     # prova: 10 frases per sistema
cat logs/<jobid>_0_jutge_llm.out           # s/text i la taula
sbatch --array=0 jutge_llm.sh              # Qwen 3.6, tot
sbatch --array=1 jutge_llm.sh              # Gemma 4 31B (descartat, no s'ha llançat)
```

Demana 2 GPU (els models no caben en una d'11 GB); Ollama reparteix les
capes i el que no càpia ho posa en CPU. Ollama ha de ser prou nou per a
`qwen3.6` (si `ollama pull` falla, actualitzar-lo). Fa servir `python3`
del sistema: no necessita cap paquet.

Portar els resultats (des de `scrapeo/` en local):

```powershell
scp -r nmartin@abaco:scrapeo/AVLizador/pipeline/03_seleccio_de_model/jutge_llm/resultats pipeline/03_seleccio_de_model/jutge_llm/
scp "nmartin@abaco:scrapeo/AVLizador/pipeline/03_seleccio_de_model/jutge_llm/logs/*" pipeline/03_seleccio_de_model/jutge_llm/logs/
```

`python jutge_gemba.py resum resultats/<model>/` torna a fer la taula.

## Resultats

### Qwen 3.6 35B-A3B (job 2712 de prova, 2719 complet, 04/11/2026)

Les 42 capes en GPU (2 targetes), uns 5 s per text, sense errors. Taula
completa en `resultats/qwen3.6-35b-a3b/resum.md`:

| Sistema | Nota (fase 2) | BOE | AVL | Nota des dels errors | Frases amb error |
|---|---|---|---|---|---|
| salamandra-7b-instruct | 81,28 | 79,45 | 83,41 | 92,69 | 319/458 |
| llama3.1:8b | 80,25 | 78,09 | 82,75 | 91,78 | 333/458 |
| qwen3:14b | 79,57 | 77,83 | 81,59 | 91,92 | 333/458 |
| **Sense traduir** (català tal qual) | **79,22** | 78,17 | 80,44 | 91,80 | 335/458 |
| qwen3:8b … gemma3:12b | 79,07 … 78,83 | | | | |
| **Referència valenciana** (manual) | **77,00** | 75,16 | 79,14 | 88,89 | 402/458 |
| AVLizador 1.1.0 | 76,62 | 74,45 | 79,14 | 87,97 | 405/458 |
| AVLizador, només el motor | 76,20 | 74,15 | 78,58 | 87,97 | 406/458 |
| qwen2.5:7b … mistral-nemo:12b | 75,59 … 70,29 | | | | |

Parells contrastius (referència valenciana / la mateixa frase en català):

| Nota | Guanya el valencià | Empat | Guanya el català | Diferència mitjana |
|---|---|---|---|---|
| Fase 2 | 132 | 151 | 175 | −2,22 |
| Des dels errors | 89 | 155 | 214 | −2,91 |

**Conclusió: el jutge tampoc veu el dialecte, com XCOMET.** Prefereix el
català al valencià revisat a mà, encara que el prompt demana la norma de
l'AVL:

- De 893 trossos amb error en la referència, **242 cauen en formes
  valencianes normatives** ("esta", "este", "estes", "estos",
  "servicis", "seua", "siga", "sigut", "tindre", "ací", "haja"…), quasi
  sempre com a *spelling*. En el català només 64 de 641 toquen "aquest*",
  "seva", "serveis"…
- AVLizador queda quasi igual que la referència (76,62 / 77,00): el jutge
  no el castiga per mal traduït, sinó per valencià.
- A vegades el tros amb error és raonament al·lucinat del model i no
  està en la frase (BM-AVL-079: dubta d'un "fauen" que no existix; la
  frase diu "facen").

Gemma 4 31B (`--array=1`): **descartat**, no s'ha llançat (decisió de
l'usuari, 04/11/2026).

## Prompt «valencia»: amb l'original i la norma valenciana (24/11/2026)

Petició de l'usuari: que el jutge avalue la qualitat de la traducció al
valencià **sense penalitzar el valencià**. Mateix model (Qwen 3.6) i mateix
protocol en dues fases; canvis (`--prompt valencia`, `jutge_gemba.py`):

1. **Veu l'original català**: els nostres errors són de sentit ("cop" ->
   "vegada", "calces" -> "bragues", "La exitosa del projecte"); sense
   original només es veu la gramàtica. Tornen les categories d'*accuracy*;
   l'escala de la fase 2 és la del WMT amb origen (significat + gramàtica).
2. **Bloc «Valencian norm»**: tota forma acceptada per l'AVL és correcta,
   amb exemples de les que marcava el prompt anterior (este, esta, seua,
   servicis, siga, sigut, tindre, hui, ací...); les paraules del DNV que
   pareixen castellanes també (gasto, exitós, llavadora), i l'accentuació
   valenciana (é tancada: francés, cinqué, sotmés, comprén; diacrítics de
   l'AVL).
3. **Concordança amb el nom valencià** ("la despesa" -> "el gasto"): és on
   fallen de veritat les nostres substitucions (el prompt anterior premiava
   "Amb esta fi").
4. **Les formes catalanes que també accepta l'AVL no són error** (aquest,
   servei, -eix): el jutge mesura qualitat; el dialecte, el GD. Per això no
   hi ha la categoria *non-translation* i el català sense traduir pot
   traure nota alta.
5. Els errors de sentit coneguts (vegada per cop, bragues per calces,
   exitosa com a nom) hi van com a exemple (decisió de l'usuari).

Job: `jutge_valencia.sh` (genera abans, amb `avlizador avalua`, les
traduccions d'AVLizador i del motor sol en `entrades_valencia/`):

| Conjunt | Sistemes | Per a què |
|---|---|---|
| manual (458) | referència, sense traduir, gemma3:12b, AVLizador | comparar amb el prompt anterior; trossos en formes valencianes (abans 242 / 893 en la referència) |
| homografs (249), homografs_v2 (144) | referència, AVLizador, motor sol | el motor tradueix sempre: si el jutge veu els errors de sentit, la referència ha de guanyar quasi sempre on el motor és distint |

```
cd ~/scrapeo/AVLizador && git fetch && git checkout jutge-valencia && git pull
cd pipeline/03_seleccio_de_model/jutge_llm
LIMIT=10 sbatch jutge_valencia.sh     # prova
sbatch jutge_valencia.sh              # tot (~2.200 textos, unes 4-5 h)
```

Eixida en `resultats/valencia/<conjunt>/qwen3.6-35b-a3b/` (`resum.md` amb
la taula «cada sistema contra la referència»).

### Resultats (caiman, amb raonament; jobs 2455, 2456, 2484 i 2526, 24-25/11/2026)

Qwen 3.6 amb raonament (`PENSA=1`), prompt `341f0eeb`. Carpetes
`resultats/valencia/<conjunt>/qwen3.6-35b-a3b_pensa/`; l'anàlisi,
`python analitza_valencia.py` → `resultats/valencia/analisi.md` (taules) i
`analisi_detall.md` (frase a frase). Falta una frase: la referència de
BM-BOE-001 (manual) fa caure el llama-server cada vegada (HTTP 500, també
en tornar-la a llançar, job 2526); el manual de la referència té 457
frases. El benchmark d'homògrafs v1 té l'id RC047 repetit (dues variants
de la mateixa frase): `analitza_valencia.py` en compta una (248).

**Manual (458)**:

| Sistema | Nota (fase 2) | BOE | AVL | Frases amb error |
|---|---|---|---|---|
| Sense traduir | 99,25 | 99,76 | 98,66 | 28 |
| AVLizador 2.0.1 | 97,72 | 97,09 | 98,44 | 98 |
| Referència | 94,64 | 91,18 | 98,63 | 159 / 457 |
| gemma3:12b | 94,17 | 94,71 | 93,54 | 171 |

- **Ja no castiga el valencià.** Trossos amb error de la referència: 893 →
  245, i els que cauen en una forma valenciana (marcador del GD de la frase),
  426 → 70 (mateix càlcul per als dos prompts). Els que queden són sobretot
  accents tancats i paraules del DNV: interés 7, comité 3, perjuí 3, díhuit
  3, ferramenta(es) 4, estés 2, depén 2, servicis 2; esta/este/seua/siga, que
  abans eren els més marcats, quasi desapareixen.
- **En l'AVL** (la referència només canvia el dialecte) el jutge és quasi
  neutral: referència / sense traduir 16 guanya la referència, 160 empats,
  35 guanya el català (nota 98,63 / 98,66). Amb el prompt del 04/11, en tot
  el manual: 132 / 151 / 175.
- **En el BOE la referència perd perquè s'aparta de l'original**, i el jutge
  ara ho veu (86 errors d'*accuracy*, 53 majors, enfront de 0 del català):
  futur per present («podrà» 7, «tindrà» 3, «es remetrà», «es regularan»),
  «no» omés (BM-BOE-185), «un altre» per «l'altre», «obligar-lo» per
  «obligar-la». Alguns són errors del jutge («fins» per «finalitats»,
  «reben»). Per això el català sense traduir guanya 140 de 245 frases del
  BOE i n'empata 103.
- **AVLizador contra la referència**: 225 frases distintes; el jutge marca
  alguna de les paraules que canvien en 7. Qui guanya (22 la referència, 100
  empats, 103 AVLizador) és soroll i el BOE de la referència; en l'AVL, 15
  frases distintes: 5 / 9 / 1. Cap error real d'AVLizador nou en les 22 (el
  jutge marca «sol·licitaren» major en AVLizador i menor en la referència,
  o trossos que no hi són: «estes espais»).
- **gemma3:12b sí que perd** (errors de sentit i gramàtica): en l'AVL la
  referència guanya 61 frases i gemma 17.

**Homògrafs**:

| Conjunt | Referència | AVLizador 2.0.1 | Motor sol |
|---|---|---|---|
| v1 (249) | 97,97 | 97,75 | 94,80 |
| v2 (144) | 96,46 | 97,78 | 87,29 |

On el motor sol és distint de la referència, guanya la referència 24 / 70
(v1) i 38 / 69 (v2); el motor, 2 i 2. **El jutge castiga els errors de
sentit, però en veu la meitat més o menys.** En v2 (quasi tot són errors
de sentit del motor): gandula(es) → hamaca(es) 8 de 8, fartanera(es) →
fartada(es) 6/8, rentadora(es) → llavadora(es) 5/8, manques → faltes 5/8,
manca → falta 4/7, calces → bragues 3/4; però nou → anou 3/8 (empat en «cotxe
anou», «a les anou en punt»), nous → anous 1/4, panotxa(es) → panolla(es) 1/8,
reeixides → exitoses 1/2 («Les seues exitoses professionals» = 100). En v1,
cop → vegada/colp no apareix: on el motor és distint és perquè deixa «cop»
(no tria en les col·lisions), i el jutge ho empata (correcte: no és error).

Dues causes:

1. **La llista del bloc «Valencian norm» guanya al sentit.** «anou»,
   «llavadora», «exitosa» i «colp» hi són com a formes correctes, i en el
   raonament el model ho diu: «the prompt explicitly says: anou... so it's
   definitely correct» (cotxe anou), «exitoses... explicitly allowed». La
   línia que diu que una paraula d'un altre sentit és *mistranslation* (amb
   l'exemple d'«exitosa» com a nom) no ho compensa.
2. **No coneix el sentit menys freqüent del català**: «calces» = bragues,
   «gandula» = hamaca, «manques» = faltes, «fartanera» = fartada. Castiga la
   referència quan tradueix bé aquests sentits (HG2-090 «Les bragues són al
   calaix», 45; HG053 «hamaques», 20) i premia AVLizador quan deixa la
   paraula catalana: d'ací ve que AVLizador passe la referència en v2 (guanya
   7, perd 2: en 6 dels 7 la referència tradueix i AVLizador deixa el català;
el setè és HG2-045, on prefereix «aigua molt fred» d'AVLizador, que és
l'error de concordança conegut).

**Conclusió**: amb l'original i el bloc de la norma, el jutge ja no
penalitza el valencià (AVL quasi neutral) i detecta la meitat dels errors de
sentit dels homògrafs i les desviacions de la referència del BOE. No mesura
el dialecte (el català sense traduir n'ix primer, com s'havia decidit: això
ho fa el GD) i premia deixar la paraula catalana en un homògraf, igual que
el nostre criteri (no traduir és un error lleu). Per a mesurar els errors de
sentit, el comparador de homògrafs (encerts / greus) continua sent més
fiable. Llevar de la llista les formes candidates d'un homògraf es va
provar l'endemà (prompt «valencia2», baix): no ho arregla.

### Prova «valencia2»: sense les formes candidates d'un homògraf (job 2527, 25/11/2026)

`--prompt valencia2` (`PROMPT=valencia2` en `jutge_valencia.sh`; empremta
`22ff4239`; «valencia» no canvia, `341f0eeb`): el mateix prompt sense colp,
llavadora, anou, brollador, exitós/exitosa en el bloc «Valencian norm», i
l'exemple de «dos vegades» canviat per «dos persones». Eixida en
`resultats/valencia2/`; anàlisi amb `python analitza_valencia.py --prompt
valencia2`. Només els homògrafs: el manual es va aturar a mitjan (vore
«Velocitat» baix), perquè els homògrafs ja responien la pregunta i en el
manual estes paraules quasi no ixen.

| Conjunt | Referència | AVLizador 2.0.1 | Motor sol |
|---|---|---|---|
| v1 (249) | 97,63 (97,97) | 97,61 (97,75) | 94,44 (94,80) |
| v2 (144) | 95,00 (96,46) | 96,91 (97,78) | 86,46 (87,29) |

(Entre parèntesis, «valencia».) **El jutge no distingix el sentit: llevar
una paraula de la llista només gira el biaix.** Amb «valencia» acceptava
anou/colp/llavadora sempre; amb «valencia2» les marca quasi sempre, també
quan són correctes.

- **Millora**: veu més vegades l'«anou» erroni del motor. Motor sol contra
  la referència (guanya la referència / empat / guanya el motor): nou → anou
  v1 2/5/0 → 6/1/0, v2 3/5/0 → 7/1/0; nous → anous (v2) 1/3/0 → 4/0/0;
  panotxes → panolles 1/3/0 → 3/1/0.
- **Empitjora**: castiga la referència quan la paraula és correcta.
  «colp» (colp de porta, colp de sort): el motor deixa «cop» i ara és el
  motor qui guanya en 5 frases (colp → cop 0/11/0 → 0/6/5); colps → cops
  0/6/0 → 0/3/3.
  «anou» fruit: HG057 «Va trencar una anou amb les dents» 85, HG2-004 «Afig
  una anou picada a l'ensalada» 65 (7 frases). «llavadora» electrodomèstic:
  HG2-066 «Les llavadores modernes gasten poca aigua» 65, error major (4
  frases). Trossos de la referència en formes valencianes: v1 19 → 29, v2
  11 → 18.
- On el motor fa un error de sentit que no depén de la llista, igual o
  pitjor: rentadora → llavadora 3/1/0 → 2/2/0, manques → faltes 5/3/0 →
  3/5/0; gandula, calces, fartanera, igual que abans.

**Conclusió**: Qwen 3.6 (35B-A3B, quantitzat a 4 bits, Q4_K_M) no sap en
quin sentit és valenciana cadascuna d'estes paraules; cap llista ho
arregla. Per als errors de sentit dels homògrafs, el jutge no servix: hi
mana la comparació exacta amb la referència (comparador d'homògrafs). El
jutge es queda per a la qualitat general en el manual, amb «valencia».

**Velocitat i GPU en caiman (25/11/2026)**. El manual anava a ~30 s/text
(ahir, job 2455, ~12 s): el model generava a ~110 tokens/s enfront de ~240,
amb raonaments de la mateixa llargària. El job tenia 4 CPU
(`--cpus-per-task=4`) i el llama-server arranca amb 36 fils (410 % de CPU,
GPU al 17 %): tot apunta a falta de CPU (el 2455 en tenia 8; no s'ha
comprovat). A més, **la GPU no era la que donava SLURM**: SLURM va assignar
la 0 (`scontrol show job -d <id>` → `IDX:0`, `CUDA_VISIBLE_DEVICES=0`), però
CUDA numera les GPU en un altre orde que `nvidia-smi`, i Ollama va carregar
el model en la del bus `e1:00.0`, que és la 3 de `nvidia-smi`. Per a
comprovar-ho:

    nvidia-smi --query-gpu=index,pci.bus_id --format=csv,noheader
    nvidia-smi --query-compute-apps=gpu_bus_id,pid,used_memory --format=csv,noheader | while IFS=, read bus pid mem; do echo "$bus $pid $mem $(ps -o user= -p $pid)"; done

Arreglat: `jutge_valencia.sh` fa `export CUDA_DEVICE_ORDER=PCI_BUS_ID` abans
d'`ollama serve` (CUDA numera aleshores les GPU com SLURM), i diu que no es
baixen les CPU per davall de les 8 per defecte. El job 2527 es va cancel·lar
a mitjan manual.

### Meta-avaluació en els homògrafs: ¿el jutge encerta? (25/11/2026)

`python meta_homografs.py --resultats resultats --eixida
resultats/meta_homografs.md` (sense tornar a puntuar res). Veritat: el
benchmark diu la paraula catalana (`paraula`) i la correcta (`esperat`) de
cada frase; per a cada eixida (referència, AVLizador, motor sol) es busca la
paraula que hi ha en eixe lloc (alineada amb l'original) i es classifica en
correcta valenciana (anou fruit, colp, bragues…), correcta catalana (nou
adjectiu, calces de vestir…), deixa el català (lleu) o error de sentit
(greu). El jutge «marca» el lloc si un tros amb error conté la paraula. Tots
els errors de sentit són del motor (90); la referència i AVLizador en tenen
0.

| | «valencia» | «valencia2» |
|---|---|---|
| Errors de sentit marcats (exhaustivitat) | 47/90 (52 %) | 64/90 (71 %) |
| Precisió (dels llocs marcats, quants són errors) | 57 % | 43 % |
| Forma valenciana **correcta** marcada | 33/306 (11 %) | 80/306 (26 %) |
| Paraula catalana correcta marcada | 2/237 (1 %) | 4/237 (2 %) |
| Deixa el català (lleu) marcat | 1/75 (1 %) | 0/75 |
| AUC de la nota (error vs. correcta) | 0,74 | 0,78 |
| Nota mitjana: forma valenciana correcta / catalana correcta | 94,4 / 99,6 | 92,4 / 98,9 |

- **Sí que penalitza formes valencianes correctes**, deu vegades més que les
  catalanes correctes, però no per ser valencianes sinó **perquè no sap què
  volen dir** (ho diu en el raonament): «panolla» = «a small loaf of bread»
  (és la panotxa), «gandula» = gandula (no sap que és hamaca, i marca
  «hamaca» com a *mistranslation*), «calces» = mitges (marca «bragues»), i
  en «valencia2», «the standard Valencian word for nut is nou» (marca
  «anou»), «de cop» = fixed expression (marca «colp»).
- Els errors que veu millor són de les mateixes paraules que marca encara
  que siguen correctes (calces, gandula): part de l'«exhaustivitat» és
  marcar la forma, no el sentit.
- Deixar el català no el castiga mai (com volíem: és un error lleu).

**Proposta per a fer-lo útil (no provada)**: en compte d'una llista fixa de
formes correctes, donar-li en cada frase el significat de les paraules
dialectals que hi ha, tret del lèxic (`lexic_general.json`: català,
valencià, castellà). Per exemple: «anou = nou (cat.) = nuez; hamaca = gandula
(cat.) = tumbona; panolla = panotxa (cat.) = mazorca». Així pot jutjar el
sentit («cotxe anou» = cotxe nuez) sense que la forma diga res a favor ni en
contra. Es mesuraria amb `meta_homografs.py`: ha de baixar la forma
valenciana correcta marcada (11 %) sense baixar l'exhaustivitat; després, el
manual, per a vore que no torna a castigar el valencià.
