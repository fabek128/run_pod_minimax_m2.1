# minimax-runpod

Serve MiniMaxAI/MiniMax-M2.1 on RunPod using vLLM nightly and an OpenAI-compatible API.

## Repo layout
- docker/ Docker image and entrypoint scripts
- configs/ Example env file (no secrets)
- client/python/ Windows client example
- ui/ Optional Open WebUI compose
- .github/workflows/ GHCR build and push

## Build and publish (GitHub Actions)
Push to main to publish:
- ghcr.io/<OWNER>/<REPO>:latest
- ghcr.io/<OWNER>/<REPO>:sha-<shortsha>

Create a release tag to publish vX.Y.Z:
git tag v0.1.0
git push origin v0.1.0

Verify image exists:
docker pull ghcr.io/<OWNER>/<REPO>:v0.1.0

## Local client (Windows)
Copy the example env file and run:
copy client\\python\\.env.example client\\python\\.env
powershell -ExecutionPolicy Bypass -File client\\python\\run.ps1

## Open WebUI env example
Copy and edit as needed:
copy ui\\openwebui.env.example ui\\openwebui.env
docker compose --env-file ui\\openwebui.env -f ui\\openwebui-compose.yml up -d

## RunPod env (minimum)
MODEL_ID=MiniMaxAI/MiniMax-M2.1
TP_SIZE=<num_gpus>
HF_TOKEN=<your_token>
HF_HOME=/workspace/hf
HUGGINGFACE_HUB_CACHE=/workspace/hf/hub
TRANSFORMERS_CACHE=/workspace/hf/transformers

## Security
Do not commit secrets. Keep HF_TOKEN only in RunPod env vars. Use VLLM_API_KEY if the endpoint is public.
