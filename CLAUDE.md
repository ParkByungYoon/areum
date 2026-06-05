# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 언어

모든 답변은 한국어로 작성한다.

## 프로젝트 개요

**아름(Areum)**은 기독교인을 위한 말씀 묵상 + 기도 관리 AI 앱이다. 사용자의 고민/기도제목을 입력받아 관련 성경 에피소드를 연결하고, 기도를 로컬 마크다운에 축적한다.

핵심 철학: AI는 해석하거나 방향을 지시하지 않는다 — 성경 에피소드를 연결할 뿐이다.

## 환경 설정

conda 환경 `areum`을 사용한다. `conda run`은 인터랙티브 프롬프트를 트리거하는 경우가 있으므로, Python 실행파일을 직접 사용한다:

```powershell
# Windows (PowerShell)
C:\Users\USER\anaconda3\envs\areum\python.exe <script>
C:\Users\USER\anaconda3\envs\areum\python.exe -m pytest
C:\Users\USER\anaconda3\envs\areum\python.exe -m pip install <package>
```

`.env` 파일에 `ANTHROPIC_API_KEY`가 필요하다.

## 주요 명령어

```powershell
$py = "C:\Users\USER\anaconda3\envs\areum\python.exe"

# 전체 테스트
& $py -m pytest

# 단일 테스트 파일 / 단일 테스트
& $py -m pytest tests/test_build_crossref.py
& $py -m pytest tests/test_episode_pipeline.py::test_load_bible_returns_dict

# 사복음서 cross-reference 파이프라인
& $py data/fetch_crossref.py          # cross_references.db 다운로드 (최초 1회)
& $py data/build_episodes.py          # subtitle.md → data/episodes.json
& $py data/build_crossref.py          # data/episodes.json → data/gospels_crossrefs.json
& $py visualize/visualize_crossref.py   # gospels_crossrefs.json → visualize/gospels_network.html
& $py visualize/visualize_same_title.py # episodes.json → visualize/gospels_same_title.html

# 에피소드 AI 파이프라인 (신약 전체)
& $py data/episode_pipeline.py --step 1              # 상황 요약 생성
& $py data/episode_pipeline.py --step 2              # 의미 해석 생성
& $py data/episode_pipeline.py --step 1 --book 마태복음  # 특정 책만

# CLI 실행 (에피소드 기반 구현 후 사용 가능)
& $py cli/main.py
```

## 아키텍처

### 에피소드 기반 파이프라인

신약 전체(852 에피소드)를 페리코페(pericope) 단위로 처리한다.

```
subtitle.md + bible.json
    → parse_subtitles.py (에피소드 경계 파싱)
    → episode_pipeline.py --step 1 (Haiku: 상황 요약)
    → episode_pipeline.py --step 2 (Sonnet: 신학적 의미 해석)
    → data/episodes/<책이름>/<NNN_제목>.md
```

### 사복음서 Cross-Reference 파이프라인

사복음서(마태/마가/누가/요한) 472개 에피소드 간 서사적 병행(narrative parallel)을 구축한다.

```
subtitle.md + bible.json
    → build_episodes.py
    → data/episodes.json  (472개 에피소드, chapter_start/chapter_end 포맷)

data/cross_references.db (openbible.info, votes 기반)
+ data/episodes.json
    → build_crossref.py (VOTES_THRESHOLD=100, 1-hop 직접 연결)
    → data/gospels_crossrefs.json

data/gospels_crossrefs.json
    → visualize/visualize_crossref.py  → visualize/gospels_network.html
    → visualize/visualize_same_title.py → visualize/gospels_same_title.html
```

**서사적 병행 판정 기준**: cross-reference의 `to_verse`가 대상 에피소드의 `(chapter_start, verse_start)~(chapter_end, verse_end)` 범위 안에 속하면 직접 연결(1-hop, 전이 없음).

### 앱 레이어 (재작성 예정)

`core/matcher.py`와 `core/translator.py`는 에피소드 기반 매칭으로 재작성 예정이다. `cli/main.py`는 이 두 모듈이 완성된 후 연결된다.

### 에피소드 파일 포맷

`data/episodes/<책이름>/<NNN_제목>.md`:

```markdown
# 제목
**범위**: 책 X:X-X:X

## 1-step (상황)
<상황 요약 산문>

## 2-step (의미)
<신학적·감정적 의미 산문>
```

### episodes.json 포맷

`data/episodes.json` (build_episodes.py 생성, 472개 사복음서 에피소드):

```json
{
  "book": 42,
  "book_name": "누가복음",
  "episode": "탕자의 비유",
  "chapter_start": 15,
  "verse_start": 11,
  "chapter_end": 15,
  "verse_end": 32
}
```

`book` 번호: 마태복음=40, 마가복음=41, 누가복음=42, 요한복음=43.

### 데이터 파일

| 파일 | 설명 |
|------|------|
| `bible.json` | 신약 성경 원문 JSON (`korean`, `chapters[].verses[]`) |
| `subtitle.md` | 새번역 소제목 목록 (에피소드 경계 정의) |
| `data/episodes.json` | 사복음서 472개 에피소드 (`build_episodes.py` 생성) |
| `data/cross_references.db` | openbible.info cross-reference DB (gitignored, `fetch_crossref.py` 다운로드) |
| `data/gospels_crossrefs.json` | 에피소드별 cross-reference + 연결 에피소드 (gitignored, `build_crossref.py` 생성) |
| `data/episodes/` | AI 생성 에피소드 페이지 (`<책이름>/<NNN_제목>.md`) |
| `visualize/` | 시각화 스크립트 및 HTML 출력 |
| `prayers.md` | 축적된 기도 일지 (append-only 마크다운) |

### 모델 사용 기준

- **Step 1 (상황 요약)**: `claude-haiku-4-5-20251001`
- **Step 2 (신학적 의미 해석)**: `claude-sonnet-4-6`

### API 호출 패턴

모든 Claude API 호출은 `call_with_retry(fn, retries=3)` 래퍼를 통한다. 실패 시 5초·10초 간격으로 재시도한다. 파이프라인은 이미 처리된 에피소드를 건너뛰는 멱등성 구조다(`needs_step1`, `needs_step2` 확인).

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 언어 | Python 3.11 |
| AI | Anthropic Claude API (`anthropic>=0.40.0`) |
| 성경 DB | 로컬 마크다운 (`data/episodes/`) |
| 기도 저장소 | 로컬 마크다운 (`prayers.md`) |
| 환경 변수 | python-dotenv |
| 테스트 | pytest |

## 테스트 규칙

- 테스트 파일에 `sys.path.insert(0, ".")` 로 루트 경로를 추가한다.
- Claude API 호출이 포함된 함수는 `unittest.mock.patch`로 모킹한다.
- 파일 I/O 테스트는 `tempfile.TemporaryDirectory()`를 사용한다.
- `bible.json`을 직접 읽는 테스트는 실제 파일에 의존한다(fixture 없음).
