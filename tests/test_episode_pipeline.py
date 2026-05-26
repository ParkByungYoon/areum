import sys
sys.path.insert(0, ".")
from data.episode_pipeline import load_bible, extract_verses


def test_load_bible_returns_dict():
    bible = load_bible("bible.json")
    assert isinstance(bible, dict)


def test_load_bible_contains_nt_books():
    bible = load_bible("bible.json")
    assert "마태복음" in bible
    assert "요한계시록" in bible


def test_load_bible_verse_structure():
    bible = load_bible("bible.json")
    v = bible["마태복음"][0]
    assert v["chapter"] == 1
    assert v["verse"] == 1
    assert isinstance(v["text"], str)
    assert len(v["text"]) > 0


def test_extract_verses_single_chapter():
    bible = load_bible("bible.json")
    text = extract_verses(bible, "마태복음", 1, 1, 1, 3)
    assert "1:1" in text
    assert "1:2" in text
    assert "1:3" in text
    assert "1:4" not in text


def test_extract_verses_multi_chapter():
    bible = load_bible("bible.json")
    text = extract_verses(bible, "마태복음", 1, 25, 2, 2)
    assert "1:25" in text
    assert "2:1" in text
    assert "2:2" in text
    assert "2:3" not in text


def test_extract_verses_invalid_book():
    bible = load_bible("bible.json")
    assert extract_verses(bible, "존재하지않는책", 1, 1, 1, 5) == ""


import tempfile
from pathlib import Path
from data.episode_pipeline import save_episode, update_step2, needs_step1, needs_step2

SAMPLE_EPISODE = {
    "book": "마태복음",
    "title": "예수의 계보",
    "start_ch": 1, "start_v": 1,
    "end_ch": 1, "end_v": 17,
    "slug": "001_예수의_계보",
}


def test_save_episode_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        save_episode(tmpdir, SAMPLE_EPISODE, "예수의 계보 요약입니다.")
        fp = Path(tmpdir) / "마태복음" / "001_예수의_계보.md"
        assert fp.exists()


def test_save_episode_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        save_episode(tmpdir, SAMPLE_EPISODE, "예수의 계보 요약입니다.")
        fp = Path(tmpdir) / "마태복음" / "001_예수의_계보.md"
        content = fp.read_text(encoding="utf-8")
        assert "# 예수의 계보" in content
        assert "마태복음 1:1-1:17" in content
        assert "예수의 계보 요약입니다." in content
        assert "## 2-step (의미)" in content


def test_save_episode_step2_initially_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        save_episode(tmpdir, SAMPLE_EPISODE, "요약")
        fp = Path(tmpdir) / "마태복음" / "001_예수의_계보.md"
        content = fp.read_text(encoding="utf-8")
        marker = "## 2-step (의미)\n"
        idx = content.find(marker)
        assert content[idx + len(marker):].strip() == ""


def test_update_step2_fills_section():
    with tempfile.TemporaryDirectory() as tmpdir:
        save_episode(tmpdir, SAMPLE_EPISODE, "요약")
        fp = Path(tmpdir) / "마태복음" / "001_예수의_계보.md"
        update_step2(str(fp), "의미 해석입니다.")
        assert "의미 해석입니다." in fp.read_text(encoding="utf-8")


def test_update_step2_does_not_overwrite_step1():
    with tempfile.TemporaryDirectory() as tmpdir:
        save_episode(tmpdir, SAMPLE_EPISODE, "상황 요약")
        fp = Path(tmpdir) / "마태복음" / "001_예수의_계보.md"
        update_step2(str(fp), "의미 해석")
        content = fp.read_text(encoding="utf-8")
        assert "상황 요약" in content
        assert "의미 해석" in content


def test_needs_step1_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        assert needs_step1(tmpdir, SAMPLE_EPISODE) is True


def test_needs_step1_file_exists():
    with tempfile.TemporaryDirectory() as tmpdir:
        save_episode(tmpdir, SAMPLE_EPISODE, "요약")
        assert needs_step1(tmpdir, SAMPLE_EPISODE) is False


def test_needs_step2_empty_section():
    with tempfile.TemporaryDirectory() as tmpdir:
        save_episode(tmpdir, SAMPLE_EPISODE, "요약")
        assert needs_step2(tmpdir, SAMPLE_EPISODE) is True


def test_needs_step2_filled_section():
    with tempfile.TemporaryDirectory() as tmpdir:
        save_episode(tmpdir, SAMPLE_EPISODE, "요약")
        fp = Path(tmpdir) / "마태복음" / "001_예수의_계보.md"
        update_step2(str(fp), "의미 해석")
        assert needs_step2(tmpdir, SAMPLE_EPISODE) is False


def test_needs_step2_no_file_returns_false():
    with tempfile.TemporaryDirectory() as tmpdir:
        assert needs_step2(tmpdir, SAMPLE_EPISODE) is False
