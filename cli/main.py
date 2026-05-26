import json
import sys
sys.path.insert(0, ".")

from core.matcher import extract_tags, find_top_verses
from core.translator import generate_connection
from storage.prayer_store import save_prayer


def load_data() -> tuple[list[dict], dict]:
    with open("data/luke_tagged.json", encoding="utf-8") as f:
        verses = json.load(f)
    with open("data/tags.json", encoding="utf-8") as f:
        vocab = json.load(f)
    return verses, vocab


def run():
    verses, vocab = load_data()

    print("\n아름에 오신 것을 환영합니다.")
    print("오늘 어떤 고민이나 기도제목이 있으신가요?\n")

    concern = input("> ").strip()
    if not concern:
        print("입력이 없어요. 다시 시작해주세요.")
        return

    print("\n[관련 말씀을 찾고 있어요...]\n")

    query_tags = extract_tags(concern, vocab)
    top_verses = find_top_verses(verses, query_tags, top_n=1)

    if not top_verses:
        print("관련 구절을 찾지 못했어요. 다른 표현으로 입력해보세요.")
        return

    verse = top_verses[0]
    connection = generate_connection(concern, verse)

    ref = f"누가복음 {verse['chapter']}:{verse['verse']}"
    print(f"📖 {ref}")
    print(f"{verse['text']}\n")
    print(f"💬 {connection}\n")

    answer = input("기도제목을 저장하시겠어요? (y/n) ").strip().lower()
    if answer == "y":
        save_prayer(concern, verse, connection)
        print("저장되었어요. prayers.md에서 확인하실 수 있어요.\n")
    else:
        print("저장하지 않았어요.\n")


if __name__ == "__main__":
    run()
