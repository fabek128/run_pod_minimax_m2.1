# CPU + RAM LLM inference on RunPod (llama.cpp)

This repo runs GGUF models on large CPU/RAM instances using `llama.cpp` and exposes an OpenAI-compatible API.

## Alternatives (CPU + RAM)
- llama.cpp + GGUF (recommended): best CPU performance, supports quantization, simple server, can fully load into RAM.
- llama-cpp-python: same backend with Python bindings; good for experiments, slightly more overhead.
- Transformers + IPEX/OpenVINO: best for Intel-heavy environments and batch workloads; more complex and slower for huge LLMs.
- vLLM CPU backend: experimental and usually not cost-effective for large models.

This project implements the first option because it is the most reliable and cost-effective on CPU.

## Quickstart
1) Copy `.env.example` to `.env` and fill: `RUNPOD_API_KEY`, `RUNPOD_IMAGE_NAME`, `RUNPOD_CPU_FLAVORS` (use the exact CPU flavor ID from RunPod), and a `MODEL_URL` (or pre-upload a GGUF to the volume and set `MODEL_PATH`).  
2) Build and push the image:
```powershell
docker build -t ghcr.io/<owner>/<repo>:latest -f docker/Dockerfile .
docker push ghcr.io/<owner>/<repo>:latest
```
3) Create (or recreate) the CPU pod:
```powershell
python scripts/runpod_manage.py --verbose
```
4) When the pod is ready, set `LLAMA_BASE_URL` in `.env` to the RunPod HTTP endpoint ending in `/v1`, then run the client:
```powershell
pip install -r client/python/requirements.txt
python client/python/client.py
```
5) Optional UI (ChatGPT-style):
```powershell
docker compose -f ui/openwebui-compose.yml up -d
```
Open http://localhost:3000 and set the model if prompted.

## Notes for large CPU/RAM instances
- Use GGUF quantized models (4-bit or 5-bit). Full-precision models are usually too slow or too large for CPU.
- If you want the model fully in RAM, set `LLAMA_NO_MMAP=1` and keep `LLAMA_MLOCK=1`. Make sure RAM is large enough.
- For a quick smoke test, start with a 7B GGUF model, then scale up.

## Files
- `docker/`: llama.cpp build + server entrypoint.
- `scripts/runpod_manage.py`: creates/recreates CPU pods via RunPod REST API.
- `configs/llama.env.example`: container-level settings.
- `client/python/`: OpenAI-style client example.
- `ui/openwebui-compose.yml`: optional local chat UI.
