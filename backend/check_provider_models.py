import os

import httpx
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv(
    "LLM_BASE_URL",
    "https://api.groq.com/openai/v1",
).strip().rstrip("/")

api_key = os.getenv("LLM_API_KEY", "").strip()

if not api_key:
    raise SystemExit(
        "LLM_API_KEY is missing. Check backend/.env."
    )

if base_url.endswith("/chat/completions"):
    raise SystemExit(
        "LLM_BASE_URL should end at /openai/v1, "
        "not /chat/completions."
    )

try:
    response = httpx.get(
        f"{base_url}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=20.0,
    )

    print("HTTP status:", response.status_code)

    if response.status_code != 200:
        print(
            "Could not list models. Check the base URL, "
            "credentials and provider response."
        )
        raise SystemExit(1)

    models = response.json().get("data", [])
    model_ids = sorted(
        model["id"]
        for model in models
        if isinstance(model, dict) and model.get("id")
    )

    print("\nModels returned by the provider:")
    for model_id in model_ids:
        print("-", model_id)

except httpx.RequestError as exc:
    raise SystemExit(
        f"Could not connect to the provider: {exc}"
    )