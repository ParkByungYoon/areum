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


from unittest.mock import patch, MagicMock
from data.episode_pipeline import run_step1, run_step2, call_with_retry


def test_run_step1_calls_haiku():
    mock_resp = MagicMock()
    mock_resp.content[0].text = "  상황 요약  "
    with patch("data.episode_pipeline.client.messages.create", return_value=mock_resp) as mock_create:
        result = run_step1(SAMPLE_EPISODE, "1:1 태초에...")
    assert result == "상황 요약"
    assert mock_create.call_args.kwargs["model"] == "claude-haiku-4-5-20251001"


def test_run_step2_calls_sonnet():
    mock_resp = MagicMock()
    mock_resp.content[0].text = "  의미 해석  "
    with patch("data.episode_pipeline.client.messages.create", return_value=mock_resp) as mock_create:
        result = run_step2(SAMPLE_EPISODE, "상황 요약")
    assert result == "의미 해석"
    assert mock_create.call_args.kwargs["model"] == "claude-sonnet-4-6"


def test_call_with_retry_succeeds_first_try():
    fn = MagicMock(return_value="ok")
    assert call_with_retry(fn) == "ok"
    assert fn.call_count == 1


def test_call_with_retry_retries_on_failure():
    fn = MagicMock(side_effect=[Exception("fail"), Exception("fail"), "ok"])
    with patch("data.episode_pipeline.time.sleep"):
        result = call_with_retry(fn, retries=3)
    assert result == "ok"
    assert fn.call_count == 3


def test_call_with_retry_raises_after_max():
    fn = MagicMock(side_effect=Exception("always fails"))
    with patch("data.episode_pipeline.time.sleep"):
        try:
            call_with_retry(fn, retries=3)
            assert False, "Should have raised"
        except Exception as e:
            assert str(e) == "always fails"
    assert fn.call_count == 3
