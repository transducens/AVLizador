#!/bin/bash
# entrena_metrica.sh -- Entrena la mètrica sense referència cat->val
# (ReferencelessRegression d'unbabel-comet, xlm-roberta-large, fp16) en una
# GPU d'Abaco (RTX 2080 Ti, 11 GB).
#
# Dades: dades/metrica_sense_referencia/ (gitignorat; es generen en local amb
# genera_corpus.py i es pugen amb scp, vore README.es.md).
#
# Llançar-ho (des de ~/scrapeo/AVLizador/pipeline/03_seleccio_de_model/metrica_sense_referencia):
#   PROVA=1 sbatch entrena_metrica.sh                 # prova: 200 lots, encoder descongelat (pic de memòria)
#   sbatch entrena_metrica.sh                         # model final (corpus sense reserva)
#   VARIANT=reserva sbatch entrena_metrica.sh         # model per al test de circularitat
#   LOT=4 sbatch entrena_metrica.sh                   # lot 4 x acumulació 8 si el de 8 no cap
# Eixida: models/<variant>/lightning_logs/version_N/{hparams.yaml,checkpoints/*.ckpt,metrics.csv}
# Logs: logs/%j_metrica.out (inclou l'ús de memòria de la GPU cada minut).
#
# Entorn: el venv de XCOMET (~/venvs/comet: torch cu128 + unbabel-comet; vore
# ../comet/comet.sh), que ja existix en Abaco.

#SBATCH --job-name=metrica_qe
#SBATCH --output=logs/%j_metrica.out
#SBATCH --error=logs/%j_metrica.err
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=24:00:00

set -euo pipefail

VARIANT="${VARIANT:-complet}"
SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
CONFIG="$SCRIPT_DIR/configs/referenceless_${VARIANT}.yaml"
echo "Repo: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
echo "Variant: $VARIANT  Config: $CONFIG  Prova: ${PROVA:-0}"
[[ -f "$CONFIG" ]] || { echo "ERROR: no existix $CONFIG (VARIANT=complet|reserva)" >&2; exit 1; }
if [[ -z "${CUDA_VISIBLE_DEVICES:-}" ]]; then
    echo "ERROR: SLURM no ha assignat cap GPU." >&2
    exit 1
fi
echo "GPU: $CUDA_VISIBLE_DEVICES"
nvidia-smi -i "$CUDA_VISIBLE_DEVICES" --query-gpu=name,memory.total --format=csv,noheader || true

DADES="$ARREL_REPO/dades/metrica_sense_referencia"
[[ "$VARIANT" == "complet" ]] && DADES="$DADES/complet"
for f in train.csv val.csv; do
    [[ -f "$DADES/$f" ]] || { echo "ERROR: falta $DADES/$f (pujar-lo amb scp; vore README.es.md)" >&2; exit 1; }
done
wc -l "$DADES/train.csv" "$DADES/val.csv"

export PYTHONIOENCODING=utf-8
export TOKENIZERS_PARALLELISM=false
export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
VENV="${VENV:-$HOME/venvs/comet}"
[[ -x "$VENV/bin/comet-train" ]] || { echo "ERROR: no hi ha $VENV/bin/comet-train (crear el venv amb ../comet/comet.sh)" >&2; exit 1; }
"$VENV/bin/python" -c "import torch, comet, pytorch_lightning as pl; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), '| comet', comet.__version__, '| lightning', pl.__version__)"
"$VENV/bin/python" -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)" \
    || { echo "ERROR: torch no veu la GPU." >&2; exit 1; }

cd "$ARREL_REPO"
mkdir -p "$SCRIPT_DIR/logs"

# Variacions de la configuració, en un YAML temporal en logs/:
# - PROVA=1: 200 lots d'entrenament i 50 de validació, una època, i l'encoder
#   descongelat des del principi (nr_frozen_epochs 0) per a vore el pic de
#   memòria de veres en pocs minuts.
# - LOT=4: lot de 4 amb acumulació 8 (el lot efectiu continua sent 32), si
#   el de 8 no cap en la GPU.
if [[ "${PROVA:-0}" == "1" || -n "${LOT:-}" ]]; then
    CONFIG_TMP="$SCRIPT_DIR/logs/${SLURM_JOB_ID:-local}_${VARIANT}.yaml"
    PROVA="${PROVA:-0}" LOT="${LOT:-}" "$VENV/bin/python" - "$CONFIG" "$CONFIG_TMP" <<'EOF'
import os, sys, yaml
cfg = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
m = cfg["referenceless_regression_metric"]["init_args"]
t = cfg["trainer"]["init_args"]
if os.environ["LOT"]:
    lot = int(os.environ["LOT"])
    efectiu = m["batch_size"] * t["accumulate_grad_batches"]
    assert efectiu % lot == 0, f"el lot efectiu {efectiu} no és múltiple de {lot}"
    m["batch_size"], t["accumulate_grad_batches"] = lot, efectiu // lot
if os.environ["PROVA"] == "1":
    m["nr_frozen_epochs"] = 0.0
    t.update(limit_train_batches=200, limit_val_batches=50, max_epochs=1, val_check_interval=1.0)
    t["default_root_dir"] = t["default_root_dir"] + "_prova"
print(f"Lot {m['batch_size']} x acumulació {t['accumulate_grad_batches']}")
yaml.safe_dump(cfg, open(sys.argv[2], "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)
EOF
    CONFIG="$CONFIG_TMP"
fi

# Memòria de NOMÉS la nostra GPU cada minut (sense -i, nvidia-smi les
# llista totes i el màxim podia ser d'un altre treball). El pic exacte del
# procés l'escriu entrena_comet.py al final.
nvidia-smi -i "$CUDA_VISIBLE_DEVICES" --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 60     > "$SCRIPT_DIR/logs/${SLURM_JOB_ID:-local}_gpu.csv" &
MONITOR_GPU=$!
trap 'kill $MONITOR_GPU 2>/dev/null || true' EXIT

# `comet-train` peta en un print amb el lightning d'Abaco: vore entrena_comet.py.
"$VENV/bin/python" "$SCRIPT_DIR/entrena_comet.py" --cfg "$CONFIG" --seed_everything 20261118

echo "Màxim de memòria de la GPU segons nvidia-smi, cada minut (MiB): $(cut -d, -f2 "$SCRIPT_DIR/logs/${SLURM_JOB_ID:-local}_gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)"
echo "Checkpoints:"
find "$SCRIPT_DIR/models" -name "*.ckpt" -newer "$CONFIG" -printf "%TY-%Tm-%Td %TH:%TM  %p\n" 2>/dev/null | sort || true
