import json


def extract_luke(bible_path: str = "bible.json") -> list[dict]:
    with open(bible_path, encoding="utf-8") as f:
        data = json.load(f)
    luke = next((b for b in data if b["korean"] == "누가복음"), None)
    if luke is None:
        raise ValueError(f"'누가복음' not found in {bible_path}. Check the file schema.")
    verses = []
    for chapter in luke["chapters"]:
        for v in chapter["verses"]:
            verses.append({
                "book": "누가복음",
                "chapter": int(v["chapterNum"]),
                "verse": int(v["verseNum"]),
                "text": v["verse"],
            })
    return verses


if __name__ == "__main__":
    verses = extract_luke()
    with open("data/luke_raw.json", "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)
    print(f"추출 완료: {len(verses)}절")
