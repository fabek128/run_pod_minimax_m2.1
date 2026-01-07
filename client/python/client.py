import os
from openai import OpenAI

base_url = os.getenv("VLLM_BASE_URL", "https://YOUR-RUNPOD-ENDPOINT/v1")
api_key = os.getenv("VLLM_API_KEY", "local-key")
model = os.getenv("MODEL_ID", "MiniMaxAI/MiniMax-M2.1")

client = OpenAI(
    base_url=base_url,
    api_key=api_key,
)

resp = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "Give me a 2-sentence summary of vLLM."},
    ],
    temperature=0.2,
)

print(resp.choices[0].message.content)
