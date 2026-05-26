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
