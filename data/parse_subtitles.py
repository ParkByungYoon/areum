import re

BOOK_ABBR = {
    "마": "마태복음", "막": "마가복음", "눅": "누가복음", "요": "요한복음",
    "행": "사도행전", "롬": "로마서", "고전": "고린도전서", "고후": "고린도후서",
    "갈": "갈라디아서", "엡": "에베소서", "빌": "빌립보서", "골": "골로새서",
    "살전": "데살로니가전서", "살후": "데살로니가후서", "딤전": "디모데전서",
    "딤후": "디모데후서", "딛": "디도서", "몬": "빌레몬서", "히": "히브리서",
    "약": "야고보서", "벧전": "베드로전서", "벧후": "베드로후서",
    "요1": "요한일서", "요2": "요한이서", "요3": "요한삼서", "유": "유다서",
    "계": "요한계시록",
}


def parse_subtitles(path: str = "subtitle.md") -> list[dict]:
    episodes = []
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if "[" not in line:
            continue
        match = re.match(r'^(.+?)\s+\[(\S+)\s+(\d+):(\d+)\]$', line)
        if not match:
            continue
        title = match.group(1)
        abbr = match.group(2)
        chapter = int(match.group(3))
        verse = int(match.group(4))
        book = BOOK_ABBR.get(abbr, abbr)
        episodes.append({"book": book, "title": title, "start_ch": chapter, "start_v": verse})

    book_counters: dict[str, int] = {}
    for ep in episodes:
        book = ep["book"]
        book_counters[book] = book_counters.get(book, 0) + 1
        idx = book_counters[book]
        safe_title = re.sub(r'[^\w]', '_', ep["title"], flags=re.UNICODE).strip('_')
        ep["slug"] = f"{idx:03d}_{safe_title}"

    return episodes


def compute_ranges(episodes: list[dict], bible: dict) -> list[dict]:
    result = []
    for i, ep in enumerate(episodes):
        ep = dict(ep)
        book = ep["book"]

        next_ep = next(
            (episodes[j] for j in range(i + 1, len(episodes)) if episodes[j]["book"] == book),
            None,
        )

        if next_ep:
            if next_ep["start_v"] > 1:
                ep["end_ch"] = next_ep["start_ch"]
                ep["end_v"] = next_ep["start_v"] - 1
            else:
                prev_ch = next_ep["start_ch"] - 1
                book_verses = bible.get(book, [])
                last_v = max(
                    (v["verse"] for v in book_verses if v["chapter"] == prev_ch),
                    default=1,
                )
                ep["end_ch"] = prev_ch
                ep["end_v"] = last_v
        else:
            book_verses = bible.get(book, [])
            if book_verses:
                last = max(book_verses, key=lambda v: (v["chapter"], v["verse"]))
                ep["end_ch"] = last["chapter"]
                ep["end_v"] = last["verse"]
            else:
                ep["end_ch"] = ep["start_ch"]
                ep["end_v"] = ep["start_v"]

        result.append(ep)
    return result
