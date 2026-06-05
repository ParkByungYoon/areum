"""아름 CLI — BM25 에피소드 매칭"""
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.matcher import EpisodeMatcher
from storage.prayer_store import save_prayer, find_connection

USER_FILE = Path(".areum_user")


def _get_user() -> str:
    if USER_FILE.exists():
        name = USER_FILE.read_text(encoding="utf-8").strip()
        if name:
            return name
    try:
        name = input("이름을 입력해 주세요: ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit(0)
    if not name:
        name = "익명"
    USER_FILE.write_text(name, encoding="utf-8")
    return name


def _truncate(text: str, limit: int = 150) -> str:
    return text[:limit] + " ..." if len(text) > limit else text


def _card(label: str, ep: dict) -> str:
    lines = [f"{label}. {ep['subtitle']}"]
    if ep.get("situation"):
        lines.append("[상황]")
        lines.append(_truncate(ep["situation"]))
    return "\n".join(lines)


def _print_passages(ep: dict):
    passages = ep["passages"]
    best_idx = ep.get("best_passage_idx", 0)
    main = passages[best_idx]
    others = [p for i, p in enumerate(passages) if i != best_idx]

    print("\n[선택한 성경구절]")
    ref = f"{main['book']} {main['chapter_start']}:{main['verse_start']}-{main['chapter_end']}:{main['verse_end']}"
    print(f"{ep['subtitle']} ({ref})")
    for v in main["verses"]:
        print(f"{v['chapter']}:{v['verse']}  {v['text']}")

    if others:
        print("\n[비슷한 내용의 성경구절]")
        for p in others:
            ref = f"{p['book']} {p['chapter_start']}:{p['verse_start']}-{p['chapter_end']}:{p['verse_end']}"
            print(f"\n{ep['subtitle']} ({ref})")
            for v in p["verses"]:
                print(f"{v['chapter']}:{v['verse']}  {v['text']}")

    if ep.get("meaning"):
        print(f"\n[의미]\n{ep['meaning']}")


def _print_connection(conn: dict):
    r = conn["record"]
    date_str = datetime.fromisoformat(r["date"]).strftime("%Y-%m-%d")
    days_ago = conn["days_ago"]
    print("\n[기도 기억]")
    if conn["type"] == "same_episode":
        print(f'{days_ago}일 전 ({date_str}) — "{r["concern"]}"')
        print("→ 그때도 이 말씀을 받으셨어요.")
    else:
        print(f'{days_ago}일 전 ({date_str}) — "{r["concern"]}"')
        print(f'→ 그때는 {r["subtitle"]}을(를) 받으셨어요.')


def run():
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n아름에 오신 것을 환영합니다.")

    user_id = _get_user()
    print(f"안녕하세요, {user_id}님. 고민이나 기도제목을 말씀해 주세요. (종료: q)\n")

    try:
        matcher = EpisodeMatcher()
    except FileNotFoundError:
        print("gospel_episodes.json이 없습니다. 먼저 실행하세요:")
        print("  python data/build_episodes.py")
        return

    labels = ["A", "B", "C"]
    while True:
        try:
            query = input("오늘 어떤 고민이나 기도제목이 있으신가요?\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            break

        if query.lower() in ("q", "quit", "종료"):
            print("종료합니다.")
            break
        if not query:
            continue

        print("\n[관련 말씀을 찾고 있어요...]\n")
        episodes = matcher.match(query, top_n=3)
        if not episodes:
            print("관련 말씀을 찾지 못했습니다. 다른 표현으로 시도해 보세요.\n")
            continue

        for label, ep in zip(labels, episodes):
            print(_card(label, ep))
            print()

        try:
            choice = input("선택 (A/B/C): ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            break

        valid = labels[: len(episodes)]
        if choice not in valid:
            print("A, B, C 중에서 선택해 주세요.\n")
            continue

        selected = episodes[valid.index(choice)]
        _print_passages(selected)

        conn = find_connection(user_id, query, selected["subtitle"])
        if conn:
            _print_connection(conn)

        try:
            answer = input("\n이 말씀으로 기도하셨나요? (y / n)\n> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            break

        if answer == "y":
            passages = selected["passages"]
            best_idx = selected.get("best_passage_idx", 0)
            p = passages[best_idx]
            passage_ref = f"{p['book']} {p['chapter_start']}:{p['verse_start']}-{p['chapter_end']}:{p['verse_end']}"
            save_prayer(user_id, query, selected["subtitle"], selected["subtitle"], passage_ref)
            print("기도가 기록되었습니다.")

        print()


if __name__ == "__main__":
    run()
