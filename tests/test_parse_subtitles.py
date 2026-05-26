import sys
import json
sys.path.insert(0, ".")
from data.parse_subtitles import parse_subtitles, compute_ranges, BOOK_ABBR


def test_returns_list():
    episodes = parse_subtitles("subtitle.md")
    assert isinstance(episodes, list)


def test_total_episode_count():
    episodes = parse_subtitles("subtitle.md")
    assert len(episodes) == 852


def test_first_episode_structure():
    episodes = parse_subtitles("subtitle.md")
    ep = episodes[0]
    assert ep["book"] == "마태복음"
    assert ep["title"] == "예수의 계보"
    assert ep["start_ch"] == 1
    assert ep["start_v"] == 1
    assert "slug" in ep


def test_book_abbr_resolved():
    episodes = parse_subtitles("subtitle.md")
    books = {ep["book"] for ep in episodes}
    assert "마태복음" in books
    assert "요한계시록" in books
    assert "마" not in books


def test_slug_format_first_episode():
    episodes = parse_subtitles("subtitle.md")
    assert episodes[0]["slug"].startswith("001_")


def test_per_book_slug_index_resets():
    episodes = parse_subtitles("subtitle.md")
    mark_start = next(i for i, ep in enumerate(episodes) if ep["book"] == "마가복음")
    assert episodes[mark_start]["slug"].startswith("001_")


def _minimal_bible():
    with open("bible.json", encoding="utf-8") as f:
        raw = json.load(f)
    bible = {}
    for book in raw:
        name = book["korean"]
        verses = []
        for ch in book["chapters"]:
            for v in ch["verses"]:
                verses.append({"chapter": int(v["chapterNum"]), "verse": int(v["verseNum"])})
        bible[name] = verses
    return bible


def test_compute_ranges_middle_episode():
    episodes = parse_subtitles("subtitle.md")
    bible = _minimal_bible()
    ranged = compute_ranges(episodes, bible)
    # 예수의 계보 [마 1:1], 다음은 예수의 탄생 [마 1:18] → 끝절 1:17
    ep = next(ep for ep in ranged if ep["book"] == "마태복음" and ep["start_ch"] == 1 and ep["start_v"] == 1)
    assert ep["end_ch"] == 1
    assert ep["end_v"] == 17


def test_compute_ranges_chapter_boundary():
    episodes = parse_subtitles("subtitle.md")
    bible = _minimal_bible()
    ranged = compute_ranges(episodes, bible)
    # 죄인인 한 여인이 예수께 향유를 붓다 [눅 7:36], 다음은 여인들이 예수의 활동을 돕다 [눅 8:1]
    ep = next(ep for ep in ranged if ep["book"] == "누가복음" and ep["start_ch"] == 7 and ep["start_v"] == 36)
    assert ep["end_ch"] == 7
    assert ep["end_v"] == 50


def test_compute_ranges_last_episode_in_book():
    episodes = parse_subtitles("subtitle.md")
    bible = _minimal_bible()
    ranged = compute_ranges(episodes, bible)
    # 마태복음 마지막 에피소드는 제자들의 사명 [마 28:16] → 끝은 28:20
    last_matt = next(ep for ep in reversed(ranged) if ep["book"] == "마태복음")
    assert last_matt["end_ch"] == 28
    assert last_matt["end_v"] == 20
