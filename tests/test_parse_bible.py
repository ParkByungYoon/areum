import sys
sys.path.insert(0, ".")
from data.parse_bible import extract_luke


def test_returns_list():
    verses = extract_luke("bible.json")
    assert isinstance(verses, list)


def test_verse_count_reasonable():
    verses = extract_luke("bible.json")
    assert len(verses) > 1100


def test_verse_structure():
    verses = extract_luke("bible.json")
    v = verses[0]
    assert v["book"] == "누가복음"
    assert v["chapter"] == 1
    assert v["verse"] == 1
    assert isinstance(v["text"], str)
    assert len(v["text"]) > 0


def test_covers_all_24_chapters():
    verses = extract_luke("bible.json")
    chapters = {v["chapter"] for v in verses}
    assert chapters == set(range(1, 25))
