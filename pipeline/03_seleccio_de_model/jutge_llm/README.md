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
Gemma 4 queda preparat (`--array=1`) perquè és el millor obert del WMT26;
el mateix parell contrastiu dirà si sap valencià encara que la fitxa no
el nomene. Cap dels dos es va avaluar en català al WMT26 (no hi havia cap
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
sbatch --array=1 jutge_llm.sh              # Gemma 4 31B, tot (opcional)
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

Gemma 4 31B (`--array=1`): sense llançar.
