#!/usr/bin/env bash
set -euo pipefail

: "${MODEL_ID:=MiniMaxAI/MiniMax-M2.1}"
: "${SERVED_MODEL_NAME:=$MODEL_ID}"
: "${TP_SIZE:=1}"
: "${HOST:=0.0.0.0}"
: "${PORT:=8000}"
: "${GPU_MEMORY_UTILIZATION:=0.90}"
: "${MAX_MODEL_LEN:=32768}"

ARGS=(
  --model "$MODEL_ID"
  --served-model-name "$SERVED_MODEL_NAME"
  --trust-remote-code
  --tensor-parallel-size "$TP_SIZE"
  --enable-auto-tool-choice
  --tool-call-parser minimax_m2
  --reasoning-parser minimax_m2_append_think
  --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"
  --max-model-len "$MAX_MODEL_LEN"
  --host "$HOST"
  --port "$PORT"
)

if [[ -n "${VLLM_API_KEY:-}" ]]; then
  ARGS+=(--api-key "$VLLM_API_KEY")
fi

if [[ -n "${DTYPE:-}" ]]; then
  ARGS+=(--dtype "$DTYPE")
fi

python3 -m vllm.entrypoints.openai.api_server "${ARGS[@]}"
