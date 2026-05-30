import json
import sqlite3

GOSPEL_BOOKS = (40, 41, 42, 43)
VOTES_THRESHOLD = 10

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


def load_crossrefs_for_episode(rows: list[tuple], episode: dict, min_votes: int = VOTES_THRESHOLD) -> list[dict]:
    book = episode["book"]
    chapter = episode["chapter"]
    v_start = episode["verse_start"]
    v_end = episode["verse_end"]

    result = []
    for row in rows:
        from_book, from_chapter, from_verse, to_book, to_chapter, to_verse_start, to_verse_end, votes = row
        if (
            from_book == book
            and from_chapter == chapter
            and v_start <= from_verse <= v_end
            and to_book in GOSPEL_BOOKS
            and votes >= min_votes
        ):
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


def _build_connected_episodes(episodes_with_refs: list[dict]) -> list[list[dict]]:
    """to_verse_range가 다른 에피소드의 from_verse_range 안에 속하면 직접 연결."""
    n = len(episodes_with_refs)

    # 인접 그래프: cross-ref의 to_verse가 상대 에피소드 본문 범위 안에 있을 때만 연결
    adj: list[set[int]] = [set() for _ in range(n)]
    for i, ep in enumerate(episodes_with_refs):
        for ref in ep["cross_references"]:
            t_book = ref["to_book"]
            t_ch = ref["to_chapter"]
            t_vs = ref["to_verse_start"]
            for j, target in enumerate(episodes_with_refs):
                if (
                    j != i
                    and target["book"] == t_book
                    and target["from_chapter"] == t_ch
                    and target["from_verse_start"] <= t_vs <= target["from_verse_end"]
                ):
                    adj[i].add(j)
                    adj[j].add(i)

    # 1-hop 이웃만 반환 (전이 없음 — 직접 참조한 에피소드만)
    result = []
    for i in range(n):
        connected = [
            {
                "book": episodes_with_refs[j]["book"],
                "book_name": episodes_with_refs[j]["book_name"],
                "episode": episodes_with_refs[j]["episode"],
                "from_chapter": episodes_with_refs[j]["from_chapter"],
                "from_verse_start": episodes_with_refs[j]["from_verse_start"],
                "from_verse_end": episodes_with_refs[j]["from_verse_end"],
            }
            for j in sorted(adj[i])
        ]
        result.append(connected)

    return result


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
        f"SELECT from_book, from_chapter, from_verse, to_book, to_chapter, to_verse_start, to_verse_end, votes "
        f"FROM cross_references WHERE from_book IN ({placeholders}) AND to_book IN ({placeholders})",
        GOSPEL_BOOKS * 2,
    )
    all_rows = cur.fetchall()
    conn.close()

    episodes_with_refs = []
    for ep in episodes:
        refs = load_crossrefs_for_episode(all_rows, ep)
        episodes_with_refs.append({
            "book": ep["book"],
            "book_name": ep["book_name"],
            "episode": ep["episode"],
            "from_chapter": ep["chapter"],
            "from_verse_start": ep["verse_start"],
            "from_verse_end": ep["verse_end"],
            "cross_references": refs,
        })

    connected_list = _build_connected_episodes(episodes_with_refs)

    output = []
    for ep, connected in zip(episodes_with_refs, connected_list):
        output.append({**ep, "connected_episodes": connected})

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total_refs = sum(len(ep["cross_references"]) for ep in output)
    total_connected = sum(len(ep["connected_episodes"]) for ep in output)
    print(f"완료: {len(output)}개 에피소드, {total_refs}개 cross-reference, {total_connected}개 connected 연결 → {output_path}")


if __name__ == "__main__":
    build()
