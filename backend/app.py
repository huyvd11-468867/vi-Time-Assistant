from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import date
from openai import OpenAI

from storage import (
    add_usage, add_usage_bulk, add_chat, get_user,
    aggregate_for_date, aggregate_last_n_days, reset_user, DATA_FILE
)

app = FastAPI(title="ViTimeAssistant Backend", version="1.0.0")

# CORS (allow extension + local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for local demo; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Schemas -----
class ChatRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    question: str = Field(..., description="User question in Vietnamese")
    usage: Dict[str, int] = Field(default_factory=dict, description="Optional {domain: seconds} to override today data")


class UsageRequest(BaseModel):
    user_id: str
    site: str
    duration: int
    log_date: Optional[str] = None  # ISO date "YYYY-MM-DD"


class BulkUsageEntry(BaseModel):
    site: str
    duration: int
    log_date: Optional[str] = None  # ISO date


class BulkUsageRequest(BaseModel):
    user_id: str
    entries: List[BulkUsageEntry]


# ----- Helpers -----
def _build_answer_short_expert(usage_map: Dict[str, int], question: str, client: OpenAI) -> str:
    # minutes, percent
    total = sum(usage_map.values())
    minutes_map = {k: v // 60 for k, v in usage_map.items()}
    fb_m = minutes_map.get("facebook.com", 0)
    yt_m = minutes_map.get("youtube.com", 0)
    total_m = total // 60 if total > 0 else 0

    system_prompt = (
        "Bạn là một chuyên gia phân tích thói quen sử dụng internet.\n"
        "- Trả lời ngắn gọn, súc tích, bằng tiếng Việt.\n"
        "- Nêu số liệu chính, phần trăm và 1–2 nhận xét quan trọng.\n"
        "- Đưa ra đúng một gợi ý ngắn gọn để cải thiện."
    )
    user_prompt = (
        f"Dữ liệu hôm nay:\n"
        f"- Facebook: {fb_m} phút\n"
        f"- YouTube: {yt_m} phút\n"
        f"- Tổng: {total_m} phút\n\n"
        f"Các nền tảng khác (phút): { {k: v for k, v in minutes_map.items() if k not in ['facebook.com','youtube.com']} }\n\n"
        f"Câu hỏi người dùng: {question}"
    )

    # Use Responses API (chat.completions also fine)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
    )
    return resp.choices[0].message.content.strip()


# ----- Routes -----
@app.get("/")
def root():
    return {"message": "ViTimeAssistant backend is running 🚀"}


@app.get("/debug/filepath")
def debug_filepath():
    return {"data_json_abs_path": str(DATA_FILE.resolve())}


@app.get("/user/{user_id}")
def get_user_data(user_id: str):
    return get_user(user_id)


@app.post("/log_usage")
def log_usage(req: UsageRequest):
    add_usage(req.user_id, req.site, req.duration, req.log_date)
    return {"status": "ok"}


@app.post("/log_usage_bulk")
def log_usage_bulk(req: BulkUsageRequest):
    # entries: [{site, duration, log_date?}, ...]
    add_usage_bulk(req.user_id, [e.dict() for e in req.entries])
    return {"status": "ok", "count": len(req.entries)}


@app.get("/today_summary/{user_id}")
def today_summary(user_id: str):
    today_iso = date.today().isoformat()
    agg = aggregate_for_date(user_id, today_iso)
    total = sum(agg.values())
    by_site = [
        {
            "site": k,
            "seconds": v,
            "minutes": v // 60,
            "share_pct": round(100 * v / total, 2) if total > 0 else 0.0,
        }
        for k, v in sorted(agg.items(), key=lambda kv: kv[1], reverse=True)
    ]
    return {"date": today_iso, "total_seconds": total, "by_site": by_site}


@app.get("/week_summary/{user_id}")
def week_summary(user_id: str):
    agg = aggregate_last_n_days(user_id, 7)
    total = sum(agg.values())
    by_site = [
        {
            "site": k,
            "seconds": v,
            "minutes": v // 60,
            "share_pct": round(100 * v / total, 2) if total > 0 else 0.0,
        }
        for k, v in sorted(agg.items(), key=lambda kv: kv[1], reverse=True)
    ]
    return {"days": 7, "total_seconds": total, "by_site": by_site}


@app.post("/chat")
def chat(req: ChatRequest, request: Request):
    try:
        # Prefer header; fallback to env for convenience
        api_key = request.headers.get("x-api-key") or request.headers.get("authorization") or None
        if api_key and api_key.lower().startswith("bearer "):
            api_key = api_key.split(" ", 1)[1]
        if not api_key:
            return {"error": "Missing API key. Send in 'x-api-key' or 'Authorization: Bearer ...' header."}

        client = OpenAI(api_key=api_key)

        # If request provides usage override, use it; else build from today's JSON logs
        usage_map = req.usage or aggregate_for_date(req.user_id, date.today().isoformat())

        answer = _build_answer_short_expert(usage_map, req.question, client)

        add_chat(req.user_id, req.question, answer)
        return {"answer": answer}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


@app.post("/reset/{user_id}")
def reset(user_id: str):
    reset_user(user_id)
    return {"status": "ok"}
