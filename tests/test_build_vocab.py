import sys
sys.path.insert(0, ".")
from data.build_vocab import build_vocab

SAMPLE_TAGGED = [
    {
        "book": "누가복음", "chapter": 1, "verse": 1, "text": "...",
        "tags": {"emotion": ["두려움", "감사"], "situation": ["소명"]},
    },
    {
        "book": "누가복음", "chapter": 1, "verse": 2, "text": "...",
        "tags": {"emotion": ["기쁨", "감사"], "situation": ["관계", "소명"]},
    },
]


def test_returns_dict_with_two_axes():
    vocab = build_vocab(SAMPLE_TAGGED)
    assert "emotion" in vocab
    assert "situation" in vocab


def test_deduplicates_tags():
    vocab = build_vocab(SAMPLE_TAGGED)
    assert vocab["emotion"].count("감사") == 1


def test_collects_all_tags():
    vocab = build_vocab(SAMPLE_TAGGED)
    assert set(vocab["emotion"]) == {"두려움", "감사", "기쁨"}
    assert set(vocab["situation"]) == {"소명", "관계"}


def test_tags_are_sorted():
    vocab = build_vocab(SAMPLE_TAGGED)
    assert vocab["emotion"] == sorted(vocab["emotion"])
    assert vocab["situation"] == sorted(vocab["situation"])
