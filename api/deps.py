import os
from functools import lru_cache
from core.matcher import EpisodeMatcher


@lru_cache(maxsize=1)
def _load_matcher(path: str) -> EpisodeMatcher:
    return EpisodeMatcher(path)


def get_matcher() -> EpisodeMatcher:
    return _load_matcher(os.getenv("EPISODES_PATH", "data/gospel_episodes.json"))


def get_db_path() -> str:
    return os.getenv("DB_PATH", "prayers.db")
