import requests

url = "http://127.0.0.1:8000/chat"

# 🔑 Put your API key here (TEMPORARY, not for production)
api_key = "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"

payload = {
    "user_id": "u1",
    "question": "Hôm nay tôi dùng Facebook bao lâu?",
    "usage": {
        "facebook.com": 2222,
        "youtube.com": 1200
    }
}

headers = {"Content-Type": "application/json", "x-api-key": api_key}
res = requests.post(url, json=payload, headers=headers)
print(res.json())