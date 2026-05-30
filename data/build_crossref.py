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
