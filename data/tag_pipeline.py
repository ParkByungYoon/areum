import json
import os
import re
import time
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

SYSTEM_PROMPT = """성경 구절들을 분석하여 현대인의 삶의 고민과 연결되는 태그를 추출합니다.
각 구절에 대해 감정 축과 상황 축으로 태그를 부여하세요.

JSON 배열만 출력하세요. 다른 텍스트 없이:
[
  {"idx": 0, "emotion": ["태그1", "태그2"], "situation": ["태그1"]},
  ...
]

감정 태그 예시: 두려움, 외로움, 슬픔, 감사, 분노, 불안, 기쁨, 죄책감, 소망, 평안, 지침, 경외
상황 태그 예시: 관계, 직업, 건강, 가족, 자아정체성, 미래, 재정, 소명, 믿음, 공동체, 용서"""


def tag_batch(verses: list[dict]) -> list[dict]:
    content = "\n".join(
        f"[{i}] 누가복음 {v['chapter']}:{v['verse']} — {v['text']}"
        for i, v in enumerate(verses)
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    raw = response.content[0].text.strip()
    # Strip markdown code blocks if model wraps response in ```json ... ```
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    tags_list = json.loads(raw)
    return [
        {
            **verses[t["idx"]],
            "tags": {"emotion": t["emotion"], "situation": t["situation"]},
        }
        for t in tags_list
    ]


def tag_batch_with_retry(verses: list[dict], retries: int = 3) -> list[dict]:
    for attempt in range(retries):
        try:
            return tag_batch(verses)
        except Exception as e:
            if attempt < retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  재시도 {attempt + 1}/{retries - 1} ({wait}s 대기): {e}")
                time.sleep(wait)
            else:
                raise


def run_pipeline(
    raw_path: str = "data/luke_raw.json",
    output_path: str = "data/luke_tagged.json",
    batch_size: int = 5,
):
    with open(raw_path, encoding="utf-8") as f:
        all_verses = json.load(f)

    tagged = []
    if os.path.exists(output_path):
        with open(output_path, encoding="utf-8") as f:
            tagged = json.load(f)

    # Gap-fill: find verses missing by chapter:verse identity
    tagged_ids = {(v["chapter"], v["verse"]) for v in tagged}
    missing = [v for v in all_verses if (v["chapter"], v["verse"]) not in tagged_ids]

    if not missing:
        print("이미 완료됨.")
        return

    print(f"남은 절: {len(missing)}개")

    for i in range(0, len(missing), batch_size):
        batch = missing[i : i + batch_size]
        refs = ", ".join(f"{v['chapter']}:{v['verse']}" for v in batch)
        print(f"태그 중... {refs} ({i + 1}~{min(i + batch_size, len(missing))} / {len(missing)})")
        try:
            result = tag_batch_with_retry(batch)
            tagged.extend(result)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(tagged, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"오류 (건너뜀): {e}")

    print(f"태그 완료: {len(tagged)}절 → {output_path}")


if __name__ == "__main__":
    run_pipeline()
