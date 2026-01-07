#!/usr/bin/env bash
set -euo pipefail

: "${MODEL_ID:=MiniMaxAI/MiniMax-M2.1}"
: "${TP_SIZE:=1}"
: "${SERVED_MODEL_NAME:=$MODEL_ID}"
: "${HOST:=0.0.0.0}"
: "${PORT:=8000}"
: "${PERSIST_DIR:=/workspace}"

: "${HF_HOME:=$PERSIST_DIR/hf}"
: "${HUGGINGFACE_HUB_CACHE:=$HF_HOME/hub}"
: "${TRANSFORMERS_CACHE:=$HF_HOME/transformers}"
: "${VLLM_CACHE:=$PERSIST_DIR/vllm-cache}"

export HF_HOME HUGGINGFACE_HUB_CACHE TRANSFORMERS_CACHE VLLM_CACHE

mkdir -p "$HF_HOME" "$HUGGINGFACE_HUB_CACHE" "$TRANSFORMERS_CACHE" "$VLLM_CACHE"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "WARNING: HF_TOKEN is not set; model download may fail."
fi

if [[ "${WARMUP_DOWNLOAD:-0}" == "1" ]]; then
  echo "Warmup download enabled. Prefetching model..."
  python3 - <<'PY'
import os
from huggingface_hub import snapshot_download

model_id = os.environ.get("MODEL_ID")
token = os.environ.get("HF_TOKEN")
cache_dir = os.environ.get("HUGGINGFACE_HUB_CACHE")

snapshot_download(repo_id=model_id, token=token, cache_dir=cache_dir, local_files_only=False)
print("Warmup download complete.")
PY
fi

exec /serve_vllm.sh
