import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, ".")


def _make_bible(tmp_dir: str) -> str:
    data = [
        {
            "korean": "마태복음",
            "english": "Matthew",
            "testament": "NT",
            "categoryNumber": 1,
            "chapters": [
                {
                    "chapterNum": "14",
                    "verses": [
                        {"chapterNum": "14", "verseNum": "13", "verse": "예수께서 이 말씀을 들으시고"},
                        {"chapterNum": "14", "verseNum": "14", "verse": "무리를 보시고 불쌍히 여기셨다"},
                    ],
                }
            ],
        },
        {
            "korean": "마가복음",
            "english": "Mark",
            "testament": "NT",
            "categoryNumber": 2,
            "chapters": [
                {
                    "chapterNum": "6",
                    "verses": [
                        {"chapterNum": "6", "verseNum": "30", "verse": "사도들이 예수께 모여"},
                    ],
                }
            ],
        },
    ]
    path = Path(tmp_dir) / "bible.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(path)


def _make_episodes(tmp_dir: str) -> str:
    data = [
        {
            "book": 40,
            "book_name": "마태복음",
            "episode": "오천 명을 먹이심",
            "chapter_start": 14,
            "verse_start": 13,
            "chapter_end": 14,
            "verse_end": 14,
        },
        {
            "book": 41,
            "book_name": "마가복음",
            "episode": "오천 명을 먹이심",
            "chapter_start": 6,
            "verse_start": 30,
            "chapter_end": 6,
            "verse_end": 30,
        },
    ]
    path = Path(tmp_dir) / "episodes.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(path)


def test_build_creates_output():
    from data.parse_episodes import build
    with tempfile.TemporaryDirectory() as tmp:
        bible_path = _make_bible(tmp)
        episodes_path = _make_episodes(tmp)
        output_path = Path(tmp) / "gospel_episodes.json"
        result = build(bible_path, episodes_path, str(output_path))
        assert output_path.exists()
        assert len(result) == 1
        assert result[0]["subtitle"] == "오천 명을 먹이심"


def test_groups_by_subtitle():
    from data.parse_episodes import build
    with tempfile.TemporaryDirectory() as tmp:
        bible_path = _make_bible(tmp)
        episodes_path = _make_episodes(tmp)
        output_path = Path(tmp) / "out.json"
        result = build(bible_path, episodes_path, str(output_path))
        assert len(result) == 1
        assert len(result[0]["passages"]) == 2


def test_verses_extracted():
    from data.parse_episodes import build
    with tempfile.TemporaryDirectory() as tmp:
        bible_path = _make_bible(tmp)
        episodes_path = _make_episodes(tmp)
        output_path = Path(tmp) / "out.json"
        result = build(bible_path, episodes_path, str(output_path))
        matthew_passage = next(p for p in result[0]["passages"] if p["book"] == "마태복음")
        assert len(matthew_passage["verses"]) == 2
        assert matthew_passage["verses"][0]["text"] == "예수께서 이 말씀을 들으시고"


def test_non_gospel_excluded():
    from data.parse_episodes import build
    with tempfile.TemporaryDirectory() as tmp:
        bible_path = Path(tmp) / "bible.json"
        bible_path.write_text(json.dumps([
            {"korean": "로마서", "english": "Romans", "testament": "NT",
             "categoryNumber": 1,
             "chapters": [{"chapterNum": "1", "verses": [
                 {"chapterNum": "1", "verseNum": "1", "verse": "바울이 쓴 편지"}
             ]}]}
        ], ensure_ascii=False), encoding="utf-8")
        eps_path = Path(tmp) / "episodes.json"
        eps_path.write_text(json.dumps([
            {"book_name": "로마서", "episode": "믿음으로",
             "chapter_start": 1, "verse_start": 1, "chapter_end": 1, "verse_end": 1}
        ], ensure_ascii=False), encoding="utf-8")
        result = build(str(bible_path), str(eps_path), str(Path(tmp) / "out.json"))
        assert len(result) == 0
