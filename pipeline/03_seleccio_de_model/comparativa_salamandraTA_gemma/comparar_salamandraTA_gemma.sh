#!/bin/bash
# comparar_salamandraTA_gemma.sh — Compara, en paral·lel (5 GPUs en total)
# i sobre el mateix benchmark de 60 frases:
#
#   GPU 0:   gemma3:12b               (Ollama)
#   GPU 1:   salamandra-7b-instruct   (Ollama -- el genèric, NO el TA; recalculat
#                                       amb el corpus/prompt ja arreglats)
#   GPU 2+4: salamandraTA-7b-instruct (vLLM, fp16 repartit en 2 GPUs -- vore per què)
#   GPU 3:   qwen2.5:14b              (Ollama -- referència ja coneguda, recalculada
#                                       en esta mateixa passada per a poder comparar
#                                       en igualtat de condicions)
#
# AJUSTAT A 8×11264 MiB (11 GB) de VRAM per GPU, arquitectura Turing/compute
# capability 7.5 (node "abaco", confirmat amb `nvidia-smi`). Dos coses de
# qualsevol configuració "per defecte" NO caben/funcionen i s'han descartat:
#   - gemma3:27b a 4 bits ocupa ~15-17 GB -- no cap en 11 GB. Substituït per
#     salamandra-7b-instruct (~4-5 GB, i és una recomprovació útil: ja el vam
#     provar abans i va perdre contra qwen, però amb el corpus encara sense
#     arreglar -- val la pena un número fresc, ara que sí ho està).
#   - SalamandraTA-7b-instruct en bf16 (la manera per defecte de vLLM) ocupa
#     ~16 GB -- no cap en UNA GPU de 11 GB. Es van provar DUES maneres de
#     cuantitzar-lo per a que cabera en una sola GPU, i les dos van fallar
#     per motius reals, no de configuració:
#       1. bitsandbytes -- la versió de vLLM que cal per a l'altre problema
#          (vore baix) ja no el suporta com a mètode ("Unknown quantization
#          method: bitsandbytes").
#       2. fp8 dinàmic -- SÍ el suporta vLLM, però exigix compute capability
#          >=80 (Ampere o més nou); este node és Turing, capability 75.
#          Error real i confirmat: "The quantization method fp8 is not
#          supported for the current GPU. Minimum capability: 80. Current
#          capability: 75." Este és un límit de HARDWARE, no de versions --
#          cap combinació de paquets ho arregla.
#     La solució real NO és cuantitzar més fort, és no cuantitzar: repartir
#     el model SENCER en bf16 entre 2 GPUs amb --tensor-parallel-size 2 (cada
#     GPU només carrega la meitat, ~8 GB, que sí cap en 11 GB). Per això este
#     script demana 5 GPUs en compte de 4 -- una més per a SalamandraTA.
# Si algun dia proves açò en GPUs Ampere+ de 24 GB (p.ex. RTX 3090/4090,
# A100), pots tornar a 1 sola GPU amb bf16 o fp8 sense el segon canvi.
#
# Per què SalamandraTA NO va per Ollama: el propi model card de BSC-LT
# (https://huggingface.co/BSC-LT/salamandraTA-7b-instruct) ho diu explícitament:
#   "We strongly discourage using ollama as we have encountered compatibility
#    issues that may seriously degrade the model's performance."
# Recomanen vLLM o llama.cpp (versió GGUF, que BSC-LT no publica oficialment).
# Este script fa servir vLLM, servint un endpoint compatible amb l'API de
# chat d'OpenAI que evalua_models.py ja sap cridar (--model openai).
#
# SalamandraTA es prova de DUES maneres (una darrere de l'altra, mateix
# servidor, no calen més GPUs per a la segona). --openai-mode regles (el
# mateix system prompt llarg de regles dialectals que qwen/gemma) es va
# provar i es va DESCARTAR: confirmat que el model repeteix fragments
# literals de les pròpies instruccions en lloc de traduir (0,13-1,75 BLEU,
# 0/60) -- no és un instructor de propòsit general, un system prompt de
# ~2200 tokens amb 10 categories de regles no és el seu format.
#   1. --openai-mode traduccio        -> la plantilla oficial de traducció
#                                         del model ("Translate the following
#                                         text from X into Y..."), sense cap
#                                         pista. SalamandraTA tracta valencià
#                                         i català com una sola entrada de
#                                         l'idioma ("Catalan (and Catalan-
#                                         Valencian variety)"), així que no
#                                         hi ha garantia que sàpia distingir
#                                         la direcció tot sol -- funciona
#                                         (83,54 BLEU) però per davall de
#                                         qwen/gemma.
#   2. --openai-mode traduccio_lexic  -> la MATEIXA plantilla, però afegint
#                                         el glossari dinàmic curt
#                                         [VOCABULARI: ...] (el mateix
#                                         format compacte, pensat per a no
#                                         ser repetit, que ja usen qwen/
#                                         gemma) en lloc de les regles
#                                         senceres -- per a comprovar si el
#                                         problema de 'regles' era la
#                                         mida/format del prompt, no que el
#                                         model siga incapaç de fer servir
#                                         cap pista.
#
# Si encara falla per memòria en bf16 amb 2 GPUs (pot passar: la memòria cau
# de vLLM també consumix VRAM), baixa GPU_MEMORY_UTILIZATION o
# VLLM_MAX_MODEL_LEN ahí baix abans de res més.
#
# Lanzarlo:
#   cd 03_seleccio_de_model/comparativa_salamandraTA_gemma
#   sbatch comparar_salamandraTA_gemma.sh

#SBATCH --job-name=compara-salamandraTA-gemma
#SBATCH --output=%j_compara.out
#SBATCH --error=%j_compara.err
#SBATCH --gres=gpu:5
#SBATCH --cpus-per-task=20
#SBATCH --mem=80G
#SBATCH --time=04:00:00
# #SBATCH --partition=gpu            # CAMBIA-ESTO si tu clúster lo exige
# #SBATCH --account=TU_CUENTA        # CAMBIA-ESTO si tu clúster lo exige

set -euo pipefail

# ── Modelos a comparar (edita aquí si quieres cambiar alguno) ───────────────
GEMMA_PETIT="gemma3:12b"                        # ~8 GB en Ollama (Q4) -- cabe holgado en 11 GB
SALAMANDRA_INSTRUCT="hdnh2006/salamandra-7b-instruct"  # ~4-5 GB en Ollama (Q4) -- de sobra
# ("hdnh2006/" es obligatorio: es el nombre real en el registro de Ollama,
# no está publicado como "salamandra-7b-instruct" a secas. Confirmado con los
# resultados ya guardados de la vez anterior: 03_seleccio_de_model/resultats/
# benchmark_Ollama_hdnh2006-salamandra-7b-instruct_*.json)
QWEN_REF="qwen2.5:14b"                          # ~9.2 GB en Ollama (Q4) -- ya confirmado que cabe en este nodo
SALAMANDRA_HF="BSC-LT/salamandraTA-7b-instruct"
# Entorno virtual dedicado para vLLM/bitsandbytes -- el Python del sistema
# en Debian/Ubuntu recientes es "externally managed" (PEP 668) y rechaza
# `pip install` directo. Nunca se usa --break-system-packages en un nodo
# compartido: tocaría el Python de TODOS los usuarios del nodo. Persistente
# en $HOME, igual que $OLLAMA_MODELS -- se crea una sola vez.
VENV_VLLM="${VENV_VLLM:-$HOME/venv_vllm}"
# Versión de vLLM FIJADA a propósito, no "la última": instalar sin fijar
# versión trajo vLLM 0.29.0, que exige torch 2.13.0+cu130 -- una build de
# PyTorch para CUDA 13.0, más nueva que el driver de este nodo (575.57.08,
# CUDA 12.9). vLLM 0.9.2 está confirmado compatible con PyTorch 2.6.0 +
# CUDA 12.4 (documentación oficial de vLLM), que sí cabe bajo un driver de
# 12.9 -- no es una suposición, es una combinación de versiones conocida.
VLLM_VERSION="0.9.2"
# vLLM 0.9.x necesita transformers <4.54.0 -- sin fijarlo, pip trae una
# version mas nueva que ya registra "aimv2" de forma nativa (soporte de un
# modelo de vision de Apple), chocando con el propio codigo de
# compatibilidad de vLLM 0.9.2 para versiones antiguas de transformers
# ("ValueError: 'aimv2' is already used by a Transformers config") --
# error real confirmado en un intento anterior, con arreglo documentado
# (issues publicos de vllm-project y otros proyectos que dependen de vLLM).
TRANSFORMERS_VERSION="<4.54.0"
# SalamandraTA en bf16 (~16 GB) NO cabe en UNA GPU de 11 GB, y ninguna
# cuantización a una sola GPU funciona en este hardware: bitsandbytes ya no
# lo soporta esta versión de vLLM, y fp8 exige compute capability >=80
# (Ampere+) pero este nodo es Turing, capability 75 -- error real
# confirmado ("Minimum capability: 80. Current capability: 75."), no algo
# que se arregle con más versiones. La solución es repartir el modelo
# SIN cuantizar entre 2 GPUs con --tensor-parallel-size 2 (cada una carga
# solo la mitad, ~8 GB). Con el doble de GPUs para los pesos, sobra memoria
# de sobra para la caché KV -- por eso GPU_MEMORY_UTILIZATION baja otra vez
# a un valor cómodo en vez del límite ajustado que hacía falta para fp8.
VLLM_TENSOR_PARALLEL="2"         # nº de GPUs entre las que se reparte SalamandraTA
GPU_MEMORY_UTILIZATION="0.85"    # fracción de los 11 GB (por GPU) que vLLM puede reservar; baja esto si aun así falla
VLLM_MAX_MODEL_LEN="4096"        # el prompt de --openai-mode regles (reglas dialectales + glosario dinámico)
# ocupa ~2200 tokens él solo -- con 1024 (valor anterior, pensado para cuando
# hacía falta ahorrar memoria por la cuantización) TODAS las peticiones de
# ese modo fallaban con "400 Bad Request: This model's maximum context
# length is 1024 tokens. However, you requested 2373 tokens" -- error real
# confirmado, no hipotético. Con 2 GPUs y sin cuantizar sobra memoria de
# caché KV de sobra para 4096 (comprobado con los números reales del log:
# a 1024 tokens/petición había margen para 23x más peticiones concurrentes
# de las que --max-num-seqs pide, así que subir a 4096 con el mismo
# --max-num-seqs sigue cabiendo sin tocar GPU_MEMORY_UTILIZATION).
VLLM_MAX_NUM_SEQS="4"            # el benchmark traduce de una en una, no necesita reservar para muchas secuencias a la vez

# IMPORTANT: SLURM copia este script a /var/spool/slurmd/jobXXXXX/ abans
# d'executar-lo -- ${BASH_SOURCE[0]} apuntaria ahí, no al projecte real.
# $SLURM_SUBMIT_DIR sí és fiable (ve resolt d'una execució anterior d'este
# mateix bug a generar_corpus_paralelo.sh).
if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    SCRIPT_DIR="$SLURM_SUBMIT_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
EVALUA_DIR="$(dirname "$SCRIPT_DIR")"           # 03_seleccio_de_model/
BENCHMARK="$EVALUA_DIR/benchmark_corpus.json"
LOGS_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOGS_DIR"

# El aislamiento de GPU por cgroups de SLURM no está activo en "abaco"
# (confirmado antes con generar_corpus_paralelo.sh) -- se restringe a mano
# a las 5 GPUs físicas 0-4 (0,1,3 para Ollama; 2+4 para SalamandraTA en
# vLLM con tensor-parallel), y se desactiva Vulkan en Ollama (bug conocido:
# github.com/ollama/ollama/issues/16508 -- Vulkan no respeta
# CUDA_VISIBLE_DEVICES) para que cada instancia se quede en su GPU.
export CUDA_VISIBLE_DEVICES="0,1,2,3,4"
echo "Restringiendo el job a las GPUs físicas: $CUDA_VISIBLE_DEVICES"

export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/ollama_models}"
mkdir -p "$OLLAMA_MODELS"

# Dos llistes de PIDs separades a propòsit: els SERVIDORS (ollama serve x3 +
# vllm x1) no acaben mai sols -- cal matar-los explícitament a la neteja. Els
# BENCHMARKS (evalua_models.py) sí acaben sols -- són els únics als quals
# esperem amb `wait` al final (esperar als servidors seria esperar per sempre).
PIDS_SERVIDORS=()
PIDS_BENCHMARK=()
limpiar() {
    echo "Deteniendo procesos..."
    for pid in "${PIDS_BENCHMARK[@]:-}"; do kill "$pid" 2>/dev/null || true; done
    for pid in "${PIDS_SERVIDORS[@]:-}"; do kill "$pid" 2>/dev/null || true; done
}
trap limpiar EXIT

# ── GPU 0/1/3: instancias de Ollama para gemma y qwen ───────────────────────
echo "[GPU0] Arrancando Ollama para $GEMMA_PETIT (puerto 11434)..."
CUDA_VISIBLE_DEVICES=0 OLLAMA_SCHED_SPREAD=false OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 \
    OLLAMA_HOST="127.0.0.1:11434" ollama serve > "$LOGS_DIR/ollama_gpu0.log" 2>&1 &
PIDS_SERVIDORS+=($!)

echo "[GPU1] Arrancando Ollama para $SALAMANDRA_INSTRUCT (puerto 11435)..."
CUDA_VISIBLE_DEVICES=1 OLLAMA_SCHED_SPREAD=false OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 \
    OLLAMA_HOST="127.0.0.1:11435" ollama serve > "$LOGS_DIR/ollama_gpu1.log" 2>&1 &
PIDS_SERVIDORS+=($!)

echo "[GPU3] Arrancando Ollama para $QWEN_REF (referencia, puerto 11436)..."
CUDA_VISIBLE_DEVICES=3 OLLAMA_SCHED_SPREAD=false OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 \
    OLLAMA_HOST="127.0.0.1:11436" ollama serve > "$LOGS_DIR/ollama_gpu3.log" 2>&1 &
PIDS_SERVIDORS+=($!)

echo "Esperando a que las 3 instancias de Ollama respondan..."
for PUERTO in 11434 11435 11436; do
    for _ in $(seq 1 30); do
        curl -s "http://127.0.0.1:${PUERTO}/api/tags" >/dev/null 2>&1 && break
        sleep 2
    done
done

echo "Descargando modelos de Ollama en paralelo (si no estaban ya en $OLLAMA_MODELS)..."
OLLAMA_HOST="127.0.0.1:11434" ollama pull "$GEMMA_PETIT" > "$LOGS_DIR/pull_gemma_petit.log" 2>&1 &
pid_pull_gemma=$!
OLLAMA_HOST="127.0.0.1:11435" ollama pull "$SALAMANDRA_INSTRUCT" > "$LOGS_DIR/pull_salamandra_instruct.log" 2>&1 &
pid_pull_salamandra=$!
OLLAMA_HOST="127.0.0.1:11436" ollama pull "$QWEN_REF" > "$LOGS_DIR/pull_qwen.log" 2>&1 &
pid_pull_qwen=$!

fallo_pull=0
wait "$pid_pull_gemma" || { echo "AVISO: falló la descarga de $GEMMA_PETIT (ver $LOGS_DIR/pull_gemma_petit.log)"; fallo_pull=1; }
wait "$pid_pull_salamandra" || { echo "AVISO: falló la descarga de $SALAMANDRA_INSTRUCT (ver $LOGS_DIR/pull_salamandra_instruct.log)"; fallo_pull=1; }
wait "$pid_pull_qwen" || { echo "AVISO: falló la descarga de $QWEN_REF (ver $LOGS_DIR/pull_qwen.log)"; fallo_pull=1; }
if [ "$fallo_pull" -ne 0 ]; then
    echo "Alguna descarga de Ollama falló -- revisa los logs de arriba antes de seguir."
fi
echo "Descargas de Ollama terminadas."

# ── GPU 2+4: SalamandraTA con vLLM (puerto 8000), fp16 en 2 GPUs ────────────
# GPU real confirmada: NVIDIA GeForce RTX 2080 Ti (Turing, compute
# capability 7.5). Sin cuantizar, el modelo pesa ~16 GB -- no cabe en UNA
# GPU de 11 GB. Se probaron tres cosas para que cupiera/funcionara en esta
# GPU en concreto, y las dos primeras fallaron por motivos reales:
#   - bitsandbytes: esta versión de vLLM ya no lo soporta como método
#     ("Unknown quantization method: bitsandbytes").
#   - fp8: SÍ soportado por vLLM, pero exige compute capability >=80
#     (Ampere+); Turing es capability 75 -- error real confirmado
#     ("Minimum capability: 80. Current capability: 75."), límite de
#     hardware, no de configuración.
#   - bfloat16 (el --dtype por defecto de vLLM): TAMPOCO lo soporta Turing
#     en cómputo (solo Ampere+) -- error real confirmado ("Bfloat16 is
#     only supported on GPUs with compute capability of at least 8.0").
# La solución real: --dtype float16 (Turing sí tiene tensor cores de fp16)
# SIN cuantizar, repartido entre 2 GPUs con --tensor-parallel-size 2 (fp16
# ocupa lo mismo que bf16, 2 bytes/parámetro -- sigue sin caber en 1 sola
# GPU de 11 GB, cada una carga solo la mitad, ~8 GB). Por eso este bloque
# usa 2 GPUs (2 y 4) en vez de 1, y el job entero pide 5 GPUs en vez de 4
# (cabecera del fichero).
echo "[GPU2+4] Comprobando el entorno virtual para vLLM en $VENV_VLLM (versión $VLLM_VERSION)..."
if [ ! -x "$VENV_VLLM/bin/python" ]; then
    echo "No existe -- creándolo (python3 -m venv)..."
    python3 -m venv "$VENV_VLLM"
fi

# Comprueba la VERSIÓN concreta de vllm Y que transformers respeta el
# límite <4.54.0 -- si el venv ya tiene otra combinación (p.ej. de un
# intento anterior sin fijar versión, o con vllm ya fijado pero
# transformers suelto), hay que reinstalar encima. No basta con "¿está
# instalado?": esto ya ha fallado dos veces por versiones sueltas.
if ! "$VENV_VLLM/bin/python" -c "
import vllm, transformers
from packaging.version import Version
assert vllm.__version__ == '$VLLM_VERSION'
assert Version(transformers.__version__) < Version('4.54.0')
" >/dev/null 2>&1; then
    echo "vLLM $VLLM_VERSION + transformers$TRANSFORMERS_VERSION no están instalados tal cual en el entorno virtual. Instalando..."
    echo "Puede tardar varios minutos. Si este nodo no tiene salida a internet, instálalo antes desde el nodo de acceso:"
    echo "  $VENV_VLLM/bin/pip install \"vllm==$VLLM_VERSION\" \"transformers$TRANSFORMERS_VERSION\" --extra-index-url https://download.pytorch.org/whl/cu124"
    "$VENV_VLLM/bin/pip" install -q --upgrade pip
    "$VENV_VLLM/bin/pip" install -q "vllm==$VLLM_VERSION" "transformers$TRANSFORMERS_VERSION" --extra-index-url https://download.pytorch.org/whl/cu124
fi
"$VENV_VLLM/bin/python" -c "
import torch, transformers
print('  torch', torch.__version__, '/ CUDA', torch.version.cuda)
print('  transformers', transformers.__version__)
"

# Descarga el modelo COMO PASO APARTE, no dentro del arranque de vLLM --
# igual que 'ollama pull' antes de 'ollama serve'. Si no, la descarga
# (~15 GB, la 1a vez) pasa perezosamente dentro de "Starting to load
# model..." y cuenta contra el tiempo de espera de más abajo -- con la
# descarga a HF sin autenticar (más lenta, avisa el propio log) puede
# tardar más de lo que se esperaba, y el script se rendía pensando que
# vLLM no arrancaba cuando en realidad solo estaba descargando.
echo "[GPU2+4] Descargando $SALAMANDRA_HF de HuggingFace (si no está ya en caché)..."
"$VENV_VLLM/bin/python" -c "
from huggingface_hub import snapshot_download
snapshot_download('$SALAMANDRA_HF')
print('Descarga completa (o ya estaba en caché).')
" 2>&1 | tail -5

echo "[GPU2+4] Arrancando vLLM para $SALAMANDRA_HF en fp16 (Turing no soporta bf16), repartido en $VLLM_TENSOR_PARALLEL GPUs (puerto 8000)..."
CUDA_VISIBLE_DEVICES=2,4 "$VENV_VLLM/bin/python" -m vllm.entrypoints.openai.api_server \
    --model "$SALAMANDRA_HF" \
    --dtype float16 \
    --tensor-parallel-size "$VLLM_TENSOR_PARALLEL" \
    --max-model-len "$VLLM_MAX_MODEL_LEN" \
    --max-num-seqs "$VLLM_MAX_NUM_SEQS" \
    --enforce-eager \
    --port 8000 \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
    > "$LOGS_DIR/vllm_gpu2.log" 2>&1 &
PIDS_SERVIDORS+=($!)

echo "Esperando a que vLLM cargue el modelo (ya descargado; repartirlo en 2 GPUs y con custom allreduce desactivado -- vore log -- puede tardar unos minutos)..."
VLLM_LISTO=0
for _ in $(seq 1 225); do
    if curl -s "http://127.0.0.1:8000/v1/models" >/dev/null 2>&1; then
        VLLM_LISTO=1
        break
    fi
    sleep 4
done
if [ "$VLLM_LISTO" -eq 0 ]; then
    echo "AVISO: vLLM no respondió a tiempo. Revisa $LOGS_DIR/vllm_gpu2.log."
    echo "  Causas más probables con bf16 repartido en 2 GPUs de 11 GB:"
    echo "  - Aun así falta VRAM (poco probable con 2 GPUs, pero por si acaso):"
    echo "    baja GPU_MEMORY_UTILIZATION o VLLM_MAX_MODEL_LEN."
    echo "  - Las 2 GPUs (2 y 4) no están realmente libres a la vez -- revisa"
    echo "    'nvidia-smi' de este mismo log más abajo."
    echo "  - Fallo de comunicación entre GPUs (NCCL) al repartir el modelo --"
    echo "    mira si el log menciona 'NCCL' explícitamente."
fi

echo ""
echo "Comprovació nvidia-smi (activitat esperada a GPU 0-4):"
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv || true
echo ""

# ── Lanza los benchmarks ────────────────────────────────────────────────────
cd "$EVALUA_DIR"
echo "Lanzando los benchmarks (60 frases cada uno)..."

python3 evalua_models.py --model ollama --ollama-model "$GEMMA_PETIT" \
    --ollama-url "http://127.0.0.1:11434" --ollama-timeout 300 \
    --benchmark "$BENCHMARK" > "$LOGS_DIR/resultado_gemma_petit.log" 2>&1 &
PIDS_BENCHMARK+=($!)

python3 evalua_models.py --model ollama --ollama-model "$SALAMANDRA_INSTRUCT" \
    --ollama-url "http://127.0.0.1:11435" --ollama-timeout 300 \
    --benchmark "$BENCHMARK" > "$LOGS_DIR/resultado_salamandra_instruct.log" 2>&1 &
PIDS_BENCHMARK+=($!)

python3 evalua_models.py --model ollama --ollama-model "$QWEN_REF" \
    --ollama-url "http://127.0.0.1:11436" --ollama-timeout 300 \
    --benchmark "$BENCHMARK" > "$LOGS_DIR/resultado_qwen_referencia.log" 2>&1 &
PIDS_BENCHMARK+=($!)

if [ "$VLLM_LISTO" -eq 1 ]; then
    # SalamandraTA: dos maneras de usarlo, una detrás de otra contra el
    # mismo servidor vLLM (no hace falta otra GPU para la 2a pasada). Se
    # dejan en primer plano para no perder el "wait" de los otros tres.
    #
    # 'regles' YA NO SE PRUEBA -- confirmado roto (0.13-1.75 BLEU, 0/60):
    # en vez de aplicar las reglas del system prompt largo (~2200 tokens),
    # el modelo repite fragmentos literales de las propias instrucciones
    # como si fueran la traducción. No es un modelo instructor de propósito
    # general, así que un system prompt con 10 categorías de reglas no es
    # su formato. En su lugar se prueba 'traduccio_lexic': la MISMA
    # plantilla nativa de traducción que sí funciona (83,54 BLEU en
    # 'traduccio'), pero añadiéndole el glosario dinámico corto
    # [VOCABULARI: ...] -- el mismo formato compacto, pensado para no ser
    # repetido, que ya usan qwen/gemma -- en vez de las reglas enteras.
    echo "Probando SalamandraTA en modo 'traduccio' (plantilla oficial del modelo, sin pistas)..."
    python3 evalua_models.py --model openai --openai-model "$SALAMANDRA_HF" \
        --openai-url "http://127.0.0.1:8000/v1" --openai-mode traduccio --openai-timeout 300 \
        --benchmark "$BENCHMARK" > "$LOGS_DIR/resultado_salamandraTA_traduccio.log" 2>&1 || true

    echo "Probando SalamandraTA en modo 'traduccio_lexic' (plantilla oficial + glosario corto)..."
    python3 evalua_models.py --model openai --openai-model "$SALAMANDRA_HF" \
        --openai-url "http://127.0.0.1:8000/v1" --openai-mode traduccio_lexic --openai-timeout 300 \
        --benchmark "$BENCHMARK" > "$LOGS_DIR/resultado_salamandraTA_traduccio_lexic.log" 2>&1 || true
else
    echo "Se salta SalamandraTA: vLLM no arrancó (ver aviso arriba)."
fi

echo "Esperando a que terminen gemma/qwen..."
estado=0
for pid in "${PIDS_BENCHMARK[@]}"; do
    wait "$pid" || estado=1
done

if [ "$estado" -ne 0 ]; then
    echo "AVISO: algún benchmark de Ollama terminó con error — revisa $LOGS_DIR/resultado_*.log."
fi

echo "Generando el informe comparativo final..."
python3 "$SCRIPT_DIR/combina_resultats.py" \
    --resultats-dir "$EVALUA_DIR/resultats" \
    --minuts 240 \
    --salida "$SCRIPT_DIR/informe_comparatiu.txt" || true

if [ -f "$SCRIPT_DIR/informe_comparatiu.txt" ]; then
    echo ""
    cat "$SCRIPT_DIR/informe_comparatiu.txt"
fi

echo ""
echo "Hecho. Resultados individuales en $EVALUA_DIR/resultats/, logs en $LOGS_DIR/,"
echo "informe combinado en $SCRIPT_DIR/informe_comparatiu.txt"
