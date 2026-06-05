import sqlite3
import os
from datetime import datetime
from rank_bm25 import BM25Okapi

PRAYERS_DB = "prayers.db"


def init_db(db_path: str = PRAYERS_DB) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prayers (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                date TEXT NOT NULL,
                concern TEXT NOT NULL,
                episode_id TEXT NOT NULL,
                subtitle TEXT NOT NULL,
                passage_ref TEXT NOT NULL
            )
        """)


def save_prayer(
    user_id: str,
    concern: str,
    episode_id: str,
    subtitle: str,
    passage_ref: str,
    db_path: str = PRAYERS_DB,
) -> dict:
    init_db(db_path)
    now = datetime.now()
    record = {
        "id": now.strftime("%Y%m%d-%H%M%S-%f-") + user_id,
        "user_id": user_id,
        "date": now.isoformat(timespec="seconds"),
        "concern": concern,
        "episode_id": episode_id,
        "subtitle": subtitle,
        "passage_ref": passage_ref,
    }
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO prayers VALUES (:id, :user_id, :date, :concern, :episode_id, :subtitle, :passage_ref)",
            record,
        )
    return record


def find_connection(
    user_id: str,
    concern: str,
    episode_id: str,
    db_path: str = PRAYERS_DB,
) -> dict | None:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM prayers WHERE user_id = ? ORDER BY date ASC",
            (user_id,),
        ).fetchall()

    if not rows:
        return None

    prayers = [dict(r) for r in rows]
    today = datetime.now().date()

    # Case 1: 같은 에피소드를 전에 받은 경우
    same = [p for p in prayers if p["episode_id"] == episode_id]
    if same:
        recent = same[-1]  # ORDER BY date ASC이므로 마지막이 최신
        days_ago = (today - datetime.fromisoformat(recent["date"]).date()).days
        return {"type": "same_episode", "record": recent, "days_ago": days_ago}

    # Case 2: BM25로 유사한 고민 검색
    corpus = [p["concern"].split() for p in prayers]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(concern.split())
    best_idx = int(max(range(len(scores)), key=lambda i: scores[i]))
    query_tokens = set(concern.split())
    best_tokens = set(prayers[best_idx]["concern"].split())
    if not (query_tokens & best_tokens):
        return None

    best = prayers[best_idx]
    days_ago = (today - datetime.fromisoformat(best["date"]).date()).days
    return {"type": "similar_concern", "record": best, "days_ago": days_ago}
