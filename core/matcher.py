import json
import re
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()


def score_verse(verse_tags: dict, query_tags: dict) -> int:
    emotion_overlap = len(
        set(verse_tags.get("emotion", [])) & set(query_tags.get("emotion", []))
    )
    situation_overlap = len(
        set(verse_tags.get("situation", [])) & set(query_tags.get("situation", []))
    )
    return emotion_overlap + situation_overlap


def find_top_verses(verses: list[dict], query_tags: dict, top_n: int = 3) -> list[dict]:
    scored = [{**v, "score": score_verse(v["tags"], query_tags)} for v in verses]
    filtered = [v for v in scored if v["score"] > 0]
    return sorted(filtered, key=lambda v: v["score"], reverse=True)[:top_n]


def extract_tags(user_input: str, vocab: dict) -> dict:
    emotion_list = ", ".join(vocab["emotion"])
    situation_list = ", ".join(vocab["situation"])
    system = (
        f"사용자의 고민을 분석하여 아래 태그 목록에서 관련 태그를 선택하세요.\n\n"
        f"감정 태그 목록: {emotion_list}\n"
        f"상황 태그 목록: {situation_list}\n\n"
        '반드시 JSON만 출력하세요: {"emotion": ["태그1"], "situation": ["태그1"]}'
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system=system,
        messages=[{"role": "user", "content": user_input}],
    )
    raw = response.content[0].text.strip()
    # Strip markdown code blocks if present
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)
