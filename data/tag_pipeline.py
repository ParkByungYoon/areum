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

    start_idx = len(tagged)
    if start_idx == len(all_verses):
        print("이미 완료됨.")
        return

    remaining = all_verses[start_idx:]

    for i in range(0, len(remaining), batch_size):
        batch = remaining[i : i + batch_size]
        current = start_idx + i + 1
        end = start_idx + i + len(batch)
        print(f"태그 중... {current}~{end} / {len(all_verses)}")
        try:
            result = tag_batch(batch)
            tagged.extend(result)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(tagged, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"오류 (batch {i}): {e}")
            time.sleep(5)

    print(f"태그 완료: {len(tagged)}절 → {output_path}")


if __name__ == "__main__":
    run_pipeline()
