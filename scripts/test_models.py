import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
base_url = "https://openrouter.ai/api/v1/chat/completions"

models = [
    "stepfun/step-3.5-flash:free",
    "deepseek/deepseek-chat:free",
    "google/gemini-2.0-flash-exp:free",
]


def test_model(model_id):
    print(f"\nTesting {model_id}...")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Property Guardian Test",
        "Content-Type": "application/json",
    }
    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Say 'OK' if you see this."}],
        "max_tokens": 10,
    }
    try:
        response = requests.post(
            base_url, headers=headers, data=json.dumps(data), timeout=15
        )
        if response.status_status == 200:
            print(f"SUCCESS: {response.json()['choices'][0]['message']['content']}")
            return True
        else:
            print(f"FAILED ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


results = {}
for model in models:
    results[model] = test_model(model)

print("\nFinal Results:")
for model, success in results.items():
    print(f"{model}: {'✅ WORKING' if success else '❌ FAILING'}")
