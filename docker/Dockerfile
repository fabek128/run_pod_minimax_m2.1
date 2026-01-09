FROM ubuntu:22.04

ARG LLAMA_CPP_REF=master

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git curl ca-certificates \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone https://github.com/ggerganov/llama.cpp \
    && cd llama.cpp \
    && git checkout "$LLAMA_CPP_REF" \
    && cmake -S . -B build -DLLAMA_SERVER=ON -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build -j

COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/serve_llama.sh /serve_llama.sh

RUN chmod +x /entrypoint.sh /serve_llama.sh \
    && sed -i 's/\r$//' /entrypoint.sh /serve_llama.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
