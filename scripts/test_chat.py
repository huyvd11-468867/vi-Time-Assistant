import requests

BACKEND = "http://127.0.0.1:8000"
API_KEY = "sk-REPLACE_ME"  # put your key here (demo only)

payload = {
    "user_id": "u1",
    "question": "Hôm nay tôi dùng Facebook bao lâu?",
    "usage": {
        "facebook.com": 3600,
        "youtube.com": 1200,
        "news.ycombinator.com": 300
    }
}

headers = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY
}

res = requests.post(f"{BACKEND}/chat", json=payload, headers=headers)
print("Status:", res.status_code)
print("Text:", res.text)
