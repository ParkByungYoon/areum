import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, ".")


def _make_episodes_file(tmp_dir: str) -> str:
    episodes = [
        {
            "subtitle": "오천 명을 먹이심",
            "summary": "광야에서 오천 명을 먹이신 이야기",
            "passages": [
                {
                    "book": "마태복음",
                    "chapter_start": 14,
                    "verse_start": 13,
                    "chapter_end": 14,
                    "verse_end": 21,
                    "verses": [
                        {"chapter": 14, "verse": 13, "text": "광야에서 예수께서 기도하셨다"},
                        {"chapter": 14, "verse": 14, "text": "무리를 보시고 불쌍히 여기셨다"},
                    ],
                }
            ],
        },
        {
            "subtitle": "탕자의 비유",
            "summary": "아버지께로 돌아온 아들 이야기",
            "passages": [
                {
                    "book": "누가복음",
                    "chapter_start": 15,
                    "verse_start": 11,
                    "chapter_end": 15,
                    "verse_end": 32,
                    "verses": [
                        {"chapter": 15, "verse": 11, "text": "아버지와 두 아들이 있었다"},
                        {"chapter": 15, "verse": 20, "text": "아버지가 달려나가 아들을 맞이하였다"},
                    ],
                }
            ],
        },
        {
            "subtitle": "포도원 품꾼의 비유",
            "summary": "일한 시간과 무관하게 동일한 삯을 받는 이야기",
            "passages": [
                {
                    "book": "마태복음",
                    "chapter_start": 20,
                    "verse_start": 1,
                    "chapter_end": 20,
                    "verse_end": 16,
                    "verses": [
                        {"chapter": 20, "verse": 1, "text": "천국은 포도원 주인과 같으니"},
                        {"chapter": 20, "verse": 16, "text": "나중 된 자가 먼저 되고 먼저 된 자가 나중 되리라"},
                    ],
                }
            ],
        },
    ]
    path = Path(tmp_dir) / "gospel_episodes.json"
    path.write_text(json.dumps(episodes, ensure_ascii=False), encoding="utf-8")
    return str(path)


def test_match_returns_results():
    from core.matcher import EpisodeMatcher
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_episodes_file(tmp)
        m = EpisodeMatcher(path)
        results = m.match("배고파서 힘들어요", top_n=3)
        assert len(results) >= 1
        assert "subtitle" in results[0]
        assert "passages" in results[0]


def test_match_top_n_respected():
    from core.matcher import EpisodeMatcher
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_episodes_file(tmp)
        m = EpisodeMatcher(path)
        results = m.match("아버지", top_n=1)
        assert len(results) == 1


def test_match_includes_score():
    from core.matcher import EpisodeMatcher
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_episodes_file(tmp)
        m = EpisodeMatcher(path)
        results = m.match("아버지와 아들", top_n=2)
        for r in results:
            assert "score" in r


def test_match_includes_best_passage_idx():
    from core.matcher import EpisodeMatcher
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_episodes_file(tmp)
        m = EpisodeMatcher(path)
        results = m.match("불쌍히 여기심", top_n=1)
        assert "best_passage_idx" in results[0]
        assert isinstance(results[0]["best_passage_idx"], int)


def test_match_empty_query():
    from core.matcher import EpisodeMatcher
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_episodes_file(tmp)
        m = EpisodeMatcher(path)
        results = m.match("", top_n=3)
        assert isinstance(results, list)
