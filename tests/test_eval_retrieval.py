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
