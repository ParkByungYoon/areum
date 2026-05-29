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


def tokenize(text: str) -> list[str]:
    return [t for t in re.split(r'[\s\W]+', text) if t]


def search_bm25(episodes: list[dict], query: str, top_k: int = 5) -> list[dict]:
    corpus = [tokenize(ep["text"]) for ep in episodes]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(tokenize(query))
    indexed = sorted(range(len(episodes)), key=lambda i: scores[i], reverse=True)
    return [{**episodes[i], "score": float(scores[i])} for i in indexed[:top_k]]


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
        cosine_similarity(query_embedding, cache[ep["slug"]])
        if ep["slug"] in cache
        else 0.0
        for ep in episodes
    ]

    bm25_norm = normalize_scores(bm25_raw)
    emb_norm = normalize_scores(emb_raw)

    combined = [alpha * b + (1 - alpha) * e for b, e in zip(bm25_norm, emb_norm)]
    indexed = sorted(range(len(episodes)), key=lambda i: combined[i], reverse=True)
    return [{**episodes[i], "score": combined[i]} for i in indexed[:top_k]]


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
    try:
        slugs = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  [LLM] JSON 파싱 실패, 원래 순서 유지: {raw[:80]}")
        return [{**ep, "score": float(len(candidates) - i)} for i, ep in enumerate(candidates[:top_k])]

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


def load_queries(path: str = QUERIES_FILE) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_queries(queries: list[dict], path: str = QUERIES_FILE) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(queries, f, ensure_ascii=False, indent=2)


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
