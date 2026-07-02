import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

payload = {
    "model": "llama3.2:1b",
    "prompt": "Türkçe kısa cevap ver: Merhaba, çalışıyor musun?",
    "stream": False,
    "options": {
        "temperature": 0.2
    }
}

try:
    response = requests.post(OLLAMA_URL, json=payload, timeout=60)

    print("STATUS:", response.status_code)

    if response.status_code != 200:
        print("ERROR:")
        print(response.text)
    else:
        data = response.json()
        print("OLLAMA ANSWER:")
        print(data.get("response", ""))

except Exception as e:
    print("CONNECTION ERROR:")
    print(e)