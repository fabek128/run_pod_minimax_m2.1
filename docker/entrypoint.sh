#!/usr/bin/env bash
set -euo pipefail

: "${MODEL_PATH:=/models/model.gguf}"
: "${MODEL_URL:=}"
: "${HOST:=0.0.0.0}"
: "${PORT:=8000}"

if [[ ! -f "$MODEL_PATH" ]]; then
  if [[ -n "$MODEL_URL" ]]; then
    echo "Downloading model to $MODEL_PATH..."
    mkdir -p "$(dirname "$MODEL_PATH")"
    if [[ -n "${HF_TOKEN:-}" ]]; then
      curl -L -H "Authorization: Bearer $HF_TOKEN" -o "$MODEL_PATH" "$MODEL_URL"
    else
      curl -L -o "$MODEL_PATH" "$MODEL_URL"
    fi
  else
    echo "MODEL_PATH not found and MODEL_URL is not set."
    exit 1
  fi
fi

exec /serve_llama.sh
