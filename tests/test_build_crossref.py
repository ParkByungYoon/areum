import sys
sys.path.insert(0, ".")
from data.build_crossref import load_crossrefs_for_episode, _build_connected_episodes, BOOK_NAMES

# 테스트용 샘플 rows (votes 10~20) — 테스트에서 min_votes=10 명시 사용
SAMPLE_ROWS = [
    (42, 15, 11, 40, 6, 12, 15, 12),   # 누가 15:11 → 마태 6:12-15, votes=12
    (42, 15, 12, 41, 4, 3, 9, 11),     # 누가 15:12 → 마가 4:3-9, votes=11
    (42, 15, 32, 43, 15, 11, 17, 15),  # 누가 15:32 → 요한 15:11-17, votes=15
    (43, 3, 16, 42, 19, 10, 10, 20),   # 요한 3:16 → 누가 19:10, votes=20
]

EPISODE_LUKE = {"book": 42, "book_name": "누가복음", "episode": "탕자의 비유", "chapter_start": 15, "verse_start": 11, "chapter_end": 15, "verse_end": 32}
EPISODE_JOHN = {"book": 43, "book_name": "요한복음", "episode": "요한복음 3:16", "chapter_start": 3, "verse_start": 16, "chapter_end": 3, "verse_end": 21}


def test_filters_by_book_and_verse_range():
    refs = load_crossrefs_for_episode(SAMPLE_ROWS, EPISODE_LUKE, min_votes=10)
    assert all(r["from_verse"] >= 11 and r["from_verse"] <= 32 for r in refs)
    assert len(refs) == 3


def test_votes_threshold_filters_low_votes():
    low_votes_rows = [(42, 15, 11, 40, 6, 12, 15, 5)]  # votes=5 < 10
    refs = load_crossrefs_for_episode(low_votes_rows, EPISODE_LUKE, min_votes=10)
    assert len(refs) == 0


def test_different_book_episode():
    refs = load_crossrefs_for_episode(SAMPLE_ROWS, EPISODE_JOHN, min_votes=10)
    assert len(refs) == 1


def test_includes_to_verse_range():
    refs = load_crossrefs_for_episode(SAMPLE_ROWS, EPISODE_LUKE, min_votes=10)
    assert all("to_verse_start" in r and "to_verse_end" in r for r in refs)


def test_includes_book_name():
    refs = load_crossrefs_for_episode(SAMPLE_ROWS, EPISODE_LUKE, min_votes=10)
    assert all("to_book_name" in r for r in refs)


def test_sorted_by_votes_desc():
    refs = load_crossrefs_for_episode(SAMPLE_ROWS, EPISODE_LUKE, min_votes=10)
    votes = [r["votes"] for r in refs]
    assert votes == sorted(votes, reverse=True)


def test_book_names_covers_four_gospels():
    assert BOOK_NAMES[40] == "마태복음"
    assert BOOK_NAMES[41] == "마가복음"
    assert BOOK_NAMES[42] == "누가복음"
    assert BOOK_NAMES[43] == "요한복음"


def _make_ep(book, episode, chapter, refs):
    return {
        "book": book, "book_name": BOOK_NAMES[book], "episode": episode,
        "chapter_start": chapter, "verse_start": 1, "chapter_end": chapter, "verse_end": 10,
        "cross_references": refs,
    }


def _ref(to_book, to_chapter, to_verse_start):
    return {"to_book": to_book, "to_chapter": to_chapter, "to_verse_start": to_verse_start,
            "to_verse_end": to_verse_start, "votes": 15, "from_verse": 1,
            "to_book_name": BOOK_NAMES[to_book]}


def test_connected_episodes_ref_within_range():
    # ep_a의 cross-ref → (40, 5, 3)이 ep_b 범위(book=40, ch=5, vs=1-10) 안에 속함 → 연결
    ep_a = _make_ep(42, "A", 15, [_ref(40, 5, 3)])
    ep_b = _make_ep(40, "B", 5, [_ref(43, 1, 1)])   # ep_b의 ref는 ep_c 범위 밖
    ep_c = _make_ep(43, "C", 3, [_ref(41, 2, 5)])   # ep_c의 ref는 아무 에피소드 범위 밖

    connected = _build_connected_episodes([ep_a, ep_b, ep_c])
    assert len(connected[0]) == 1 and connected[0][0]["episode"] == "B"
    assert len(connected[1]) == 1 and connected[1][0]["episode"] == "A"
    assert len(connected[2]) == 0


def test_ref_outside_range_not_connected():
    # ep_a의 cross-ref → (40, 5, 99)은 ep_b 범위(1-10) 밖 → 연결 안 됨
    ep_a = _make_ep(42, "A", 15, [_ref(40, 5, 99)])
    ep_b = _make_ep(40, "B", 5, [])

    connected = _build_connected_episodes([ep_a, ep_b])
    assert len(connected[0]) == 0
    assert len(connected[1]) == 0


def test_isolated_episode_has_empty_connected():
    ep = _make_ep(42, "A", 15, [])
    connected = _build_connected_episodes([ep])
    assert connected[0] == []
