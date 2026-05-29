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
