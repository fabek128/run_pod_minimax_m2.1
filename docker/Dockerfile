FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    ca-certificates curl git bash \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --upgrade pip \
    && python3 -m pip install --no-cache-dir --pre vllm \
       --extra-index-url https://wheels.vllm.ai/nightly \
    && python3 -m pip install --no-cache-dir huggingface_hub

WORKDIR /workspace

COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/serve_vllm.sh /serve_vllm.sh

RUN chmod +x /entrypoint.sh /serve_vllm.sh \
    && sed -i 's/\r$//' /entrypoint.sh /serve_vllm.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
