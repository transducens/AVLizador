*[Llegeix-ho en castellà](README.es.md)*

# Comparativa: qwen2.5:14b vs. gemma3 vs. salamandra vs. SalamandraTA

Prova de si hi ha una alternativa millor a qwen2.5:14b per a la conversió
occidental→oriental, usant el mateix benchmark de 60 frases
(`03_seleccio_de_model/benchmark_corpus.json`) sobre 5 GPU en paral·lel (4
candidats, un d'ells — SalamandraTA — repartit en 2 GPU).

**Ajustat a les GPU reals del clúster** (node "abaco": 8×11264 MiB = 11 GB
per GPU, arquitectura Turing/compute capability 7.5, confirmat amb
`nvidia-smi`). Amb 11 GB, `gemma3:27b` no cap, i SalamandraTA no cap en
UNA sola GPU ni en bf16 ni quantitzat — vore detall davall.

## Candidats

| | Com se servix | VRAM aprox. | Per què |
|---|---|---|---|
| `qwen2.5:14b` | Ollama | ~9,2 GB (ja confirmat en este node) | El model actual — es recalcula en esta mateixa passada per a tindre una referència neta, en igualtat de condicions |
| `gemma3:12b` | Ollama | ~8 GB | Multilingüe ampli (140+ idiomes), grandària semblant a qwen2.5:14b |
| `hdnh2006/salamandra-7b-instruct` | Ollama | ~4-5 GB | El Salamandra genèric (no el TA) — ja es va provar abans i va perdre contra qwen, però va ser **abans** d'arreglar el tall de frases del corpus; mereix un número fresc. El nom porta el prefix `hdnh2006/` perquè així està publicat al registre d'Ollama, no com a "salamandra-7b-instruct" a soles |
| `BSC-LT/salamandraTA-7b-instruct` | **vLLM, bf16 en 2 GPU** — no Ollama | ~8 GB per GPU (16 GB repartits entre 2, `--tensor-parallel-size 2`) | Model de traducció especialitzat del BSC, suporta explícitament "Catalan (and Catalan-Valencian variety)" |

`gemma3:27b` queda descartat per a esta ronda: a 4 bits pesa ~15-17 GB, no
cap en 11 GB. Si algun dia el proves en GPU de 24 GB+, només cal canviar
la variable corresponent a l'script.

## Per què SalamandraTA no va per Ollama

El propi [model card de BSC-LT](https://huggingface.co/BSC-LT/salamandraTA-7b-instruct)
ho diu explícitament:

> "We strongly discourage using ollama as we have encountered compatibility
> issues that may seriously degrade the model's performance."

Recomanen **vLLM** (sense quantitzar) o **llama.cpp** (versió GGUF, que
BSC-LT no publica oficialment). Per això `comparar_salamandraTA_gemma.sh`
alça un servidor vLLM amb l'API compatible amb OpenAI, i `evalua_models.py`
ara sap parlar amb eixe tipus de servidor (`--model openai`, vore més
avall) — açò és nou a l'script, abans només sabia parlar amb Ollama i
Claude.

Nota important: açò és distint del "salamandra-7b-instruct" genèric que
ja es va provar i va perdre contra qwen (vore `../../documentacio/metodologia_i_resultats.md`,
secció 5). SalamandraTA és un model *de traducció*, no un instructor de
propòsit general — una altra arquitectura d'ús, no una repetició de la
prova anterior.

## Entorn virtual per a vLLM

El node usa un Python "externally managed" (PEP 668, normal en Debian/
Ubuntu recents): `pip install` directe falla amb `error:
externally-managed-environment`. L'script crea un entorn virtual
dedicat en `$HOME/venv_vllm` (variable `VENV_VLLM`, persistent entre
execucions, igual que `$OLLAMA_MODELS`) i instal·la `vllm` ahí — mai amb
`--break-system-packages`, que tocaria el Python de tots els usuaris del
node compartit. No cal fer res a mà; si vols inspeccionar-ho o
reinstal·lar de zero: `rm -rf ~/venv_vllm` i torna a llançar l'script.

**Ni `bitsandbytes` ni `fp8` s'usen — es van provar els dos i els dos van
fallar per motius reals**:
- `bitsandbytes`: la versió de vLLM que cal (vore més avall) ja no ho
  suporta com a mètode (`Unknown quantization method: bitsandbytes`).
- `fp8`: sí que ho suporta vLLM, però exigix compute capability ≥80 (GPU
  Ampere o més noves); este node és Turing, capability 75 — error real
  confirmat (`The quantization method fp8 is not supported for the
  current GPU. Minimum capability: 80. Current capability: 75.`). Este és
  un límit de **maquinari**, no de configuració — cap versió de cap
  paquet ho arregla.

La solució real no és quantitzar més fort, és no quantitzar: repartir el
model complet en bf16 entre 2 GPU amb `--tensor-parallel-size 2` (cada
una carrega només la mitat, ~8 GB, que sí cap en 11 GB amb marge de sobra).
Per això l'script demana 5 GPU en compte de 4.

**`vllm` està FIXAT a la versió `0.9.2`, no "l'última"** (variable
`VLLM_VERSION` al principi de l'script). Instal·lar sense fixar versió
porta vLLM 0.29.0, que exigix PyTorch 2.13.0 compilat per a CUDA 13.0 —
més nou que el driver d'este node (575.57.08, CUDA 12.9), i falla en
arrancar amb `RuntimeError: The NVIDIA driver on your system is too old`.
vLLM 0.9.2 està documentat oficialment com a compatible amb PyTorch 2.6.0
+ CUDA 12.4, que sí cap sota un driver de 12.9 — no és una suposició, és
una combinació de versions coneguda. L'script instal·la amb
`--extra-index-url https://download.pytorch.org/whl/cu124` per a ajudar
`pip` a resoldre eixa combinació, i comprova la versió exacta de `vllm`
ja instal·lada (no només si existix alguna) per a tornar a instal·lar si
l'entorn virtual va quedar amb la versió equivocada d'un intent anterior.

**`transformers` està FIXAT a `<4.54.0`** (variable `TRANSFORMERS_VERSION`).
Sense este límit, `pip` instal·la una versió de `transformers` que ja
registra el model de visió "aimv2" de forma nativa, i vLLM 0.9.2 intenta
registrar-lo també per compatibilitat amb versions antigues —
xoc confirmat: `ValueError: 'aimv2' is already used by a Transformers
config, pick another name`. És un problema conegut i documentat en
diversos projectes que depenen de vLLM 0.9.x, amb este mateix arreglament.

## Les formes de provar SalamandraTA

**`--openai-mode regles`** (el mateix system prompt llarg amb les 10
categories de regles dialectals + glossari dinàmic que usem amb qwen/
gemma) es va provar i es va **descartar**: resultat real 0,13-1,75 BLEU,
0/60 exactes. En lloc d'aplicar les regles, el model repetix fragments
literals de les pròpies instruccions com si foren la traducció (p.ex.
retorna `"ELISION (només 'de', 'la', 'el')..."` en lloc de traduir la
frase). No és un instructor de propòsit general — un system prompt de
~2200 tokens amb regles gramaticals no és el seu format d'entrenament.
Ja no s'executa este mode a l'script (perdre ~2-3 min per repetició sense
cap possibilitat de resultat útil).

L'script prova, una darrere l'altra contra el mateix servidor:

1. **`--openai-mode traduccio`**: la plantilla oficial de traducció del
   model (`"Translate the following text from X into Y..."`), sense cap
   pista. **Resultat real**: 83,54 BLEU, 21,7% exactes — funciona, però
   per davall de qwen/gemma. SalamandraTA tracta valencià i català com una
   sola entrada d'idioma ("Catalan (and Catalan-Valencian variety)"), així
   que no hi ha garantia documentada que distingisca la direcció ell sol.
2. **`--openai-mode traduccio_lexic`**: la MATEIXA plantilla, però afegint
   el glossari dinàmic curt en format `[VOCABULARI: este=aquest,
   roig=vermell]` — el mateix format compacte que ja usen qwen/gemma,
   dissenyat explícitament perquè el model no ho repetisca a la resposta
   (a diferència del system prompt sencer de `regles`). Hipòtesi a
   comprovar: potser el problema de `regles` no era "el model no pot
   seguir cap pista", sinó "no sap què fer amb un bloc d'instruccions
   llarg en un rol `system` que no és el seu format".

## Canvis en `evalua_models.py`

S'han afegit, de forma retrocompatible (res de l'anterior canvia de
comportament):

- `--ollama-url` — per a llançar diverses instàncies d'Ollama en paral·lel,
  cada una en el seu port/GPU (abans la URL estava fixa a `localhost:11434`).
- `--model openai` + `--openai-url` / `--openai-model` / `--openai-mode` /
  `--openai-timeout` — per a parlar amb qualsevol servidor compatible amb
  l'API de xat d'OpenAI (vLLM, etc.), reutilitzant exactament el mateix
  càlcul de BLEU/chrF/chrF++ i informe comparatiu que ja existia.

## Avís de memòria

Ja ajustat per a 11 GB per GPU, però si ho repetixes en un altre clúster,
comprova primer quanta VRAM té cada GPU:
```
nvidia-smi --query-gpu=index,memory.total --format=csv
```
Amb menys d'11 GB per GPU, fins i tot el repartiment en 2 GPU pot no
caber — baixa `GPU_MEMORY_UTILIZATION` o `VLLM_MAX_MODEL_LEN` al principi
de l'script, o puja `VLLM_TENSOR_PARALLEL` a més GPU si en tens de sobra.
Amb 24 GB o més per GPU, pots permetre't `gemma3:27b` i SalamandraTA en
bf16 en **una sola** GPU (`VLLM_TENSOR_PARALLEL="1"` i lleva
`CUDA_VISIBLE_DEVICES=2,4` de la crida a vLLM, deixant només
`CUDA_VISIBLE_DEVICES=2`).

## Com llançar-ho

```bash
# sincronitza els canvis al clúster primer (evalua_models.py + esta carpeta)

cd scrapeo/03_seleccio_de_model/comparativa_salamandraTA_gemma
sbatch comparar_salamandraTA_gemma.sh

# seguir el progrés
squeue
tail -f <jobid>_compara.out
```

## On ixen els resultats

- `03_seleccio_de_model/resultats/benchmark_<model>_<timestamp>.json` — un
  fitxer per candidat (5 en total: gemma3:12b, salamandra-7b-instruct,
  qwen2.5:14b, salamandraTA_traduccio, salamandraTA_traduccio_lexic), igual
  que qualsevol execució normal de `evalua_models.py`.
- `comparativa_salamandraTA_gemma/logs/` — logs de cada servidor (Ollama x3,
  vLLM) i de cada benchmark, per a depurar si algo falla.
- `comparativa_salamandraTA_gemma/informe_comparatiu.txt` — la taula
  comparativa final (BLEU/chrF/chrF++/Exactes), generada per
  `combina_resultats.py` a partir dels 5 fitxers anteriors. Reutilitza el
  mateix format d'informe que ja usa `evalua_models.py --model tots`.

Si vols regenerar només l'informe combinat més tard (sense relançar res):

```bash
python combina_resultats.py --resultats-dir ../resultats --minuts 240
```
