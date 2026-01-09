#!/usr/bin/env bash
set -euo pipefail

: "${MODEL_PATH:=/models/model.gguf}"
: "${HOST:=0.0.0.0}"
: "${PORT:=8000}"
: "${LLAMA_CTX:=8192}"

if [[ -z "${LLAMA_THREADS:-}" ]]; then
  if command -v nproc >/dev/null 2>&1; then
    LLAMA_THREADS="$(nproc)"
  else
    LLAMA_THREADS="$(getconf _NPROCESSORS_ONLN)"
  fi
fi

BIN=""
if [[ -x /opt/llama.cpp/build/bin/llama-server ]]; then
  BIN=/opt/llama.cpp/build/bin/llama-server
elif [[ -x /opt/llama.cpp/build/bin/server ]]; then
  BIN=/opt/llama.cpp/build/bin/server
else
  echo "llama.cpp server binary not found."
  exit 1
fi

ARGS=(
  --model "$MODEL_PATH"
  --host "$HOST"
  --port "$PORT"
  --ctx-size "$LLAMA_CTX"
  --threads "$LLAMA_THREADS"
)

if [[ "${LLAMA_MLOCK:-0}" == "1" ]]; then
  ARGS+=(--mlock)
fi

if [[ "${LLAMA_NO_MMAP:-0}" == "1" ]]; then
  ARGS+=(--no-mmap)
fi

if [[ -n "${LLAMA_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  EXTRA_ARGS=($LLAMA_EXTRA_ARGS)
  ARGS+=("${EXTRA_ARGS[@]}")
fi

exec "$BIN" "${ARGS[@]}"
