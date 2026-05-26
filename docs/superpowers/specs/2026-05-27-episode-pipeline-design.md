# 에피소드 DB 파이프라인 설계 스펙

**작성일**: 2026-05-27
**범위**: 신약 전체 852개 에피소드 2-step 처리 파이프라인

---

## 1. 목표

`subtitle.md`의 새번역 소제목을 에피소드 경계로 삼아, `bible.json` 원문을 추출하고 Claude API로 2-step 처리하여 책별 마크다운 파일로 저장한다.

---

## 2. 파일 구조

```
areum/
├── data/
│   ├── parse_subtitles.py         # subtitle.md 파서 (공유 유틸)
│   ├── episode_pipeline.py        # 메인 파이프라인 (--step 1 / --step 2)
│   └── episodes/                  # 생성 결과 (gitignore)
│       ├── 마태복음/
│       │   ├── 001_예수의_계보.md
│       │   ├── 002_예수의_탄생.md
│       │   └── ...
│       ├── 마가복음/
│       └── ...
└── subtitle.md                    # 에피소드 경계 정의 (기존)
```

---

## 3. 데이터 흐름

```
subtitle.md
    ↓ parse_subtitles.py
에피소드 목록 [(book, title, start_ref), ...]
    ↓ 절범위 계산 (다음 에피소드 시작절 - 1)
에피소드 범위 [(book, title, start_ch, start_v, end_ch, end_v), ...]
    ↓ bible.json 원문 추출
에피소드 원문 텍스트
    ↓ --step 1: Claude Haiku
1-step 상황 요약 → 마크다운 파일 저장
    ↓ (인간 확인 후)
    ↓ --step 2: Claude Sonnet
2-step 의미 해석 → 마크다운 파일 업데이트
```

---

## 4. 에피소드 마크다운 형식

```markdown
# {title}
**범위**: {book} {start_ch}:{start_v}-{end_ch}:{end_v}

## 1-step (상황)
{AI 생성 — 등장인물, 사건, 배경 3-5문장}

## 2-step (의미)
{AI 생성 — 신학적·감정적 핵심 3-5문장}
```

Step 1 완료 직후: `## 2-step (의미)` 섹션은 빈 상태로 저장.
Step 2 실행 시: 해당 섹션을 채워 덮어씀.

---

## 5. 절범위 계산

`subtitle.md`는 각 에피소드의 시작절만 제공한다. 종료절은 다음 규칙으로 계산:

- **일반**: 다음 에피소드 시작절 바로 앞 절
- **책의 마지막 에피소드**: `bible.json`에서 해당 책의 마지막 절

책 약어 → 한국어 책명 매핑 (마→마태복음, 막→마가복음, 눅→누가복음, 요→요한복음, 행→사도행전, 롬→로마서, 고전→고린도전서, 고후→고린도후서, 갈→갈라디아서, 엡→에베소서, 빌→빌립보서, 골→골로새서, 살전→데살로니가전서, 살후→데살로니가후서, 딤전→디모데전서, 딤후→디모데후서, 딛→디도서, 몬→빌레몬서, 히→히브리서, 약→야고보서, 벧전→베드로전서, 벧후→베드로후서, 요1→요한1서, 요2→요한2서, 요3→요한3서, 유→유다서, 계→요한계시록)

---

## 6. 파이프라인 동작

### Resume 로직
- `--step 1`: 마크다운 파일 없으면 처리, 있으면 건너뜀
- `--step 2`: `## 2-step (의미)` 섹션이 비어 있으면 처리, 내용 있으면 건너뜀

### 실행 인터페이스
```bash
python data/episode_pipeline.py --step 1                    # 전체 step1
python data/episode_pipeline.py --step 1 --book 마태복음    # 특정 책만
python data/episode_pipeline.py --step 2                    # 전체 step2
python data/episode_pipeline.py --step 2 --book 마태복음    # 특정 책만
```

### 에러 처리
- API 오류 시 최대 3회 재시도 (5s, 10s, 15s 대기)
- 재시도 실패 시 해당 에피소드 건너뛰고 계속 진행 (로그 출력)
- 에피소드마다 처리 후 즉시 저장 (중단 안전)

---

## 7. 프롬프트 전략

### Step 1 — Claude Haiku (상황 정리)
```
[system]
성경 에피소드의 등장인물, 사건, 배경을 3-5문장으로 요약하세요.
무엇이 일어났는가, 누가, 왜, 어떤 상황에서. 해석 없이 사실만.

[user]
제목: {title}
범위: {book} {range}
원문:
{verses}
```

### Step 2 — Claude Sonnet (의미 해석)
```
[system]
아래 에피소드 상황 요약을 바탕으로 신학적·감정적 의미를 3-5문장으로
추출하세요. 이 에피소드의 핵심이 무엇인지, 어떤 사람의 어떤 상황에
닿을 수 있는지. AI가 해석을 지시하지 않고 연결점만 제시한다.

[user]
제목: {title}
상황 요약:
{step1_content}
```

---

## 8. 비용 예상

| 단계 | 모델 | 예상 비용 |
|------|------|-----------|
| Step 1 (852 에피소드) | Claude Haiku 4.5 | ~$1.1 |
| Step 2 (852 에피소드) | Claude Sonnet 4.6 | ~$4.0 |
| **합계** | | **~$5.1** |

---

## 9. 구현 모듈

### `data/parse_subtitles.py`
- `parse_subtitles(path) -> list[dict]`: subtitle.md 파싱
- `compute_ranges(episodes, bible_data) -> list[dict]`: 절범위 계산
- 반환 구조: `{book, title, start_ch, start_v, end_ch, end_v, slug}`
  - `slug` 형식: `{NNN}_{title_underscored}` — NNN은 책 내 순서 (001, 002, ...), 제목의 공백/특수문자는 `_`로 치환

### `data/episode_pipeline.py`
- `extract_verses(bible_data, book, start_ch, start_v, end_ch, end_v) -> str`: 원문 추출
- `run_step1(episode, verses) -> str`: Haiku 호출, 상황 요약
- `run_step2(episode, step1_text) -> str`: Sonnet 호출, 의미 해석
- `save_episode(episode, step1, output_dir)`: 마크다운 파일 생성
- `update_step2(filepath, step2_text)`: 기존 파일에서 `## 2-step (의미)` 헤더 이후 내용을 step2_text로 교체
- `main(step, book_filter)`: 전체 파이프라인 실행

---

## 10. 검증 기준

- Step 1 완료: `data/episodes/` 하위 27개 폴더, 852개 파일 생성
- Step 2 완료: 모든 파일의 `## 2-step (의미)` 섹션 비어있지 않음
- Resume 검증: 중간에 중단 후 재실행 시 이미 처리된 파일 건너뜀 확인
