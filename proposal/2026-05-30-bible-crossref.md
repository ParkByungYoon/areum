# Proposal: Bible Cross-Reference Data Integration

**Date:** 2026-05-30  
**Status:** proposed

---

## Goal

scrollmapper/bible_databases의 cross-reference SQLite DB를 가져와서,
사복음서(마태/마가/누가/요한) 에피소드(pericope) 별로 연결된 `to_verse_range`를 정리한 JSON을 생성한다.

이 데이터는 향후 아름에서 "관련 말씀 더 보기" 또는 구절 간 연결망 확장에 활용된다.

---

## Background

아름 프로젝트는 신약 전체를 대상으로 한다.
Cross-reference 작업은 사복음서(마태복음 40, 마가복음 41, 누가복음 42, 요한복음 43) 범위로 진행한다.

scrollmapper/bible_databases의 cross_references 테이블 스키마:

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `from_book` | int | 출발 책 번호 |
| `from_chapter` | int | 출발 장 |
| `from_verse` | int | 출발 절 |
| `to_book` | int | 도착 책 번호 |
| `to_chapter` | int | 도착 장 |
| `to_verse_start` | int | 도착 절 시작 |
| `to_verse_end` | int | 도착 절 끝 |
| `votes` | int | 참조 신뢰도 점수 |

사복음서 book 번호: 마태복음=40, 마가복음=41, 누가복음=42, 요한복음=43

---

## Output Format

`data/gospels_crossrefs.json`:

```json
[
  {
    "book": 42,
    "book_name": "누가복음",
    "from_chapter": 15,
    "from_verse_start": 11,
    "from_verse_end": 32,
    "episode": "탕자의 비유",
    "cross_references": [
      {
        "from_verse": 11,
        "to_book": 1,
        "to_book_name": "창세기",
        "to_chapter": 41,
        "to_verse_start": 14,
        "to_verse_end": 14,
        "votes": 12
      }
    ]
  }
]
```

---

## File Map

```
areum/
├── data/
│   ├── fetch_crossref.py        # SQLite 다운로드
│   ├── build_crossref.py        # 에피소드별 to_verse_range 정리
│   ├── episodes.json            # 사복음서 에피소드(pericope) 정의
│   └── gospels_crossrefs.json   # (generated)
├── tests/
│   ├── test_fetch_crossref.py
│   └── test_build_crossref.py
```

---

## Task 1: SQLite 파일 가져오기

**Files:**
- Create: `data/fetch_crossref.py`
- Output: `data/cross_references.db`

- [ ] **Step 1: `data/fetch_crossref.py` 구현**

```python
import urllib.request
import os

DB_URL = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/sqlite/cross_references.db"
OUTPUT_PATH = "data/cross_references.db"


def download_crossref_db(url: str = DB_URL, output: str = OUTPUT_PATH) -> str:
    if os.path.exists(output):
        print(f"이미 존재함: {output}")
        return output
    print(f"다운로드 중: {url}")
    urllib.request.urlretrieve(url, output)
    print(f"완료: {output}")
    return output


if __name__ == "__main__":
    download_crossref_db()
```

- [ ] **Step 2: 실행 및 확인**

```bash
python data/fetch_crossref.py
```

Expected: `data/cross_references.db` 파일 생성됨.

- [ ] **Step 3: 사복음서 데이터 규모 확인**

```bash
python -c "
import sqlite3
conn = sqlite3.connect('data/cross_references.db')
cur = conn.cursor()
for book, name in [(40,'마태복음'),(41,'마가복음'),(42,'누가복음'),(43,'요한복음')]:
    cur.execute('SELECT COUNT(*) FROM cross_references WHERE from_book=?', (book,))
    print(f'{name}: {cur.fetchone()[0]}개')
conn.close()
"
```

- [ ] **Step 4: .gitignore에 추가**

```
data/cross_references.db
data/gospels_crossrefs.json
```

- [ ] **Step 5: Commit**

```bash
git add data/fetch_crossref.py
git commit -m "feat: fetch cross_references.db from scrollmapper"
```

---

## Task 2: 사복음서 에피소드 정의 파일 작성

**Files:**
- Create: `data/episodes.json`

사복음서의 주요 pericope(내러티브 단위)를 책별로 정의한다.

- [ ] **Step 1: `data/episodes.json` 작성**

```json
[
  {"book": 40, "book_name": "마태복음", "episode": "산상수훈", "chapter": 5, "verse_start": 1, "verse_end": 48},
  {"book": 40, "book_name": "마태복음", "episode": "주기도문", "chapter": 6, "verse_start": 9, "verse_end": 13},
  {"book": 40, "book_name": "마태복음", "episode": "씨 뿌리는 자 비유", "chapter": 13, "verse_start": 1, "verse_end": 23},
  {"book": 40, "book_name": "마태복음", "episode": "탕자의 비유 (마태)", "chapter": 18, "verse_start": 12, "verse_end": 14},
  {"book": 40, "book_name": "마태복음", "episode": "최후의 만찬", "chapter": 26, "verse_start": 17, "verse_end": 30},
  {"book": 40, "book_name": "마태복음", "episode": "부활", "chapter": 28, "verse_start": 1, "verse_end": 20},

  {"book": 41, "book_name": "마가복음", "episode": "예수의 세례", "chapter": 1, "verse_start": 9, "verse_end": 11},
  {"book": 41, "book_name": "마가복음", "episode": "광야의 시험", "chapter": 1, "verse_start": 12, "verse_end": 13},
  {"book": 41, "book_name": "마가복음", "episode": "제자 부르심", "chapter": 1, "verse_start": 16, "verse_end": 20},
  {"book": 41, "book_name": "마가복음", "episode": "씨 뿌리는 자 비유", "chapter": 4, "verse_start": 1, "verse_end": 20},
  {"book": 41, "book_name": "마가복음", "episode": "오병이어", "chapter": 6, "verse_start": 30, "verse_end": 44},
  {"book": 41, "book_name": "마가복음", "episode": "부활", "chapter": 16, "verse_start": 1, "verse_end": 20},

  {"book": 42, "book_name": "누가복음", "episode": "세례 요한의 탄생 예고", "chapter": 1, "verse_start": 5, "verse_end": 25},
  {"book": 42, "book_name": "누가복음", "episode": "예수의 탄생 예고", "chapter": 1, "verse_start": 26, "verse_end": 38},
  {"book": 42, "book_name": "누가복음", "episode": "예수 탄생", "chapter": 2, "verse_start": 1, "verse_end": 20},
  {"book": 42, "book_name": "누가복음", "episode": "광야의 시험", "chapter": 4, "verse_start": 1, "verse_end": 13},
  {"book": 42, "book_name": "누가복음", "episode": "나사렛 회당 선포", "chapter": 4, "verse_start": 14, "verse_end": 30},
  {"book": 42, "book_name": "누가복음", "episode": "제자 부르심", "chapter": 5, "verse_start": 1, "verse_end": 11},
  {"book": 42, "book_name": "누가복음", "episode": "산상설교 (평지설교)", "chapter": 6, "verse_start": 17, "verse_end": 49},
  {"book": 42, "book_name": "누가복음", "episode": "선한 사마리아인", "chapter": 10, "verse_start": 25, "verse_end": 37},
  {"book": 42, "book_name": "누가복음", "episode": "주기도문", "chapter": 11, "verse_start": 1, "verse_end": 13},
  {"book": 42, "book_name": "누가복음", "episode": "잃은 양 비유", "chapter": 15, "verse_start": 1, "verse_end": 7},
  {"book": 42, "book_name": "누가복음", "episode": "탕자의 비유", "chapter": 15, "verse_start": 11, "verse_end": 32},
  {"book": 42, "book_name": "누가복음", "episode": "부자와 나사로", "chapter": 16, "verse_start": 19, "verse_end": 31},
  {"book": 42, "book_name": "누가복음", "episode": "삭개오", "chapter": 19, "verse_start": 1, "verse_end": 10},
  {"book": 42, "book_name": "누가복음", "episode": "최후의 만찬", "chapter": 22, "verse_start": 14, "verse_end": 38},
  {"book": 42, "book_name": "누가복음", "episode": "겟세마네 기도", "chapter": 22, "verse_start": 39, "verse_end": 46},
  {"book": 42, "book_name": "누가복음", "episode": "부활", "chapter": 24, "verse_start": 1, "verse_end": 12},

  {"book": 43, "book_name": "요한복음", "episode": "태초에 말씀이 계시니라", "chapter": 1, "verse_start": 1, "verse_end": 18},
  {"book": 43, "book_name": "요한복음", "episode": "가나의 혼인 잔치", "chapter": 2, "verse_start": 1, "verse_end": 12},
  {"book": 43, "book_name": "요한복음", "episode": "니고데모와의 대화", "chapter": 3, "verse_start": 1, "verse_end": 21},
  {"book": 43, "book_name": "요한복음", "episode": "요한복음 3:16", "chapter": 3, "verse_start": 16, "verse_end": 21},
  {"book": 43, "book_name": "요한복음", "episode": "생명의 떡", "chapter": 6, "verse_start": 22, "verse_end": 59},
  {"book": 43, "book_name": "요한복음", "episode": "나는 선한 목자다", "chapter": 10, "verse_start": 1, "verse_end": 21},
  {"book": 43, "book_name": "요한복음", "episode": "나사로의 부활", "chapter": 11, "verse_start": 1, "verse_end": 44},
  {"book": 43, "book_name": "요한복음", "episode": "세족식", "chapter": 13, "verse_start": 1, "verse_end": 17},
  {"book": 43, "book_name": "요한복음", "episode": "나는 길이요 진리요 생명이니", "chapter": 14, "verse_start": 1, "verse_end": 14},
  {"book": 43, "book_name": "요한복음", "episode": "포도나무 비유", "chapter": 15, "verse_start": 1, "verse_end": 17},
  {"book": 43, "book_name": "요한복음", "episode": "대제사장 기도", "chapter": 17, "verse_start": 1, "verse_end": 26},
  {"book": 43, "book_name": "요한복음", "episode": "부활", "chapter": 20, "verse_start": 1, "verse_end": 31}
]
```

- [ ] **Step 2: Commit**

```bash
git add data/episodes.json
git commit -m "data: define gospel pericopes for cross-reference mapping"
```

---

## Task 3: 에피소드별 to_verse_range 정리

**Files:**
- Create: `data/build_crossref.py`
- Test: `tests/test_build_crossref.py`
- Output: `data/gospels_crossrefs.json`

- [ ] **Step 1: 테스트 작성**

`tests/test_build_crossref.py`:
```python
import sys
sys.path.insert(0, ".")
from data.build_crossref import load_crossrefs_for_episode, BOOK_NAMES

SAMPLE_ROWS = [
    (42, 15, 11, 1, 41, 14, 14, 12),
    (42, 15, 12, 19, 2, 1, 5, 8),
    (42, 15, 32, 15, 3, 1, 1, 5),
    (43, 3, 16, 19, 1, 1, 1, 20),  # 요한복음 3:16 — 다른 책
]

EPISODE_LUKE = {"book": 42, "book_name": "누가복음", "episode": "탕자의 비유", "chapter": 15, "verse_start": 11, "verse_end": 32}
EPISODE_JOHN = {"book": 43, "book_name": "요한복음", "episode": "요한복음 3:16", "chapter": 3, "verse_start": 16, "verse_end": 21}


def test_filters_by_book_and_verse_range():
    refs = load_crossrefs_for_episode(SAMPLE_ROWS, EPISODE_LUKE)
    assert all(r["from_verse"] >= 11 and r["from_verse"] <= 32 for r in refs)
    assert len(refs) == 3


def test_different_book_episode():
    refs = load_crossrefs_for_episode(SAMPLE_ROWS, EPISODE_JOHN)
    assert len(refs) == 1


def test_includes_to_verse_range():
    refs = load_crossrefs_for_episode(SAMPLE_ROWS, EPISODE_LUKE)
    assert all("to_verse_start" in r and "to_verse_end" in r for r in refs)


def test_includes_book_name():
    refs = load_crossrefs_for_episode(SAMPLE_ROWS, EPISODE_LUKE)
    assert all("to_book_name" in r for r in refs)


def test_sorted_by_votes_desc():
    refs = load_crossrefs_for_episode(SAMPLE_ROWS, EPISODE_LUKE)
    votes = [r["votes"] for r in refs]
    assert votes == sorted(votes, reverse=True)


def test_book_names_covers_four_gospels():
    assert BOOK_NAMES[40] == "마태복음"
    assert BOOK_NAMES[41] == "마가복음"
    assert BOOK_NAMES[42] == "누가복음"
    assert BOOK_NAMES[43] == "요한복음"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_build_crossref.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: `data/build_crossref.py` 구현**

```python
import json
import sqlite3

GOSPEL_BOOKS = (40, 41, 42, 43)

BOOK_NAMES = {
    1: "창세기", 2: "출애굽기", 3: "레위기", 4: "민수기", 5: "신명기",
    6: "여호수아", 7: "사사기", 8: "룻기", 9: "사무엘상", 10: "사무엘하",
    11: "열왕기상", 12: "열왕기하", 13: "역대상", 14: "역대하", 15: "에스라",
    16: "느헤미야", 17: "에스더", 18: "욥기", 19: "시편", 20: "잠언",
    21: "전도서", 22: "아가", 23: "이사야", 24: "예레미야", 25: "예레미야애가",
    26: "에스겔", 27: "다니엘", 28: "호세아", 29: "요엘", 30: "아모스",
    31: "오바댜", 32: "요나", 33: "미가", 34: "나훔", 35: "하박국",
    36: "스바냐", 37: "학개", 38: "스가랴", 39: "말라기",
    40: "마태복음", 41: "마가복음", 42: "누가복음", 43: "요한복음",
    44: "사도행전", 45: "로마서", 46: "고린도전서", 47: "고린도후서",
    48: "갈라디아서", 49: "에베소서", 50: "빌립보서", 51: "골로새서",
    52: "데살로니가전서", 53: "데살로니가후서", 54: "디모데전서", 55: "디모데후서",
    56: "디도서", 57: "빌레몬서", 58: "히브리서", 59: "야고보서",
    60: "베드로전서", 61: "베드로후서", 62: "요한1서", 63: "요한2서",
    64: "요한3서", 65: "유다서", 66: "요한계시록",
}


def load_crossrefs_for_episode(rows: list[tuple], episode: dict) -> list[dict]:
    book = episode["book"]
    chapter = episode["chapter"]
    v_start = episode["verse_start"]
    v_end = episode["verse_end"]

    result = []
    for row in rows:
        from_book, from_chapter, from_verse, to_book, to_chapter, to_verse_start, to_verse_end, votes = row
        if from_book == book and from_chapter == chapter and v_start <= from_verse <= v_end:
            result.append({
                "from_verse": from_verse,
                "to_book": to_book,
                "to_book_name": BOOK_NAMES.get(to_book, f"Book{to_book}"),
                "to_chapter": to_chapter,
                "to_verse_start": to_verse_start,
                "to_verse_end": to_verse_end,
                "votes": votes,
            })

    return sorted(result, key=lambda r: r["votes"], reverse=True)


def build(
    db_path: str = "data/cross_references.db",
    episodes_path: str = "data/episodes.json",
    output_path: str = "data/gospels_crossrefs.json",
):
    with open(episodes_path, encoding="utf-8") as f:
        episodes = json.load(f)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    placeholders = ",".join("?" * len(GOSPEL_BOOKS))
    cur.execute(
        f"SELECT from_book, from_chapter, from_verse, to_book, to_chapter, to_verse_start, to_verse_end, votes FROM cross_references WHERE from_book IN ({placeholders})",
        GOSPEL_BOOKS,
    )
    all_rows = cur.fetchall()
    conn.close()

    output = []
    for ep in episodes:
        refs = load_crossrefs_for_episode(all_rows, ep)
        output.append({
            "book": ep["book"],
            "book_name": ep["book_name"],
            "episode": ep["episode"],
            "from_chapter": ep["chapter"],
            "from_verse_start": ep["verse_start"],
            "from_verse_end": ep["verse_end"],
            "cross_references": refs,
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total_refs = sum(len(ep["cross_references"]) for ep in output)
    print(f"완료: {len(output)}개 에피소드, 총 {total_refs}개 cross-reference → {output_path}")


if __name__ == "__main__":
    build()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_build_crossref.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 5: 실행**

```bash
python data/fetch_crossref.py
python data/build_crossref.py
```

Expected: `data/gospels_crossrefs.json` 생성.

- [ ] **Step 6: 출력 샘플 확인**

```bash
python -c "
import json
with open('data/gospels_crossrefs.json', encoding='utf-8') as f:
    data = json.load(f)
for ep in data[:5]:
    print(ep['book_name'], ep['episode'], '-', len(ep['cross_references']), '개')
"
```

- [ ] **Step 7: Commit**

```bash
git add data/build_crossref.py tests/test_build_crossref.py
git commit -m "feat: build gospel cross-reference map from scrollmapper DB"
```

---

## Self-Review

| 요구사항 | 구현 Task |
|---------|----------|
| scrollmapper SQLite 파일 가져오기 | Task 1 — `fetch_crossref.py` |
| 사복음서(40-43) 범위 처리 | Task 3 — `GOSPEL_BOOKS = (40,41,42,43)` |
| 에피소드(pericope) 단위 정의 | Task 2 — `episodes.json` (마태/마가/누가/요한) |
| 에피소드별 `to_verse_range` 정리 | Task 3 — `build_crossref.py` |
| votes 기준 정렬 (신뢰도 순) | Task 3 — `sorted(..., reverse=True)` |
| 한국어 책 이름 매핑 | Task 3 — `BOOK_NAMES` dict |
| 기존 코드 비파괴 | `data/` 에만 추가, core/storage 미수정 |
