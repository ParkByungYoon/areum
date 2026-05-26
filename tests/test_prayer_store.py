import sys
import os
import tempfile
sys.path.insert(0, ".")
from storage.prayer_store import save_prayer, load_prayers

SAMPLE_VERSE = {
    "book": "누가복음", "chapter": 15, "verse": 20,
    "text": "아들이 아직도 먼 거리에 있을 때에...",
}


def test_save_creates_file():
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
        path = f.name
    os.unlink(path)
    try:
        save_prayer("외로워요", SAMPLE_VERSE, "연결 메시지", path)
        assert os.path.exists(path)
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_save_contains_concern():
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        path = f.name
    try:
        save_prayer("외로워요", SAMPLE_VERSE, "연결 메시지", path)
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        assert "외로워요" in content
    finally:
        os.unlink(path)


def test_save_contains_verse_ref():
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        path = f.name
    try:
        save_prayer("외로워요", SAMPLE_VERSE, "연결 메시지", path)
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        assert "누가복음 15:20" in content
    finally:
        os.unlink(path)


def test_saves_accumulate():
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        path = f.name
    try:
        save_prayer("첫 번째 기도", SAMPLE_VERSE, "연결1", path)
        save_prayer("두 번째 기도", SAMPLE_VERSE, "연결2", path)
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        assert "첫 번째 기도" in content
        assert "두 번째 기도" in content
    finally:
        os.unlink(path)


def test_load_returns_empty_string_if_no_file():
    result = load_prayers("nonexistent_file_xyz.md")
    assert result == ""
