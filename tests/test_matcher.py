import sys
sys.path.insert(0, ".")
from unittest.mock import patch, MagicMock
from core.matcher import extract_tags, score_verse, find_top_verses

SAMPLE_VOCAB = {
    "emotion": ["감사", "기쁨", "두려움", "슬픔"],
    "situation": ["가족", "관계", "소명", "직업"],
}

SAMPLE_VERSES = [
    {"chapter": 1, "verse": 1, "text": "첫번째", "tags": {"emotion": ["두려움"], "situation": ["소명"]}},
    {"chapter": 1, "verse": 2, "text": "두번째", "tags": {"emotion": ["기쁨", "감사"], "situation": ["가족"]}},
    {"chapter": 1, "verse": 3, "text": "세번째", "tags": {"emotion": ["두려움", "슬픔"], "situation": ["직업"]}},
]


def test_score_verse_exact_match():
    query = {"emotion": ["두려움"], "situation": ["소명"]}
    assert score_verse(SAMPLE_VERSES[0]["tags"], query) == 2


def test_score_verse_no_match():
    query = {"emotion": ["기쁨"], "situation": ["직업"]}
    assert score_verse(SAMPLE_VERSES[0]["tags"], query) == 0


def test_find_top_verses_returns_highest_score_first():
    query = {"emotion": ["두려움", "슬픔"], "situation": ["직업"]}
    results = find_top_verses(SAMPLE_VERSES, query, top_n=2)
    assert len(results) == 2
    assert results[0]["verse"] == 3  # 3개 매칭 (두려움+슬픔+직업)


def test_find_top_verses_excludes_zero_score():
    query = {"emotion": ["감사"], "situation": ["소명"]}
    results = find_top_verses(SAMPLE_VERSES, query, top_n=3)
    for r in results:
        assert r["score"] > 0


def test_extract_tags_calls_claude():
    mock_response = MagicMock()
    mock_response.content[0].text = '{"emotion": ["두려움"], "situation": ["직업"]}'
    with patch("core.matcher.client.messages.create", return_value=mock_response):
        tags = extract_tags("직장에서 힘들어요", SAMPLE_VOCAB)
    assert "emotion" in tags
    assert "situation" in tags
