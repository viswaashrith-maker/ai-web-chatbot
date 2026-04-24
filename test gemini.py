import requests

API_KEY = "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"

url = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": "openai/gpt-3.5-turbo",
    "messages": [
        {"role": "user", "content": "Say hello in one sentence"}
    ]
}

response = requests.post(url, headers=headers, json=data)

print(response.json())