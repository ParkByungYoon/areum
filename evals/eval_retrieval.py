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
