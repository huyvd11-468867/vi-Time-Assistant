import requests
from datetime import date

BACKEND = "http://127.0.0.1:8000"

payload = {
    "user_id": "u1",
    "entries": [
        {"site": "facebook.com", "duration": 600, "log_date": date.today().isoformat()},
        {"site": "youtube.com", "duration": 300, "log_date": date.today().isoformat()},
    ]
}

res = requests.post(f"{BACKEND}/log_usage_bulk", json=payload)
print("Status:", res.status_code, res.text)
