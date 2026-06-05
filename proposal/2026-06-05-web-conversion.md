# 웹 전환 Proposal

**날짜:** 2026-06-05  
**상태:** 제안

---

## 배경

현재 아름은 CLI 기반으로 동작한다. 소수 인원(2-3명)이 함께 사용할 수 있도록 웹 앱으로 전환한다.  
URL 하나를 공유하면 누구나 접근 가능하고, 업데이트도 배포 한 번으로 끝난다.

---

## 기술 스택

| 레이어 | 선택 | 이유 |
|---|---|---|
| 백엔드 | FastAPI (Python) | 현재 코드베이스와 동일 언어, 최소 전환 비용 |
| 프론트엔드 | React + TypeScript | 컴포넌트 기반 UI 구성 용이 |
| DB | SQLite (`prayers.db`) | 2-3명 규모, 별도 DB 서버 불필요 |
| 배포 | Railway | 무료 티어, GitHub push 시 자동 배포 |

---

## 아키텍처

```
[브라우저]
    ↕ HTTP
[FastAPI 서버 — Railway]
    ├── /api/match       BM25 에피소드 추천
    ├── /api/prayer      기도 저장 / 연결고리 조회
    └── static/          React 빌드 결과물 서빙
         ↕ 파일 읽기
    ├── data/gospel_episodes.json   (정적 데이터, 코드와 함께 배포)
    └── prayers.db                  (Railway 볼륨에 영구 저장)
```

FastAPI가 React 빌드 파일도 함께 서빙하므로 서버가 하나만 필요하다.

---

## 사용자 식별

로그인 없이 이름 입력 방식으로 운영한다.

- 첫 접속 시 이름 입력 화면
- 입력한 이름을 브라우저 `localStorage`에 저장 → 재접속 시 자동 복원
- 서버는 `user_id`(이름)로 기도 기록을 구분

```
접속 → localStorage에 이름 있음? → 있으면 바로 진입
                                 → 없으면 이름 입력 화면
```

---

## API 엔드포인트

### `POST /api/match`
고민 텍스트를 받아 BM25 top3 에피소드를 반환한다.

```json
// Request
{ "concern": "인간관계가 너무 힘들다" }

// Response
[
  { "subtitle": "오병이어", "situation": "...", "episode_id": "오병이어" },
  { "subtitle": "겟세마네", "situation": "...", "episode_id": "겟세마네" },
  { "subtitle": "삭개오", "situation": "...", "episode_id": "삭개오" }
]
```

### `GET /api/episode/{episode_id}`
선택한 에피소드의 구절 전문을 반환한다.

### `GET /api/connection`
구절 출력 후 기도 연결고리를 조회한다.

```
Query params: user_id, concern, episode_id
```

### `POST /api/prayer`
기도를 저장한다.

```json
{ "user_id": "지훈", "concern": "...", "episode_id": "...", "subtitle": "...", "passage_ref": "..." }
```

---

## 화면 흐름

```
[이름 입력]
     ↓
[고민 입력창]
     ↓
[A/B/C 에피소드 카드 선택]
     ↓
[구절 전문 + 기도 연결고리]
     ↓
[이 말씀으로 기도하셨나요? y/n]
```

---

## 디렉토리 구조 변경

```
areum/
├── api/                ← 신규: FastAPI 라우터
│   ├── main.py         (앱 진입점, static 파일 서빙 포함)
│   ├── routes/
│   │   ├── match.py
│   │   ├── episode.py
│   │   └── prayer.py
├── frontend/           ← 신규: React 앱
│   ├── src/
│   └── dist/           (빌드 결과물 → FastAPI가 서빙)
├── core/               (기존 유지)
├── storage/            (기존 유지, SQLite 전환 완료 후)
└── data/               (기존 유지)
```

---

## 배포 (Railway)

1. GitHub 연결 → `main` 브랜치 push 시 자동 배포
2. Railway 볼륨 마운트 → `prayers.db` 영구 저장 경로 설정
3. 환경변수: `DB_PATH`, `EPISODES_PATH`
4. 빌드 커맨드: `cd frontend && npm run build && cd ..`
5. 시작 커맨드: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

---

## 구현 순서

1. `storage/prayer_store.py` SQLite 전환 (prayers.json → prayers.db, user_id 추가)
2. FastAPI 백엔드 — 기존 `core/matcher.py`, `storage/prayer_store.py` 그대로 활용
3. React 프론트엔드 — 화면 흐름 구현
4. Railway 배포

---

## 참고: 현재 CLI와의 관계

CLI는 유지한다. 백엔드 로직(`core/`, `storage/`)을 CLI와 API가 공유하는 구조이므로 코드 중복 없음.
