# 에피소드 DB 파이프라인 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** subtitle.md 소제목을 경계로 bible.json 원문을 추출하고 Claude API 2-step 처리하여 신약 852개 에피소드를 책별 마크다운 파일로 저장하는 파이프라인을 구축한다.

**Architecture:** `parse_subtitles.py`가 subtitle.md 파싱 + 절범위 계산을 담당하고, `episode_pipeline.py`가 원문 추출 + Claude API 호출 + 파일 저장을 담당한다. `--step 1`은 Haiku로 상황 요약, `--step 2`는 Sonnet으로 의미 해석을 생성하며, 에피소드마다 즉시 저장하여 중단 후 resume이 가능하다.

**Tech Stack:** Python 3.11+, anthropic SDK, python-dotenv, pytest

**Spec:** `docs/superpowers/specs/2026-05-27-episode-pipeline-design.md`

---

## File Map

```
data/
├── parse_subtitles.py        # 신규 — subtitle.md 파서 + 절범위 계산
├── episode_pipeline.py       # 신규 — 메인 파이프라인 --step 1/2
└── episodes/                 # 신규 (생성됨, gitignore)
    ├── 마태복음/
    │   ├── 001_예수의_계보.md
    │   └── ...
    └── ...
tests/
├── test_parse_subtitles.py   # 신규
└── test_episode_pipeline.py  # 신규
.gitignore                    # 수정 — data/episodes/ 추가
```

---

## Task 1: Subtitle Parser

**Files:**
- Create: `data/parse_subtitles.py`
- Test: `tests/test_parse_subtitles.py`

- [ ] **Step 1: Write the failing test**

`tests/test_parse_subtitles.py`:
```python
import sys
import json
sys.path.insert(0, ".")
from data.parse_subtitles import parse_subtitles, compute_ranges, BOOK_ABBR


def test_returns_list():
    episodes = parse_subtitles("subtitle.md")
    assert isinstance(episodes, list)


def test_total_episode_count():
    episodes = parse_subtitles("subtitle.md")
    assert len(episodes) == 852


def test_first_episode_structure():
    episodes = parse_subtitles("subtitle.md")
    ep = episodes[0]
    assert ep["book"] == "마태복음"
    assert ep["title"] == "예수의 계보"
    assert ep["start_ch"] == 1
    assert ep["start_v"] == 1
    assert "slug" in ep


def test_book_abbr_resolved():
    episodes = parse_subtitles("subtitle.md")
    books = {ep["book"] for ep in episodes}
    assert "마태복음" in books
    assert "요한계시록" in books
    assert "마" not in books


def test_slug_format_first_episode():
    episodes = parse_subtitles("subtitle.md")
    assert episodes[0]["slug"].startswith("001_")


def test_per_book_slug_index_resets():
    episodes = parse_subtitles("subtitle.md")
    mark_start = next(i for i, ep in enumerate(episodes) if ep["book"] == "마가복음")
    assert episodes[mark_start]["slug"].startswith("001_")


def _minimal_bible():
    with open("bible.json", encoding="utf-8") as f:
        raw = json.load(f)
    bible = {}
    for book in raw:
        name = book["korean"]
        verses = []
        for ch in book["chapters"]:
            for v in ch["verses"]:
                verses.append({"chapter": int(v["chapterNum"]), "verse": int(v["verseNum"])})
        bible[name] = verses
    return bible


def test_compute_ranges_middle_episode():
    episodes = parse_subtitles("subtitle.md")
    bible = _minimal_bible()
    ranged = compute_ranges(episodes, bible)
    # 예수의 계보 [마 1:1], 다음은 예수의 탄생 [마 1:18] → 끝절 1:17
    ep = next(ep for ep in ranged if ep["book"] == "마태복음" and ep["start_ch"] == 1 and ep["start_v"] == 1)
    assert ep["end_ch"] == 1
    assert ep["end_v"] == 17


def test_compute_ranges_chapter_boundary():
    episodes = parse_subtitles("subtitle.md")
    bible = _minimal_bible()
    ranged = compute_ranges(episodes, bible)
    # 죄인인 한 여인이 예수께 향유를 붓다 [눅 7:36], 다음은 여인들이 예수의 활동을 돕다 [눅 8:1]
    ep = next(ep for ep in ranged if ep["book"] == "누가복음" and ep["start_ch"] == 7 and ep["start_v"] == 36)
    assert ep["end_ch"] == 7
    assert ep["end_v"] == 50


def test_compute_ranges_last_episode_in_book():
    episodes = parse_subtitles("subtitle.md")
    bible = _minimal_bible()
    ranged = compute_ranges(episodes, bible)
    # 마태복음 마지막 에피소드는 제자들의 사명 [마 28:16] → 끝은 28:20
    last_matt = next(ep for ep in reversed(ranged) if ep["book"] == "마태복음")
    assert last_matt["end_ch"] == 28
    assert last_matt["end_v"] == 20
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n areum pytest tests/test_parse_subtitles.py -v
```

Expected: `ModuleNotFoundError: No module named 'data.parse_subtitles'`

- [ ] **Step 3: Implement `data/parse_subtitles.py`**

```python
import re

BOOK_ABBR = {
    "마": "마태복음", "막": "마가복음", "눅": "누가복음", "요": "요한복음",
    "행": "사도행전", "롬": "로마서", "고전": "고린도전서", "고후": "고린도후서",
    "갈": "갈라디아서", "엡": "에베소서", "빌": "빌립보서", "골": "골로새서",
    "살전": "데살로니가전서", "살후": "데살로니가후서", "딤전": "디모데전서",
    "딤후": "디모데후서", "딛": "디도서", "몬": "빌레몬서", "히": "히브리서",
    "약": "야고보서", "벧전": "베드로전서", "벧후": "베드로후서",
    "요1": "요한1서", "요2": "요한2서", "요3": "요한3서", "유": "유다서",
    "계": "요한계시록",
}


def parse_subtitles(path: str = "subtitle.md") -> list[dict]:
    episodes = []
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if "[" not in line:
            continue
        match = re.match(r'^(.+?)\s+\[(\S+)\s+(\d+):(\d+)\]$', line)
        if not match:
            continue
        title = match.group(1)
        abbr = match.group(2)
        chapter = int(match.group(3))
        verse = int(match.group(4))
        book = BOOK_ABBR.get(abbr, abbr)
        episodes.append({"book": book, "title": title, "start_ch": chapter, "start_v": verse})

    book_counters: dict[str, int] = {}
    for ep in episodes:
        book = ep["book"]
        book_counters[book] = book_counters.get(book, 0) + 1
        idx = book_counters[book]
        safe_title = re.sub(r'[^\w]', '_', ep["title"], flags=re.UNICODE).strip('_')
        ep["slug"] = f"{idx:03d}_{safe_title}"

    return episodes


def compute_ranges(episodes: list[dict], bible: dict) -> list[dict]:
    result = []
    for i, ep in enumerate(episodes):
        ep = dict(ep)
        book = ep["book"]

        next_ep = next(
            (episodes[j] for j in range(i + 1, len(episodes)) if episodes[j]["book"] == book),
            None,
        )

        if next_ep:
            if next_ep["start_v"] > 1:
                ep["end_ch"] = next_ep["start_ch"]
                ep["end_v"] = next_ep["start_v"] - 1
            else:
                prev_ch = next_ep["start_ch"] - 1
                book_verses = bible.get(book, [])
                last_v = max(
                    (v["verse"] for v in book_verses if v["chapter"] == prev_ch),
                    default=1,
                )
                ep["end_ch"] = prev_ch
                ep["end_v"] = last_v
        else:
            book_verses = bible.get(book, [])
            if book_verses:
                last = max(book_verses, key=lambda v: (v["chapter"], v["verse"]))
                ep["end_ch"] = last["chapter"]
                ep["end_v"] = last["verse"]
            else:
                ep["end_ch"] = ep["start_ch"]
                ep["end_v"] = ep["start_v"]

        result.append(ep)
    return result
```

- [ ] **Step 4: Run test to verify it passes**

```bash
conda run -n areum pytest tests/test_parse_subtitles.py -v
```

Expected: All 9 tests PASS

- [ ] **Step 5: Verify bible.json book name compatibility**

```bash
conda run -n areum python -c "
import json
from data.parse_subtitles import parse_subtitles, BOOK_ABBR

with open('bible.json', encoding='utf-8') as f:
    raw = json.load(f)
bible_names = {b['korean'] for b in raw}
episodes = parse_subtitles('subtitle.md')
episode_books = {ep['book'] for ep in episodes}
missing = episode_books - bible_names
if missing:
    print('불일치:', missing)
else:
    print('모든 책명 일치 확인됨')
"
```

Expected: `모든 책명 일치 확인됨`

불일치가 있으면 `BOOK_ABBR` 값을 bible.json `korean` 필드에 맞게 수정한다.

- [ ] **Step 6: Commit**

```bash
git add data/parse_subtitles.py tests/test_parse_subtitles.py
git commit -m "feat: subtitle parser with verse range computation"
```

---

## Task 2: Bible Loader & Verse Extractor

**Files:**
- Create: `data/episode_pipeline.py`
- Test: `tests/test_episode_pipeline.py`

- [ ] **Step 1: Write the failing test**

`tests/test_episode_pipeline.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n areum pytest tests/test_episode_pipeline.py -v
```

Expected: `ModuleNotFoundError: No module named 'data.episode_pipeline'`

- [ ] **Step 3: Implement `data/episode_pipeline.py` (bible utilities only)**

```python
import json
import os
import time
import argparse
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from data.parse_subtitles import parse_subtitles, compute_ranges

load_dotenv()
client = anthropic.Anthropic()

STEP1_SYSTEM = """성경 에피소드의 등장인물, 사건, 배경을 3-5문장으로 요약하세요.
무엇이 일어났는가, 누가, 왜, 어떤 상황에서. 해석 없이 사실만."""

STEP2_SYSTEM = """아래 에피소드 상황 요약을 바탕으로 신학적·감정적 의미를 3-5문장으로
추출하세요. 이 에피소드의 핵심이 무엇인지, 어떤 사람의 어떤 상황에
닿을 수 있는지. AI가 해석을 지시하지 않고 연결점만 제시한다."""


def load_bible(path: str = "bible.json") -> dict:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    bible = {}
    for book in raw:
        name = book["korean"]
        verses = []
        for chapter in book["chapters"]:
            for v in chapter["verses"]:
                verses.append({
                    "chapter": int(v["chapterNum"]),
                    "verse": int(v["verseNum"]),
                    "text": v["verse"],
                })
        bible[name] = verses
    return bible


def extract_verses(bible: dict, book: str, start_ch: int, start_v: int, end_ch: int, end_v: int) -> str:
    selected = [
        f"{v['chapter']}:{v['verse']} {v['text']}"
        for v in bible.get(book, [])
        if (v["chapter"], v["verse"]) >= (start_ch, start_v)
        and (v["chapter"], v["verse"]) <= (end_ch, end_v)
    ]
    return "\n".join(selected)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
conda run -n areum pytest tests/test_episode_pipeline.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add data/episode_pipeline.py tests/test_episode_pipeline.py
git commit -m "feat: bible loader and verse extractor"
```

---

## Task 3: File I/O Functions

**Files:**
- Modify: `data/episode_pipeline.py`
- Modify: `tests/test_episode_pipeline.py`

- [ ] **Step 1: Add failing tests to `tests/test_episode_pipeline.py`**

파일 끝에 추가:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n areum pytest tests/test_episode_pipeline.py -v -k "save or update or needs"
```

Expected: `ImportError` (functions not yet defined)

- [ ] **Step 3: Add file I/O functions to `data/episode_pipeline.py`**

`extract_verses` 함수 아래에 추가:

```python
def episode_filepath(output_dir: str, episode: dict) -> Path:
    return Path(output_dir) / episode["book"] / f"{episode['slug']}.md"


def save_episode(output_dir: str, episode: dict, step1_text: str):
    fp = episode_filepath(output_dir, episode)
    fp.parent.mkdir(parents=True, exist_ok=True)
    ref = f"{episode['book']} {episode['start_ch']}:{episode['start_v']}-{episode['end_ch']}:{episode['end_v']}"
    content = (
        f"# {episode['title']}\n"
        f"**범위**: {ref}\n\n"
        f"## 1-step (상황)\n{step1_text}\n\n"
        f"## 2-step (의미)\n"
    )
    fp.write_text(content, encoding="utf-8")


def update_step2(filepath: str, step2_text: str):
    fp = Path(filepath)
    content = fp.read_text(encoding="utf-8")
    marker = "## 2-step (의미)\n"
    idx = content.find(marker)
    if idx == -1:
        return
    fp.write_text(content[:idx + len(marker)] + step2_text + "\n", encoding="utf-8")


def needs_step1(output_dir: str, episode: dict) -> bool:
    return not episode_filepath(output_dir, episode).exists()


def needs_step2(output_dir: str, episode: dict) -> bool:
    fp = episode_filepath(output_dir, episode)
    if not fp.exists():
        return False
    content = fp.read_text(encoding="utf-8")
    marker = "## 2-step (의미)\n"
    idx = content.find(marker)
    if idx == -1:
        return False
    return content[idx + len(marker):].strip() == ""
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
conda run -n areum pytest tests/test_episode_pipeline.py -v
```

Expected: All 16 tests PASS

- [ ] **Step 5: Commit**

```bash
git add data/episode_pipeline.py tests/test_episode_pipeline.py
git commit -m "feat: episode file I/O functions"
```

---

## Task 4: API Call Functions

**Files:**
- Modify: `data/episode_pipeline.py`
- Modify: `tests/test_episode_pipeline.py`

- [ ] **Step 1: Add failing tests to `tests/test_episode_pipeline.py`**

파일 끝에 추가:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n areum pytest tests/test_episode_pipeline.py -v -k "step1 or step2 or retry"
```

Expected: `ImportError` (functions not yet defined)

- [ ] **Step 3: Add API functions to `data/episode_pipeline.py`**

`needs_step2` 함수 아래에 추가:

```python
def call_with_retry(fn, retries: int = 3):
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if attempt < retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  재시도 {attempt + 1}/{retries - 1} ({wait}s 대기): {e}")
                time.sleep(wait)
            else:
                raise


def run_step1(episode: dict, verses: str) -> str:
    ref = f"{episode['book']} {episode['start_ch']}:{episode['start_v']}-{episode['end_ch']}:{episode['end_v']}"
    user_msg = f"제목: {episode['title']}\n범위: {ref}\n원문:\n{verses}"

    def call():
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=STEP1_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        return response.content[0].text.strip()

    return call_with_retry(call)


def run_step2(episode: dict, step1_text: str) -> str:
    user_msg = f"제목: {episode['title']}\n상황 요약:\n{step1_text}"

    def call():
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=STEP2_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        return response.content[0].text.strip()

    return call_with_retry(call)
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
conda run -n areum pytest tests/test_episode_pipeline.py -v
```

Expected: All 21 tests PASS

- [ ] **Step 5: Commit**

```bash
git add data/episode_pipeline.py tests/test_episode_pipeline.py
git commit -m "feat: episode pipeline API call functions"
```

---

## Task 5: Orchestration & CLI

**Files:**
- Modify: `data/episode_pipeline.py`
- Modify: `.gitignore`

- [ ] **Step 1: Add `data/episodes/` to `.gitignore`**

`.gitignore` 파일에서 `data/luke_raw.json` 아래에 추가:
```
data/episodes/
```

- [ ] **Step 2: Add orchestration functions to `data/episode_pipeline.py`**

파일 끝에 추가:

```python
def _read_step1_from_file(fp: Path) -> str:
    content = fp.read_text(encoding="utf-8")
    marker = "## 1-step (상황)\n"
    idx = content.find(marker)
    if idx == -1:
        return ""
    end = content.find("\n## ", idx + len(marker))
    return content[idx + len(marker):end].strip() if end != -1 else content[idx + len(marker):].strip()


def main_step1(episodes: list[dict], bible: dict, output_dir: str, book_filter: str = None):
    targets = [
        ep for ep in episodes
        if (book_filter is None or ep["book"] == book_filter) and needs_step1(output_dir, ep)
    ]
    print(f"Step 1: {len(targets)}개 에피소드 처리 예정")
    for i, ep in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {ep['book']} — {ep['title']}")
        verses = extract_verses(bible, ep["book"], ep["start_ch"], ep["start_v"], ep["end_ch"], ep["end_v"])
        try:
            step1 = run_step1(ep, verses)
            save_episode(output_dir, ep, step1)
        except Exception as e:
            print(f"  오류 (건너뜀): {e}")
    print("Step 1 완료.")


def main_step2(episodes: list[dict], output_dir: str, book_filter: str = None):
    targets = [
        ep for ep in episodes
        if (book_filter is None or ep["book"] == book_filter) and needs_step2(output_dir, ep)
    ]
    print(f"Step 2: {len(targets)}개 에피소드 처리 예정")
    for i, ep in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {ep['book']} — {ep['title']}")
        fp = episode_filepath(output_dir, ep)
        step1_text = _read_step1_from_file(fp)
        try:
            step2 = run_step2(ep, step1_text)
            update_step2(str(fp), step2)
        except Exception as e:
            print(f"  오류 (건너뜀): {e}")
    print("Step 2 완료.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="에피소드 DB 파이프라인")
    parser.add_argument("--step", type=int, choices=[1, 2], required=True)
    parser.add_argument("--book", type=str, default=None, help="특정 책만 처리 (예: 마태복음)")
    parser.add_argument("--output", type=str, default="data/episodes")
    args = parser.parse_args()

    episodes_raw = parse_subtitles("subtitle.md")
    bible = load_bible("bible.json")
    episodes = compute_ranges(episodes_raw, bible)

    if args.step == 1:
        main_step1(episodes, bible, args.output, args.book)
    else:
        main_step2(episodes, args.output, args.book)
```

- [ ] **Step 3: Run full test suite**

```bash
conda run -n areum pytest tests/ -v
```

Expected: All tests PASS

- [ ] **Step 4: Smoke test — 마태복음 Step 1 (3개만)**

```bash
conda run -n areum python -c "
import sys; sys.path.insert(0, '.')
from data.parse_subtitles import parse_subtitles, compute_ranges
from data.episode_pipeline import load_bible, main_step1
episodes_raw = parse_subtitles('subtitle.md')
bible = load_bible('bible.json')
episodes = compute_ranges(episodes_raw, bible)
matt3 = [ep for ep in episodes if ep['book'] == '마태복음'][:3]
main_step1(matt3, bible, 'data/episodes')
"
```

Expected:
```
Step 1: 3개 에피소드 처리 예정
[1/3] 마태복음 — 예수의 계보
[2/3] 마태복음 — 예수의 탄생
[3/3] 마태복음 — 동방박사들이 아기에게 경배하러 오다
Step 1 완료.
```

- [ ] **Step 5: Verify output file**

```bash
conda run -n areum python -c "
from pathlib import Path
print(Path('data/episodes/마태복음/001_예수의_계보.md').read_text(encoding='utf-8'))
"
```

Expected: 제목, 범위, 1-step 상황 요약 포함. `## 2-step (의미)` 섹션은 비어 있음.

- [ ] **Step 6: Smoke test — 마태복음 Step 2 (3개)**

```bash
conda run -n areum python -c "
import sys; sys.path.insert(0, '.')
from data.parse_subtitles import parse_subtitles, compute_ranges
from data.episode_pipeline import load_bible, main_step2
episodes_raw = parse_subtitles('subtitle.md')
bible = load_bible('bible.json')
episodes = compute_ranges(episodes_raw, bible)
matt3 = [ep for ep in episodes if ep['book'] == '마태복음'][:3]
main_step2(matt3, 'data/episodes')
"
```

Expected:
```
Step 2: 3개 에피소드 처리 예정
[1/3] 마태복음 — 예수의 계보
[2/3] 마태복음 — 예수의 탄생
[3/3] 마태복음 — 동방박사들이 아기에게 경배하러 오다
Step 2 완료.
```

- [ ] **Step 7: Verify Step 2 was added**

```bash
conda run -n areum python -c "
from pathlib import Path
print(Path('data/episodes/마태복음/001_예수의_계보.md').read_text(encoding='utf-8'))
"
```

Expected: `## 2-step (의미)` 섹션에 내용이 채워져 있음.

- [ ] **Step 8: Commit**

```bash
git add data/episode_pipeline.py .gitignore
git commit -m "feat: episode pipeline orchestration and CLI"
```

---

## Self-Review

| 스펙 요구사항 | Task |
|---|---|
| subtitle.md 파싱 (책, 제목, 시작절, slug) | Task 1 — `parse_subtitles()` |
| 절범위 계산 (중간/챕터경계/마지막) | Task 1 — `compute_ranges()` |
| bible.json 원문 추출 | Task 2 — `load_bible()`, `extract_verses()` |
| 책별 마크다운 파일 저장 | Task 3 — `save_episode()` |
| 2-step 섹션 업데이트 | Task 3 — `update_step2()` |
| Resume 로직 (step1/step2) | Task 3 — `needs_step1()`, `needs_step2()` |
| Claude Haiku step1 (상황) | Task 4 — `run_step1()` |
| Claude Sonnet step2 (의미) | Task 4 — `run_step2()` |
| 재시도 로직 3회 | Task 4 — `call_with_retry()` |
| `--step`, `--book`, `--output` CLI | Task 5 — argparse |
| `data/episodes/` gitignore | Task 5 — `.gitignore` |

갭 없음. 플레이스홀더 없음. Task 간 함수명·시그니처 일관성 확인됨.
