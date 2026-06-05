import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.deps import get_matcher, get_db_path
from core.matcher import EpisodeMatcher
from storage.prayer_store import init_db, save_prayer

EPISODES = [
    {
        "subtitle": "오천 명을 먹이심",
        "situation": "광야에서 오천 명을 먹이신 이야기",
        "meaning": "하나님의 풍성한 공급",
        "passages": [
            {
                "book": "마태복음",
                "chapter_start": 14, "verse_start": 13,
                "chapter_end": 14, "verse_end": 21,
                "verses": [{"chapter": 14, "verse": 13, "text": "광야로 가셨다"}],
            }
        ],
    },
    {
        "subtitle": "탕자의 비유",
        "situation": "아버지께로 돌아온 아들 이야기",
        "meaning": "돌아온 자를 기다리는 아버지의 사랑",
        "passages": [
            {
                "book": "누가복음",
                "chapter_start": 15, "verse_start": 11,
                "chapter_end": 15, "verse_end": 32,
                "verses": [{"chapter": 15, "verse": 11, "text": "아버지와 두 아들"}],
            }
        ],
    },
    {
        "subtitle": "겟세마네의 기도",
        "situation": "십자가 전날 밤 예수께서 홀로 기도하신 이야기",
        "meaning": "고난 앞에서의 순종",
        "passages": [
            {
                "book": "마태복음",
                "chapter_start": 26, "verse_start": 36,
                "chapter_end": 26, "verse_end": 46,
                "verses": [{"chapter": 26, "verse": 36, "text": "겟세마네라 하는 곳에"}],
            }
        ],
    },
]


@pytest.fixture()
def client(tmp_path):
    ep_file = tmp_path / "episodes.json"
    ep_file.write_text(json.dumps(EPISODES, ensure_ascii=False), encoding="utf-8")
    db_file = str(tmp_path / "prayers.db")
    init_db(db_file)

    app.dependency_overrides[get_matcher] = lambda: EpisodeMatcher(str(ep_file))
    app.dependency_overrides[get_db_path] = lambda: db_file
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- /api/match ---

def test_match_returns_episodes(client):
    res = client.post("/api/match", json={"concern": "배고프고 힘들어요"})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "episode_id" in data[0]
    assert "subtitle" in data[0]
    assert "situation" in data[0]


def test_match_returns_at_most_3(client):
    res = client.post("/api/match", json={"concern": "아버지"})
    assert res.status_code == 200
    assert len(res.json()) <= 3


def test_match_empty_concern_returns_422(client):
    res = client.post("/api/match", json={"concern": ""})
    assert res.status_code == 422


# --- /api/episode/{episode_id} ---

def test_get_episode_returns_detail(client):
    res = client.get("/api/episode/탕자의 비유")
    assert res.status_code == 200
    data = res.json()
    assert data["subtitle"] == "탕자의 비유"
    assert "passages" in data
    assert "meaning" in data


def test_get_episode_not_found_returns_404(client):
    res = client.get("/api/episode/존재하지않는에피소드")
    assert res.status_code == 404


# --- /api/prayer ---

def test_post_prayer_returns_record(client):
    res = client.post("/api/prayer", json={
        "user_id": "지훈",
        "concern": "외로워요",
        "episode_id": "탕자의 비유",
        "subtitle": "탕자의 비유",
        "passage_ref": "눅 15:11-32",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == "지훈"
    assert data["episode_id"] == "탕자의 비유"


# --- /api/connection ---

def test_post_connection_returns_null_when_no_history(client):
    res = client.post("/api/connection", json={
        "user_id": "지훈",
        "concern": "외로워요",
        "episode_id": "탕자의 비유",
    })
    assert res.status_code == 200
    assert res.json() is None


def test_post_connection_returns_same_episode(client, tmp_path):
    db_file = str(tmp_path / "prayers.db")
    save_prayer("지훈", "인간관계가 힘들다", "탕자의 비유", "탕자의 비유", "눅 15:11-32", db_file)

    res = client.post("/api/connection", json={
        "user_id": "지훈",
        "concern": "또 힘들다",
        "episode_id": "탕자의 비유",
    })
    assert res.status_code == 200
    data = res.json()
    assert data is not None
    assert data["type"] == "same_episode"
