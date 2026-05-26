import sys
sys.path.insert(0, ".")
from data.episode_pipeline import load_bible, extract_verses


def test_load_bible_returns_dict():
    bible = load_bible("bible.json")
    assert isinstance(bible, dict)


def test_load_bible_contains_nt_books():
    bible = load_bible("bible.json")
    assert "마태복음" in bible
    assert "요한계시록" in bible


def test_load_bible_verse_structure():
    bible = load_bible("bible.json")
    v = bible["마태복음"][0]
    assert v["chapter"] == 1
    assert v["verse"] == 1
    assert isinstance(v["text"], str)
    assert len(v["text"]) > 0


def test_extract_verses_single_chapter():
    bible = load_bible("bible.json")
    text = extract_verses(bible, "마태복음", 1, 1, 1, 3)
    assert "1:1" in text
    assert "1:2" in text
    assert "1:3" in text
    assert "1:4" not in text


def test_extract_verses_multi_chapter():
    bible = load_bible("bible.json")
    text = extract_verses(bible, "마태복음", 1, 25, 2, 2)
    assert "1:25" in text
    assert "2:1" in text
    assert "2:2" in text
    assert "2:3" not in text


def test_extract_verses_invalid_book():
    bible = load_bible("bible.json")
    assert extract_verses(bible, "존재하지않는책", 1, 1, 1, 5) == ""
