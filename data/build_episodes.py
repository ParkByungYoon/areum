"""subtitle.md의 모든 사복음서 에피소드를 data/episodes.json으로 변환"""
import json
import sys

sys.path.insert(0, ".")

from data.parse_subtitles import parse_subtitles, compute_ranges
from data.episode_pipeline import load_bible

OUTPUT_PATH = "data/episodes.json"


def build(
    subtitle_path: str = "subtitle.md",
    bible_path: str = "bible.json",
    output_path: str = OUTPUT_PATH,
) -> list[dict]:
    bible = load_bible(bible_path)
    episodes_raw = parse_subtitles(subtitle_path)
    episodes_with_ranges = compute_ranges(episodes_raw, bible)

    result = []
    for ep in episodes_with_ranges:
        result.append({
            "book_name": ep["book"],
            "episode": ep["title"],
            "chapter_start": ep["start_ch"],
            "verse_start": ep["start_v"],
            "chapter_end": ep["end_ch"],
            "verse_end": ep["end_v"],
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"완료: {len(result)}개 에피소드 → {output_path}")
    return result


if __name__ == "__main__":
    build()
