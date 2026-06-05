"""bible.json + episodes.json → data/gospel_episodes.json (사복음서 구절+요약)"""
import json
import re
from pathlib import Path

GOSPEL_BOOKS = {"마태복음", "마가복음", "누가복음", "요한복음"}
EPISODES_DIR = Path("data/episodes")
OUTPUT = Path("data/gospel_episodes.json")


def _load_bible_verse_map(bible_path: str = "bible.json") -> dict:
    """book_name → {(chapter, verse): text} 전체"""
    with open(bible_path, encoding="utf-8") as f:
        raw = json.load(f)
    result = {}
    for book in raw:
        name = book["korean"]
        verses = {}
        for ch in book["chapters"]:
            for v in ch["verses"]:
                verses[(int(v["chapterNum"]), int(v["verseNum"]))] = v["verse"]
        result[name] = verses
    return result


def _extract_verses(verse_map: dict, start_ch: int, start_v: int, end_ch: int, end_v: int) -> list:
    return [
        {"chapter": ch, "verse": v, "text": text}
        for (ch, v), text in sorted(verse_map.items())
        if (ch, v) >= (start_ch, start_v) and (ch, v) <= (end_ch, end_v)
    ]


def _extract_section(content: str, marker: str, next_marker: str = "\n## ") -> str:
    idx = content.find(marker)
    if idx == -1:
        return ""
    text = content[idx + len(marker):]
    end = text.find(next_marker)
    return text[:end].strip() if end != -1 else text.strip()


def _read_episode_texts(book_name: str, title: str) -> tuple[str, str]:
    """data/episodes/<book>/*_<safe_title>.md에서 (situation, meaning) 추출"""
    safe_title = re.sub(r"[^\w]", "_", title, flags=re.UNICODE).strip("_")
    book_dir = EPISODES_DIR / book_name
    if not book_dir.exists():
        return "", ""
    matches = list(book_dir.glob(f"*_{safe_title}.md"))
    if not matches:
        return "", ""
    content = matches[0].read_text(encoding="utf-8")
    situation = _extract_section(content, "## 1-step (상황)\n")
    meaning = _extract_section(content, "## 2-step (의미)\n")
    return situation, meaning


def build(
    bible_path: str = "bible.json",
    episodes_path: str = "data/episodes.json",
    output_path: str = str(OUTPUT),
) -> list:
    bible = _load_bible_verse_map(bible_path)

    with open(episodes_path, encoding="utf-8") as f:
        episodes = json.load(f)

    groups: dict[str, dict] = {}
    for ep in episodes:
        book_name = ep["book_name"]
        if book_name not in GOSPEL_BOOKS:
            continue
        subtitle = ep["episode"]
        verses = _extract_verses(
            bible.get(book_name, {}),
            ep["chapter_start"],
            ep["verse_start"],
            ep["chapter_end"],
            ep["verse_end"],
        )
        passage = {
            "book": book_name,
            "chapter_start": ep["chapter_start"],
            "verse_start": ep["verse_start"],
            "chapter_end": ep["chapter_end"],
            "verse_end": ep["verse_end"],
            "verses": verses,
        }
        if subtitle not in groups:
            situation, meaning = _read_episode_texts(book_name, subtitle)
            groups[subtitle] = {
                "subtitle": subtitle,
                "situation": situation,
                "meaning": meaning,
                "passages": [],
            }
        groups[subtitle]["passages"].append(passage)

    result = list(groups.values())
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"완료: {len(result)}개 에피소드 그룹 → {output_path}")
    return result


if __name__ == "__main__":
    build()
