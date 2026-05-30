import sys
sys.path.insert(0, ".")
from data.build_crossref import load_crossrefs_for_episode, BOOK_NAMES

SAMPLE_ROWS = [
    (42, 15, 11, 1, 41, 14, 14, 12),
    (42, 15, 12, 19, 2, 1, 5, 8),
    (42, 15, 32, 15, 3, 1, 1, 5),
    (43, 3, 16, 19, 1, 1, 1, 20),  # 요한복음 3:16 — 다른 책
]

EPISODE_LUKE = {"book": 42, "book_name": "누가복음", "episode": "탕자의 비유", "chapter": 15, "verse_start": 11, "verse_end": 32}
EPISODE_JOHN = {"book": 43, "book_name": "요한복음", "episode": "요한복음 3:16", "chapter": 3, "verse_start": 16, "verse_end": 21}


def test_filters_by_book_and_verse_range():
    refs = load_crossrefs_for_episode(SAMPLE_ROWS, EPISODE_LUKE)
    assert all(r["from_verse"] >= 11 and r["from_verse"] <= 32 for r in refs)
    assert len(refs) == 3


def test_different_book_episode():
    refs = load_crossrefs_for_episode(SAMPLE_ROWS, EPISODE_JOHN)
    assert len(refs) == 1


def test_includes_to_verse_range():
    refs = load_crossrefs_for_episode(SAMPLE_ROWS, EPISODE_LUKE)
    assert all("to_verse_start" in r and "to_verse_end" in r for r in refs)


def test_includes_book_name():
    refs = load_crossrefs_for_episode(SAMPLE_ROWS, EPISODE_LUKE)
    assert all("to_book_name" in r for r in refs)


def test_sorted_by_votes_desc():
    refs = load_crossrefs_for_episode(SAMPLE_ROWS, EPISODE_LUKE)
    votes = [r["votes"] for r in refs]
    assert votes == sorted(votes, reverse=True)


def test_book_names_covers_four_gospels():
    assert BOOK_NAMES[40] == "마태복음"
    assert BOOK_NAMES[41] == "마가복음"
    assert BOOK_NAMES[42] == "누가복음"
    assert BOOK_NAMES[43] == "요한복음"
