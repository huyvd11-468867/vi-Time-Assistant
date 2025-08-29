import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Any

# Anchor data.json to the backend folder (not the cwd)
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data.json"

# In-process lock (good enough for single-process uvicorn)
from threading import RLock
_LOCK = RLock()


def _atomic_save(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON atomically to avoid partial writes on crash."""
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def load_data() -> Dict[str, Any]:
    with _LOCK:
        if not DATA_FILE.exists():
            return {"users": {}}
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)


def save_data(data: Dict[str, Any]) -> None:
    with _LOCK:
        _atomic_save(DATA_FILE, data)
        print(f"[DEBUG] Saved JSON to {DATA_FILE}")


def ensure_user(data: Dict[str, Any], user_id: str) -> None:
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "usage_logs": [],   # list[ {site, duration_seconds, log_date} ]
            "chat_history": []  # list[ {question, answer, asked_at} ]
        }


def add_usage(user_id: str, site: str, duration_seconds: int, log_date_iso: str | None = None) -> None:
    if log_date_iso is None:
        log_date_iso = date.today().isoformat()
    data = load_data()
    ensure_user(data, user_id)
    data["users"][user_id]["usage_logs"].append({
        "site": site,
        "duration_seconds": int(duration_seconds),
        "log_date": log_date_iso
    })
    save_data(data)


def add_usage_bulk(user_id: str, entries: List[Dict[str, Any]]) -> None:
    data = load_data()
    ensure_user(data, user_id)
    # normalize
    today_iso = date.today().isoformat()
    for e in entries:
        site = e.get("site")
        duration = int(e.get("duration", 0))
        d = e.get("log_date") or today_iso
        if site and duration > 0:
            data["users"][user_id]["usage_logs"].append({
                "site": site,
                "duration_seconds": duration,
                "log_date": d
            })
    save_data(data)


def add_chat(user_id: str, question: str, answer: str) -> None:
    data = load_data()
    ensure_user(data, user_id)
    data["users"][user_id]["chat_history"].append({
        "question": question,
        "answer": answer,
        "asked_at": datetime.now().isoformat(timespec="seconds")
    })
    save_data(data)


def get_user(user_id: str) -> Dict[str, Any]:
    data = load_data()
    return data["users"].get(user_id, {"usage_logs": [], "chat_history": []})


def aggregate_for_date(user_id: str, target_date_iso: str) -> Dict[str, int]:
    """Return {domain: total_seconds} for a specific date."""
    u = get_user(user_id)
    agg: Dict[str, int] = {}
    for row in u["usage_logs"]:
        if row.get("log_date") == target_date_iso:
            site = row.get("site")
            dur = int(row.get("duration_seconds", 0))
            agg[site] = agg.get(site, 0) + dur
    return agg


def aggregate_last_n_days(user_id: str, n: int) -> Dict[str, int]:
    """Return {domain: total_seconds} for last n days (inclusive of today)."""
    u = get_user(user_id)
    agg: Dict[str, int] = {}
    cutoff = date.today().toordinal() - (n - 1)
    for row in u["usage_logs"]:
        try:
            d = date.fromisoformat(row.get("log_date", "1970-01-01")).toordinal()
        except Exception:
            continue
        if d >= cutoff:
            site = row.get("site")
            dur = int(row.get("duration_seconds", 0))
            agg[site] = agg.get(site, 0) + dur
    return agg


def reset_user(user_id: str) -> None:
    data = load_data()
    data["users"][user_id] = {"usage_logs": [], "chat_history": []}
    save_data(data)
