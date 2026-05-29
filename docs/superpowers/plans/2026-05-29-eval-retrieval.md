# eval_retrieval.py Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 4가지 에피소드 검색 전략(BM25, Embedding, Hybrid, LLM Reranking)을 구현하고, 10개 쿼리에 대한 결과를 `evals/eval_queries.json`에 저장해 수동 비교 평가한다.

**Architecture:** 단일 스크립트 `evals/eval_retrieval.py`에 모든 전략 함수를 구현한다. `evals/eval_queries.json`이 쿼리 입력과 결과 저장을 모두 담당한다. 에피소드 임베딩은 `evals/embeddings_cache.json`에 캐시해 재실행 비용을 줄인다.

**Tech Stack:** Python 3.11, `rank-bm25`, `openai` (text-embedding-3-small), `anthropic` (claude-haiku-4-5-20251001), `python-dotenv`

---

## File Structure

| 파일 | 역할 |
|------|------|
| `evals/eval_retrieval.py` | 4가지 전략 함수 + 메인 러너 + CLI |
| `evals/eval_queries.json` | 쿼리 10개 + 실행 결과 저장 |
| `evals/embeddings_cache.json` | 에피소드 임베딩 캐시 (자동 생성) |
| `tests/test_eval_retrieval.py` | 단위 테스트 |

---

## Task 1: 의존성 설치 + eval_queries.json 생성

**Files:**
- Install: `rank-bm25`, `openai`
- Create: `evals/eval_queries.json`
- Modify: `.gitignore`

- [ ] **Step 1: 의존성 설치**

```bash
conda run -n areum pip install rank-bm25 openai
```

Expected output: `Successfully installed rank-bm25-0.3.1 openai-...`

- [ ] **Step 2: requirements.txt 업데이트**

`requirements.txt`를 아래 내용으로 교체한다:

```
anthropic>=0.40.0
pytest>=8.0.0
python-dotenv>=1.0.0
rank-bm25>=0.3.1
openai>=1.0.0
```

- [ ] **Step 3: evals/eval_queries.json 생성**

```json
[
  {"query": "회사에서 믿었던 동료한테 배신당했어요."},
  {"query": "기도를 해도 응답이 없는 것 같아요."},
  {"query": "용서하기가 너무 힘들어요."},
  {"query": "두렵고 앞이 안 보여요. 어떻게 해야 할지 모르겠어요."},
  {"query": "돈 걱정이 너무 심해요. 생활이 너무 힘들어요."},
  {"query": "제가 너무 죄인 같아서 하나님 앞에 나아갈 자격이 없는 것 같아요."},
  {"query": "아무도 저를 알아주지 않는 것 같아요."},
  {"query": "사람들 앞에서 창피를 당했어요."},
  {"query": "가족과의 관계가 너무 힘들어요."},
  {"query": "하나님이 정말 존재하시는지 모르겠어요."}
]
```

- [ ] **Step 4: .gitignore에 캐시 파일 추가**

`.gitignore` 파일에 아래 줄을 추가한다:

```
evals/embeddings_cache.json
```

- [ ] **Step 5: 커밋**

```bash
git add requirements.txt evals/eval_queries.json .gitignore
git commit -m "chore: install rank-bm25 and openai, add eval_queries.json"
```

---

## Task 2: 에피소드 로더

**Files:**
- Create: `evals/eval_retrieval.py`
- Create: `tests/test_eval_retrieval.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_eval_retrieval.py`를 생성한다:

```python
import sys
sys.path.insert(0, ".")
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from evals.eval_retrieval import parse_episode_file, load_episodes


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
```

- [ ] **Step 2: 실패 확인**

```bash
conda run -n areum pytest tests/test_eval_retrieval.py -v
```

Expected: `ModuleNotFoundError: No module named 'evals'`

- [ ] **Step 3: evals/eval_retrieval.py 생성 (로더 구현)**

```python
import json
import re
import argparse
import math
import sys
from pathlib import Path

import anthropic
import openai
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

load_dotenv()

EPISODES_DIR = "data/episodes"
QUERIES_FILE = "evals/eval_queries.json"
EMBEDDINGS_CACHE_FILE = "evals/embeddings_cache.json"
EMBEDDING_MODEL = "text-embedding-3-small"

openai_client = openai.OpenAI()
anthropic_client = anthropic.Anthropic()


def parse_episode_file(content: str, book: str, slug: str) -> dict:
    title = ""
    for line in content.split("\n"):
        if line.startswith("# "):
            title = line[2:].strip()
            break

    step1_marker = "## 1-step (상황)\n"
    step2_marker = "## 2-step (의미)\n"
    idx1 = content.find(step1_marker)
    idx2 = content.find(step2_marker)

    step1 = ""
    step2 = ""
    if idx1 != -1:
        start = idx1 + len(step1_marker)
        end = idx2 if idx2 != -1 else len(content)
        step1 = content[start:end].strip()
    if idx2 != -1:
        step2 = content[idx2 + len(step2_marker):].strip()

    text = " ".join(filter(None, [title, step1, step2]))

    return {
        "book": book,
        "title": title,
        "slug": slug,
        "step1": step1,
        "step2": step2,
        "text": text,
    }


def load_episodes(episodes_dir: str = EPISODES_DIR) -> list[dict]:
    episodes = []
    for md_file in sorted(Path(episodes_dir).rglob("*.md")):
        book = md_file.parent.name
        slug = md_file.stem
        content = md_file.read_text(encoding="utf-8")
        episodes.append(parse_episode_file(content, book, slug))
    return episodes
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
conda run -n areum pytest tests/test_eval_retrieval.py -v
```

Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add evals/eval_retrieval.py tests/test_eval_retrieval.py
git commit -m "feat: add episode loader for eval pipeline"
```

---

## Task 3: BM25 전략

**Files:**
- Modify: `evals/eval_retrieval.py` (tokenize, search_bm25 추가)
- Modify: `tests/test_eval_retrieval.py` (BM25 테스트 추가)

- [ ] **Step 1: 실패 테스트 추가**

`tests/test_eval_retrieval.py` 상단 import에 `tokenize, search_bm25` 추가:

```python
from evals.eval_retrieval import (
    parse_episode_file, load_episodes,
    tokenize, search_bm25,
)
```

파일 끝에 추가:

```python
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
```

- [ ] **Step 2: 실패 확인**

```bash
conda run -n areum pytest tests/test_eval_retrieval.py::test_search_bm25_top_result -v
```

Expected: `ImportError: cannot import name 'tokenize'`

- [ ] **Step 3: eval_retrieval.py에 함수 추가**

`load_episodes` 함수 아래에 추가:

```python
def tokenize(text: str) -> list[str]:
    return [t for t in re.split(r'[\s\W]+', text) if t]


def search_bm25(episodes: list[dict], query: str, top_k: int = 5) -> list[dict]:
    corpus = [tokenize(ep["text"]) for ep in episodes]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(tokenize(query))
    indexed = sorted(range(len(episodes)), key=lambda i: scores[i], reverse=True)
    return [{**episodes[i], "score": float(scores[i])} for i in indexed[:top_k]]
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
conda run -n areum pytest tests/test_eval_retrieval.py -v
```

Expected: 11 passed

- [ ] **Step 5: 커밋**

```bash
git add evals/eval_retrieval.py tests/test_eval_retrieval.py
git commit -m "feat: add BM25 search strategy"
```

---

## Task 4: Embedding 전략

**Files:**
- Modify: `evals/eval_retrieval.py` (cosine_similarity, 캐시, search_embedding 추가)
- Modify: `tests/test_eval_retrieval.py` (Embedding 테스트 추가)

- [ ] **Step 1: 실패 테스트 추가**

import 줄 업데이트:

```python
from evals.eval_retrieval import (
    parse_episode_file, load_episodes,
    tokenize, search_bm25,
    cosine_similarity, search_embedding,
)
```

파일 끝에 추가:

```python
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
```

- [ ] **Step 2: 실패 확인**

```bash
conda run -n areum pytest tests/test_eval_retrieval.py::test_cosine_similarity_identical -v
```

Expected: `ImportError: cannot import name 'cosine_similarity'`

- [ ] **Step 3: eval_retrieval.py에 함수 추가**

`search_bm25` 아래에 추가:

```python
def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def load_embeddings_cache(cache_file: str = EMBEDDINGS_CACHE_FILE) -> dict:
    if Path(cache_file).exists():
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_embeddings_cache(cache: dict, cache_file: str = EMBEDDINGS_CACHE_FILE) -> None:
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def embed_episodes(episodes: list[dict], cache: dict) -> dict:
    missing = [ep for ep in episodes if ep["slug"] not in cache]
    if not missing:
        return cache
    print(f"  임베딩 생성 중... {len(missing)}개 (API 호출)")
    batch_size = 100
    for i in range(0, len(missing), batch_size):
        batch = missing[i:i + batch_size]
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[ep["text"] for ep in batch],
        )
        for ep, emb_obj in zip(batch, response.data):
            cache[ep["slug"]] = emb_obj.embedding
    return cache


def embed_query(query: str) -> list[float]:
    response = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
    return response.data[0].embedding


def search_embedding(
    episodes: list[dict],
    query_embedding: list[float],
    cache: dict,
    top_k: int = 5,
) -> list[dict]:
    scored = [
        (ep, cosine_similarity(query_embedding, cache[ep["slug"]]))
        for ep in episodes
        if ep["slug"] in cache
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [{**ep, "score": score} for ep, score in scored[:top_k]]
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
conda run -n areum pytest tests/test_eval_retrieval.py -v
```

Expected: 17 passed

- [ ] **Step 5: 커밋**

```bash
git add evals/eval_retrieval.py tests/test_eval_retrieval.py
git commit -m "feat: add embedding search strategy with cache"
```

---

## Task 5: Hybrid 전략

**Files:**
- Modify: `evals/eval_retrieval.py` (normalize_scores, search_hybrid 추가)
- Modify: `tests/test_eval_retrieval.py` (Hybrid 테스트 추가)

- [ ] **Step 1: 실패 테스트 추가**

import 줄 업데이트:

```python
from evals.eval_retrieval import (
    parse_episode_file, load_episodes,
    tokenize, search_bm25,
    cosine_similarity, search_embedding,
    normalize_scores, search_hybrid,
)
```

파일 끝에 추가:

```python
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
```

- [ ] **Step 2: 실패 확인**

```bash
conda run -n areum pytest tests/test_eval_retrieval.py::test_normalize_scores_basic -v
```

Expected: `ImportError: cannot import name 'normalize_scores'`

- [ ] **Step 3: eval_retrieval.py에 함수 추가**

`search_embedding` 아래에 추가:

```python
def normalize_scores(scores: list[float]) -> list[float]:
    min_s, max_s = min(scores), max(scores)
    if max_s == min_s:
        return [0.0] * len(scores)
    return [(s - min_s) / (max_s - min_s) for s in scores]


def search_hybrid(
    episodes: list[dict],
    query: str,
    query_embedding: list[float],
    cache: dict,
    alpha: float = 0.5,
    top_k: int = 5,
) -> list[dict]:
    corpus = [tokenize(ep["text"]) for ep in episodes]
    bm25 = BM25Okapi(corpus)
    bm25_raw = list(bm25.get_scores(tokenize(query)))

    emb_raw = [
        cosine_similarity(query_embedding, cache.get(ep["slug"], []))
        for ep in episodes
    ]

    bm25_norm = normalize_scores(bm25_raw)
    emb_norm = normalize_scores(emb_raw)

    combined = [alpha * b + (1 - alpha) * e for b, e in zip(bm25_norm, emb_norm)]
    indexed = sorted(range(len(episodes)), key=lambda i: combined[i], reverse=True)
    return [{**episodes[i], "score": combined[i]} for i in indexed[:top_k]]
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
conda run -n areum pytest tests/test_eval_retrieval.py -v
```

Expected: 23 passed

- [ ] **Step 5: 커밋**

```bash
git add evals/eval_retrieval.py tests/test_eval_retrieval.py
git commit -m "feat: add hybrid search strategy"
```

---

## Task 6: LLM Reranking + to_result

**Files:**
- Modify: `evals/eval_retrieval.py` (rerank_with_llm, to_result 추가)
- Modify: `tests/test_eval_retrieval.py` (LLM, to_result 테스트 추가)

- [ ] **Step 1: 실패 테스트 추가**

import 줄 업데이트:

```python
from evals.eval_retrieval import (
    parse_episode_file, load_episodes,
    tokenize, search_bm25,
    cosine_similarity, search_embedding,
    normalize_scores, search_hybrid,
    rerank_with_llm, to_result,
)
```

파일 끝에 추가:

```python
# --- LLM Reranking ---


def _make_candidates():
    return [
        {**SAMPLE_EPISODES[0], "score": 3.0},
        {**SAMPLE_EPISODES[1], "score": 2.0},
        {**SAMPLE_EPISODES[2], "score": 1.0},
    ]


def test_rerank_with_llm_reorders():
    mock_resp = MagicMock()
    mock_resp.content[0].text = '["b", "a", "c"]'
    with patch("evals.eval_retrieval.anthropic_client.messages.create", return_value=mock_resp):
        results = rerank_with_llm("사랑에 관해", _make_candidates(), top_k=2)
    assert results[0]["slug"] == "b"
    assert results[1]["slug"] == "a"
    assert len(results) == 2


def test_rerank_fills_remaining_when_partial_response():
    mock_resp = MagicMock()
    mock_resp.content[0].text = '["c"]'
    with patch("evals.eval_retrieval.anthropic_client.messages.create", return_value=mock_resp):
        results = rerank_with_llm("두려움", _make_candidates(), top_k=3)
    assert results[0]["slug"] == "c"
    assert len(results) == 3


def test_rerank_handles_markdown_code_block():
    mock_resp = MagicMock()
    mock_resp.content[0].text = '```json\n["a", "b"]\n```'
    with patch("evals.eval_retrieval.anthropic_client.messages.create", return_value=mock_resp):
        results = rerank_with_llm("배신", _make_candidates(), top_k=2)
    assert results[0]["slug"] == "a"


# --- to_result ---


def test_to_result_keys():
    ep = {**SAMPLE_EPISODES[0], "score": 7.123456}
    result = to_result(ep)
    assert set(result.keys()) == {"book", "title", "slug", "score", "step2"}


def test_to_result_score_rounded():
    ep = {**SAMPLE_EPISODES[0], "score": 7.123456}
    result = to_result(ep)
    assert result["score"] == pytest.approx(7.1235, abs=0.001)
```

- [ ] **Step 2: 실패 확인**

```bash
conda run -n areum pytest tests/test_eval_retrieval.py::test_rerank_with_llm_reorders -v
```

Expected: `ImportError: cannot import name 'rerank_with_llm'`

- [ ] **Step 3: eval_retrieval.py에 함수 추가**

`search_hybrid` 아래에 추가:

```python
def rerank_with_llm(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    lines = []
    for ep in candidates:
        lines.append(f"[{ep['slug']}] {ep['book']} — {ep['title']}")
        if ep.get("step2"):
            lines.append(f"  {ep['step2'][:150]}")

    prompt = (
        f"고민: {query}\n\n에피소드:\n" + "\n".join(lines) +
        "\n\n관련도 높은 순서로 slug 목록을 JSON 배열로만 반환하세요."
    )
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system="성경 에피소드를 사용자 고민과의 관련도로 정렬합니다. JSON 배열만 반환하세요.",
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    slugs = json.loads(raw)

    slug_to_ep = {ep["slug"]: ep for ep in candidates}
    reranked = [slug_to_ep[s] for s in slugs if s in slug_to_ep]

    seen = {ep["slug"] for ep in reranked}
    for ep in candidates:
        if ep["slug"] not in seen:
            reranked.append(ep)

    return [
        {**ep, "score": float(len(reranked) - i)}
        for i, ep in enumerate(reranked[:top_k])
    ]


def to_result(ep: dict) -> dict:
    return {
        "book": ep["book"],
        "title": ep["title"],
        "slug": ep["slug"],
        "score": round(ep["score"], 4),
        "step2": ep.get("step2", ""),
    }
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
conda run -n areum pytest tests/test_eval_retrieval.py -v
```

Expected: 31 passed

- [ ] **Step 5: 커밋**

```bash
git add evals/eval_retrieval.py tests/test_eval_retrieval.py
git commit -m "feat: add LLM reranking strategy and to_result helper"
```

---

## Task 7: 쿼리 I/O

**Files:**
- Modify: `evals/eval_retrieval.py` (load_queries, save_queries 추가)
- Modify: `tests/test_eval_retrieval.py` (I/O 테스트 추가)

- [ ] **Step 1: 실패 테스트 추가**

import 줄 업데이트:

```python
from evals.eval_retrieval import (
    parse_episode_file, load_episodes,
    tokenize, search_bm25,
    cosine_similarity, search_embedding,
    normalize_scores, search_hybrid,
    rerank_with_llm, to_result,
    load_queries, save_queries,
)
```

파일 끝에 추가:

```python
# --- Queries I/O ---


def test_save_and_load_queries_roundtrip():
    import tempfile
    queries = [
        {"query": "테스트 쿼리"},
        {"query": "두 번째 쿼리", "results": {"bm25": []}},
    ]
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        path = f.name
    save_queries(queries, path)
    loaded = load_queries(path)
    assert loaded[0]["query"] == "테스트 쿼리"
    assert "results" in loaded[1]
    assert loaded[1]["results"]["bm25"] == []


def test_save_queries_is_utf8():
    import tempfile
    queries = [{"query": "한글 쿼리"}]
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        path = f.name
    save_queries(queries, path)
    raw = Path(path).read_text(encoding="utf-8")
    assert "한글 쿼리" in raw
```

- [ ] **Step 2: 실패 확인**

```bash
conda run -n areum pytest tests/test_eval_retrieval.py::test_save_and_load_queries_roundtrip -v
```

Expected: `ImportError: cannot import name 'load_queries'`

- [ ] **Step 3: eval_retrieval.py에 함수 추가**

`to_result` 아래에 추가:

```python
def load_queries(path: str = QUERIES_FILE) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_queries(queries: list[dict], path: str = QUERIES_FILE) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(queries, f, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
conda run -n areum pytest tests/test_eval_retrieval.py -v
```

Expected: 33 passed

- [ ] **Step 5: 커밋**

```bash
git add evals/eval_retrieval.py tests/test_eval_retrieval.py
git commit -m "feat: add queries I/O helpers"
```

---

## Task 8: 메인 러너 + CLI

**Files:**
- Modify: `evals/eval_retrieval.py` (run_eval, __main__ 블록 추가)

이 태스크는 통합 로직이므로 별도 단위 테스트 없이 구현한다.

- [ ] **Step 1: eval_retrieval.py 파일 끝에 run_eval과 __main__ 블록 추가**

`save_queries` 아래에 추가:

```python
def run_eval(
    strategies: list[str],
    top_k: int,
    alpha: float,
    llm_pool: int,
) -> None:
    print("에피소드 로딩 중...")
    episodes = load_episodes()
    print(f"에피소드 {len(episodes)}개 로딩 완료.\n")

    queries = load_queries()
    cache = {}

    needs_embedding = any(s in strategies for s in ["embedding", "hybrid"])
    if needs_embedding:
        cache = load_embeddings_cache()
        cache = embed_episodes(episodes, cache)
        save_embeddings_cache(cache)

    for i, q in enumerate(queries):
        query_text = q["query"]
        existing = q.get("results", {})
        pending = [s for s in strategies if s not in existing]

        if not pending:
            print(f"[{i+1}/{len(queries)}] 스킵 (완료): {query_text[:40]}")
            continue

        print(f"=== 쿼리 {i+1}/{len(queries)}: \"{query_text}\" ===\n")

        if "results" not in q:
            q["results"] = {}

        query_embedding = None
        if needs_embedding and any(s in pending for s in ["embedding", "hybrid"]):
            query_embedding = embed_query(query_text)

        for strategy in pending:
            if strategy == "bm25":
                results = search_bm25(episodes, query_text, top_k)
            elif strategy == "embedding":
                results = search_embedding(episodes, query_embedding, cache, top_k)
            elif strategy == "hybrid":
                results = search_hybrid(
                    episodes, query_text, query_embedding, cache, alpha, top_k
                )
            elif strategy == "llm":
                candidates = search_bm25(episodes, query_text, llm_pool)
                results = rerank_with_llm(query_text, candidates, top_k)
            else:
                continue

            q["results"][strategy] = [to_result(r) for r in results]

            print(f"[{strategy.upper()}]")
            for j, r in enumerate(results, 1):
                preview = (r.get("step2") or "")[:100].replace("\n", " ")
                print(f"  {j}. {r['book']} — {r['title']} ({r['score']:.3f})")
                if preview:
                    print(f"     {preview}")
            print()

        save_queries(queries)

    print(f"완료. 결과 저장 → {QUERIES_FILE}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="에피소드 검색 전략 비교 평가")
    parser.add_argument(
        "--strategies", nargs="+",
        default=["bm25", "embedding", "hybrid", "llm"],
        choices=["bm25", "embedding", "hybrid", "llm"],
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument("--llm-pool", type=int, default=20)
    args = parser.parse_args()

    run_eval(
        strategies=args.strategies,
        top_k=args.top_k,
        alpha=args.alpha,
        llm_pool=args.llm_pool,
    )
```

- [ ] **Step 2: 전체 테스트 통과 확인**

```bash
conda run -n areum pytest tests/test_eval_retrieval.py -v
```

Expected: 33 passed (신규 단위 테스트 없음, 기존 모두 통과)

- [ ] **Step 3: 커밋**

```bash
git add evals/eval_retrieval.py
git commit -m "feat: add main runner and CLI for eval_retrieval"
```

---

## Task 9: BM25 스모크 실행으로 검증

실제 에피소드 DB와 BM25 전략으로 end-to-end 동작을 확인한다. (API 비용 없음)

- [ ] **Step 1: BM25만 실행**

```bash
conda run -n areum python evals/eval_retrieval.py --strategies bm25 --top-k 3
```

Expected 출력 예시:
```
에피소드 NNN개 로딩 완료.

=== 쿼리 1/10: "회사에서 믿었던 동료한테 배신당했어요." ===

[BM25]
  1. 마태복음 — ... (12.340)
     ...
  2. ...
  3. ...
...
완료. 결과 저장 → evals/eval_queries.json
```

- [ ] **Step 2: eval_queries.json에 bm25 결과 확인**

```bash
conda run -n areum python -c "
import json
with open('evals/eval_queries.json', encoding='utf-8') as f:
    qs = json.load(f)
for q in qs:
    print(q['query'][:30], '->', len(q.get('results', {}).get('bm25', [])), 'results')
"
```

Expected: 10줄, 각 줄에 `-> 3 results`

- [ ] **Step 3: 최종 커밋**

```bash
git add evals/eval_queries.json
git commit -m "eval: run BM25 strategy on 10 queries"
```
