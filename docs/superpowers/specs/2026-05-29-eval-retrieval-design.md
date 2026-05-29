# 에피소드 검색 전략 비교 실험 설계

**날짜**: 2026-05-29
**상태**: 승인됨

---

## 목표

`data/episodes/`에 축적된 에피소드 DB를 활용해 4가지 검색 전략을 구현하고, 실제 기도제목/고민 쿼리에 대한 결과를 수동으로 비교 평가한다. 이 실험 결과를 바탕으로 `core/matcher.py`를 에피소드 기반으로 재작성한다.

---

## 파일 구조

```
evals/
  eval_retrieval.py        # 메인 스크립트
  eval_queries.json        # 쿼리 입력 + 결과 저장 (같은 파일)
  embeddings_cache.json    # 에피소드 임베딩 캐시 (자동 생성, git 제외)
```

---

## 에피소드 로딩

`data/episodes/**/*.md` 전체를 읽어 각 에피소드의 텍스트를 구성한다.

파싱 대상:
- `book`: 디렉터리명 (예: `마태복음`)
- `title`: `# ` 헤더
- `slug`: 파일명 (확장자 제외)
- `step1`: `## 1-step (상황)` 섹션 텍스트
- `step2`: `## 2-step (의미)` 섹션 텍스트

인덱싱 텍스트: `title + " " + step1 + " " + step2` 연결

step1 또는 step2가 비어 있는 파일은 로딩하되, 있는 텍스트만 사용한다.

---

## 4가지 전략

### BM25 (Sparse Retrieval)

- 라이브러리: `rank-bm25`
- 인덱싱 텍스트를 공백/구두점 기준으로 토큰화
- 쿼리 토큰과 문서 토큰의 BM25 점수로 순위 결정

### Embedding (Dense Retrieval)

- 모델: OpenAI `text-embedding-3-small`
- 에피소드 임베딩을 `embeddings_cache.json`에 slug 기준으로 캐시
- 재실행 시 캐시에 없는 에피소드만 추가 임베딩
- 쿼리 임베딩과 에피소드 임베딩 간 코사인 유사도로 순위 결정

### Hybrid (BM25 + Embedding)

- BM25 점수와 코사인 유사도 점수를 각각 [0, 1]로 min-max 정규화
- `score = α × BM25_norm + (1-α) × embedding_norm`
- 기본 α = 0.5 (CLI `--alpha`로 조정 가능)

### BM25 + LLM Reranking

- BM25로 상위 `llm_pool`개(기본 20) 후보 추출
- Claude Haiku에 쿼리 + 후보 목록을 전달해 재순위 요청
- JSON 배열(slug 목록)로 응답받아 순서대로 최종 결과 반환

---

## eval_queries.json 스키마

```json
[
  {
    "query": "회사에서 믿었던 동료한테 배신당했어요.",
    "results": {
      "bm25": [
        {"book": "마태복음", "title": "...", "slug": "...", "score": 1.23, "step2": "..."}
      ],
      "embedding": [...],
      "hybrid": [...],
      "llm": [...]
    }
  }
]
```

- `results` 키가 없는 쿼리 = 미처리.
- 실행 시 지정된 전략 중 결과가 없는 쿼리+전략 조합만 처리. 이미 결과가 있는 조합은 건너뜀.
- 재처리가 필요한 경우: `eval_queries.json`에서 해당 전략 키를 직접 삭제 후 재실행.

---

## CLI

```bash
# 전체 전략, 기본값으로 실행
conda run -n areum python evals/eval_retrieval.py

# 특정 전략만
conda run -n areum python evals/eval_retrieval.py --strategies bm25 hybrid

# 파라미터 조정
conda run -n areum python evals/eval_retrieval.py --top-k 5 --alpha 0.4 --llm-pool 20
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--strategies` | `bm25 embedding hybrid llm` | 실행할 전략 (복수 선택 가능) |
| `--top-k` | `5` | 전략별 반환 에피소드 수 |
| `--alpha` | `0.5` | Hybrid 전략의 BM25 가중치 |
| `--llm-pool` | `20` | LLM Reranking 전략의 BM25 후보 수 |

---

## 터미널 출력 형식

```
에피소드 852개 로딩 완료.

=== 쿼리 1/10: "회사에서 믿었던 동료한테 배신당했어요." ===

[BM25]
1. 마태복음 — 베드로가 예수를 부인하다 (score: 14.2)
   사람의 배신과 자기 보호 본능...
2. ...

[Embedding]
1. ...

[Hybrid]
1. ...

[LLM]
1. ...

결과 저장 완료 → evals/eval_queries.json
```

---

## 의존성

```
rank-bm25     # BM25
openai        # Embedding API
anthropic     # LLM Reranking (기존 설치)
```

`.env`에 `OPENAI_API_KEY` 필요.

---

## 범위 밖

- 자동 메트릭 계산 (Hit@k, MRR 등) — 수동 검토로 충분
- 임베딩 모델 교체 인터페이스 — 현재 규모에서 불필요
- 결과 파일 분리 — eval_queries.json 단일 파일로 관리
