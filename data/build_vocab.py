import json


def build_vocab(tagged_verses: list[dict]) -> dict:
    emotion_set = set()
    situation_set = set()
    for v in tagged_verses:
        emotion_set.update(v["tags"].get("emotion", []))
        situation_set.update(v["tags"].get("situation", []))
    return {
        "emotion": sorted(emotion_set),
        "situation": sorted(situation_set),
    }


if __name__ == "__main__":
    with open("data/luke_tagged.json", encoding="utf-8") as f:
        tagged = json.load(f)
    vocab = build_vocab(tagged)
    with open("data/tags.json", "w", encoding="utf-8") as f:
        json.dump(vocab, f, ensure_ascii=False, indent=2)
    print(f"감정 태그 {len(vocab['emotion'])}개, 상황 태그 {len(vocab['situation'])}개")
