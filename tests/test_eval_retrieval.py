import sys
sys.path.insert(0, ".")
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from evals.eval_retrieval import (
    parse_episode_file, load_episodes,
    tokenize, search_bm25,
    cosine_similarity, search_embedding,
    normalize_scores, search_hybrid,
)


def test_parse_episode_basic():
    content = (
        "# 예수의 계보\n"
        "**범위**: 마태복음 1:1-1:17\n\n"
        "## 1-step (상황)\n"
        "족보 내용이다.\n\n"
        "## 2-step (의미)\n"
        "계보의 의미이다.\n"
    )
    ep = parse_episode_file(content, "마태복음", "001_예수의_계보")
    assert ep["book"] == "마태복음"
    assert ep["title"] == "예수의 계보"
    assert ep["slug"] == "001_예수의_계보"
    assert ep["step1"] == "족보 내용이다."
    assert ep["step2"] == "계보의 의미이다."
    assert "예수의 계보" in ep["text"]
    assert "족보 내용이다." in ep["text"]
    assert "계보의 의미이다." in ep["text"]


def test_parse_episode_missing_step2():
    content = "# 제목\n\n## 1-step (상황)\n상황 요약\n\n## 2-step (의미)\n"
    ep = parse_episode_file(content, "마태복음", "001_제목")
    assert ep["step1"] == "상황 요약"
    assert ep["step2"] == ""


def test_parse_episode_no_step1():
    content = "# 제목\n\n## 1-step (상황)\n\n## 2-step (의미)\n의미 해석\n"
    ep = parse_episode_file(content, "마태복음", "001_제목")
    assert ep["step1"] == ""
    assert ep["step2"] == "의미 해석"


def test_load_episodes_returns_nonempty():
    episodes = load_episodes("data/episodes")
    assert len(episodes) > 0


def test_load_episodes_structure():
    episodes = load_episodes("data/episodes")
    ep = episodes[0]
    for key in ["book", "title", "slug", "step1", "step2", "text"]:
        assert key in ep, f"Missing key: {key}"


# --- BM25 ---

SAMPLE_EPISODES = [
    {
        "book": "마태복음", "title": "배신", "slug": "a",
        "step1": "동료에게 배신당했다", "step2": "믿음의 상실",
        "text": "배신 동료 믿음 상실",
    },
    {
        "book": "마태복음", "title": "사랑", "slug": "b",
        "step1": "가족의 사랑", "step2": "기쁨 감사",
        "text": "사랑 가족 기쁨 감사",
    },
    {
        "book": "마태복음", "title": "두려움", "slug": "c",
        "step1": "앞이 안 보인다", "step2": "두려움과 평안",
        "text": "두려움 앞 평안",
    },
]


def test_tokenize_splits_on_whitespace():
    tokens = tokenize("배신당했어요 정말")
    assert "배신당했어요" in tokens
    assert "정말" in tokens


def test_tokenize_removes_punctuation():
    tokens = tokenize("힘들어요. 정말!")
    assert "." not in tokens
    assert "!" not in tokens


def test_search_bm25_top_result():
    results = search_bm25(SAMPLE_EPISODES, "동료에게 배신당했어요", top_k=1)
    assert len(results) == 1
    assert results[0]["slug"] == "a"


def test_search_bm25_returns_top_k():
    results = search_bm25(SAMPLE_EPISODES, "사랑 가족", top_k=2)
    assert len(results) == 2


def test_search_bm25_has_float_score():
    results = search_bm25(SAMPLE_EPISODES, "배신", top_k=3)
    for r in results:
        assert "score" in r
        assert isinstance(r["score"], float)


def test_search_bm25_does_not_modify_episodes():
    original_keys = set(SAMPLE_EPISODES[0].keys())
    search_bm25(SAMPLE_EPISODES, "배신", top_k=1)
    assert set(SAMPLE_EPISODES[0].keys()) == original_keys


# --- Embedding ---


def test_cosine_similarity_identical():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == pytest.approx(0.0)


def test_search_embedding_orders_by_similarity():
    cache = {
        "a": [1.0, 0.0],
        "b": [0.0, 1.0],
        "c": [0.7, 0.7],
    }
    query_embedding = [1.0, 0.0]
    results = search_embedding(SAMPLE_EPISODES, query_embedding, cache, top_k=1)
    assert results[0]["slug"] == "a"


def test_search_embedding_has_score():
    cache = {"a": [1.0, 0.0], "b": [0.0, 1.0], "c": [0.5, 0.5]}
    results = search_embedding(SAMPLE_EPISODES, [1.0, 0.0], cache, top_k=3)
    for r in results:
        assert "score" in r
        assert 0.0 <= r["score"] <= 1.0 + 1e-9


def test_search_embedding_skips_missing_cache():
    cache = {"a": [1.0, 0.0]}  # b, c missing
    results = search_embedding(SAMPLE_EPISODES, [1.0, 0.0], cache, top_k=5)
    slugs = [r["slug"] for r in results]
    assert "b" not in slugs
    assert "c" not in slugs


# --- Hybrid ---


def test_normalize_scores_basic():
    normalized = normalize_scores([0.0, 5.0, 10.0])
    assert normalized[0] == pytest.approx(0.0)
    assert normalized[2] == pytest.approx(1.0)
    assert normalized[1] == pytest.approx(0.5)


def test_normalize_scores_all_equal():
    normalized = normalize_scores([3.0, 3.0, 3.0])
    assert normalized == [0.0, 0.0, 0.0]


def test_normalize_scores_single():
    assert normalize_scores([5.0]) == [0.0]


def test_search_hybrid_alpha1_top_matches_bm25():
    cache = {"a": [1.0, 0.0], "b": [0.0, 1.0], "c": [0.5, 0.5]}
    bm25_top = search_bm25(SAMPLE_EPISODES, "배신 동료", top_k=1)[0]["slug"]
    hybrid_top = search_hybrid(
        SAMPLE_EPISODES, "배신 동료", [1.0, 0.0], cache, alpha=1.0, top_k=1
    )[0]["slug"]
    assert hybrid_top == bm25_top


def test_search_hybrid_has_score():
    cache = {"a": [1.0, 0.0], "b": [0.0, 1.0], "c": [0.5, 0.5]}
    results = search_hybrid(SAMPLE_EPISODES, "배신", [1.0, 0.0], cache, alpha=0.5, top_k=3)
    for r in results:
        assert "score" in r
        assert 0.0 <= r["score"] <= 1.0 + 1e-9
