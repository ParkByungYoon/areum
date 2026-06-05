"""BM25 기반 에피소드 매칭"""
import json
from rank_bm25 import BM25Okapi

GOSPEL_EPISODES_PATH = "data/gospel_episodes.json"


def _tokenize(text: str) -> list[str]:
    return text.split()


class EpisodeMatcher:
    def __init__(self, episodes_path: str = GOSPEL_EPISODES_PATH):
        with open(episodes_path, encoding="utf-8") as f:
            self.episodes = json.load(f)

        corpus = []
        for ep in self.episodes:
            doc = " ".join(filter(None, [
                ep["subtitle"],
                ep.get("situation", ""),
                ep.get("meaning", ""),
            ]))
            corpus.append(_tokenize(doc))
        self._bm25 = BM25Okapi(corpus)

    def match(self, query: str, top_n: int = 3) -> list[dict]:
        """쿼리 → 상위 top_n 에피소드 반환 (situation+meaning 기반)"""
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_n]
        return [
            {**self.episodes[i], "score": scores[i], "best_passage_idx": 0}
            for i in ranked
        ]
