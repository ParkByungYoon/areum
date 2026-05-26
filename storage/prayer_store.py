from datetime import datetime


def save_prayer(
    concern: str,
    verse: dict,
    connection: str,
    filepath: str = "prayers.md",
):
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    ref = f"{verse['book']} {verse['chapter']}:{verse['verse']}"
    entry = (
        f"\n---\n"
        f"## {date_str}\n\n"
        f"**기도제목**: {concern}\n\n"
        f"**말씀**: {ref}\n"
        f"> {verse['text']}\n\n"
        f"**연결**: {connection}\n"
    )
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(entry)


def load_prayers(filepath: str = "prayers.md") -> str:
    try:
        with open(filepath, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""
