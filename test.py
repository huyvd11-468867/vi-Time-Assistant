import requests

url = "http://127.0.0.1:8000/chat"

# 🔑 Put your API key here (TEMPORARY, not for production)
api_key = ""

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