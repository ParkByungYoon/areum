import io
import os
import sqlite3
import urllib.request
import zipfile

ZIP_URL = "https://a.openbible.info/data/cross-references.zip"
OUTPUT_PATH = "data/cross_references.db"

# openbible.info abbreviation → book number mapping (sourced from TSV)
BOOK_ABBR = {
    "Gen": 1, "Exod": 2, "Lev": 3, "Num": 4, "Deut": 5,
    "Josh": 6, "Judg": 7, "Ruth": 8, "1Sam": 9, "2Sam": 10,
    "1Kgs": 11, "2Kgs": 12, "1Chr": 13, "2Chr": 14, "Ezra": 15,
    "Neh": 16, "Esth": 17, "Job": 18, "Ps": 19, "Prov": 20,
    "Eccl": 21, "Song": 22, "Isa": 23, "Jer": 24, "Lam": 25,
    "Ezek": 26, "Dan": 27, "Hos": 28, "Joel": 29, "Amos": 30,
    "Obad": 31, "Jonah": 32, "Mic": 33, "Nah": 34, "Hab": 35,
    "Zeph": 36, "Hag": 37, "Zech": 38, "Mal": 39,
    "Matt": 40, "Mark": 41, "Luke": 42, "John": 43,
    "Acts": 44, "Rom": 45, "1Cor": 46, "2Cor": 47, "Gal": 48,
    "Eph": 49, "Phil": 50, "Col": 51, "1Thess": 52, "2Thess": 53,
    "1Tim": 54, "2Tim": 55, "Titus": 56, "Phlm": 57, "Heb": 58,
    "Jas": 59, "1Pet": 60, "2Pet": 61, "1John": 62, "2John": 63,
    "3John": 64, "Jude": 65, "Rev": 66,
}


def _parse_verse(ref: str) -> tuple[int, int, int] | None:
    """'Gen.1.1' → (book_num, chapter, verse). None on parse failure."""
    parts = ref.split(".")
    if len(parts) != 3:
        return None
    book_abbr, chapter, verse = parts[0], parts[1], parts[2]
    book_num = BOOK_ABBR.get(book_abbr)
    if book_num is None:
        return None
    try:
        return book_num, int(chapter), int(verse)
    except ValueError:
        return None


def _parse_to_verse(ref: str) -> tuple[int, int, int, int] | None:
    """'Gen.1.1' or 'Gen.1.1-Gen.1.3' → (book, ch, v_start, v_end). None on failure."""
    if "-" in ref:
        parts = ref.split("-", 1)
        from_parsed = _parse_verse(parts[0])
        to_parsed = _parse_verse(parts[1])
        if from_parsed is None or to_parsed is None:
            return None
        book, chapter, v_start = from_parsed
        _, _, v_end = to_parsed
        return book, chapter, v_start, v_end
    parsed = _parse_verse(ref)
    if parsed is None:
        return None
    book, chapter, verse = parsed
    return book, chapter, verse, verse


def download_crossref_db(url: str = ZIP_URL, output: str = OUTPUT_PATH) -> str:
    if os.path.exists(output):
        print(f"이미 존재함: {output}")
        return output

    print(f"다운로드 중: {url}")
    data, _ = urllib.request.urlretrieve(url)
    print("압축 해제 및 SQLite 변환 중...")

    rows = []
    with zipfile.ZipFile(data) as zf:
        tsv_name = next(n for n in zf.namelist() if n.endswith(".txt") or n.endswith(".tsv"))
        with zf.open(tsv_name) as f:
            content = io.TextIOWrapper(f, encoding="utf-8")
            next(content)  # header line
            for line in content:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 3:
                    continue
                from_ref, to_ref, votes_str = parts[0], parts[1], parts[2]
                from_parsed = _parse_verse(from_ref)
                to_parsed = _parse_to_verse(to_ref)
                if from_parsed is None or to_parsed is None:
                    continue
                f_book, f_ch, f_v = from_parsed
                t_book, t_ch, t_v_start, t_v_end = to_parsed
                try:
                    votes = int(votes_str)
                except ValueError:
                    votes = 0
                rows.append((f_book, f_ch, f_v, t_book, t_ch, t_v_start, t_v_end, votes))

    conn = sqlite3.connect(output)
    conn.execute("""
        CREATE TABLE cross_references (
            from_book INTEGER, from_chapter INTEGER, from_verse INTEGER,
            to_book INTEGER, to_chapter INTEGER,
            to_verse_start INTEGER, to_verse_end INTEGER,
            votes INTEGER
        )
    """)
    conn.executemany("INSERT INTO cross_references VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()

    print(f"완료: {output} ({len(rows):,}개 레코드)")
    return output


if __name__ == "__main__":
    download_crossref_db()
