import os
from pathlib import Path

from openai import OpenAI


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key and key not in os.environ:
            os.environ[key] = value


repo_root = Path(__file__).resolve().parents[2]
load_env(repo_root / ".env")

base_url = os.getenv("LLAMA_BASE_URL", "http://localhost:8000/v1")
api_key = os.getenv("LLAMA_API_KEY", "local-key")

client = OpenAI(
    base_url=base_url,
    api_key=api_key,
)

model = os.getenv("SERVED_MODEL_NAME")
if not model:
    try:
        models = client.models.list()
        if models.data:
            model = models.data[0].id
    except Exception:
        model = "local-gguf"

resp = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "Explain CPU inference in 2 sentences."},
    ],
    temperature=0.2,
)

print(resp.choices[0].message.content)
