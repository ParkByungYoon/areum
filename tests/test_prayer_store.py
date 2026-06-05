import sys
import os
import tempfile

sys.path.insert(0, ".")
from storage.prayer_store import save_prayer, find_connection, init_db


def _tmp_db():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "prayers.db")
    init_db(path)
    return path


def test_save_creates_record_with_all_fields():
    db = _tmp_db()
    record = save_prayer("지훈", "외로워요", "오병이어", "오병이어", "마 14:13-21", db)
    assert record["user_id"] == "지훈"
    assert record["concern"] == "외로워요"
    assert record["episode_id"] == "오병이어"
    assert record["subtitle"] == "오병이어"
    assert record["passage_ref"] == "마 14:13-21"
    assert "id" in record and "date" in record


def test_save_appends_multiple_records():
    db = _tmp_db()
    save_prayer("지훈", "첫 번째", "에피소드A", "에피소드A", "마 1:1-5", db)
    save_prayer("지훈", "두 번째", "에피소드B", "에피소드B", "마 2:1-5", db)
    result = find_connection("지훈", "세 번째", "에피소드A", db)
    assert result is not None
    assert result["type"] == "same_episode"


def test_find_connection_returns_none_when_no_prayers():
    db = _tmp_db()
    result = find_connection("지훈", "외로워요", "오병이어", db)
    assert result is None


def test_find_connection_case1_same_episode():
    db = _tmp_db()
    save_prayer("지훈", "인간관계가 힘들다", "오병이어", "오병이어", "마 14:13-21", db)
    result = find_connection("지훈", "다시 힘들다", "오병이어", db)
    assert result is not None
    assert result["type"] == "same_episode"
    assert result["record"]["episode_id"] == "오병이어"
    assert "days_ago" in result


def test_find_connection_case1_returns_most_recent():
    db = _tmp_db()
    save_prayer("지훈", "첫 번 힘들다", "오병이어", "오병이어", "마 14:13-21", db)
    save_prayer("지훈", "두 번 힘들다", "오병이어", "오병이어", "마 14:13-21", db)
    result = find_connection("지훈", "또 힘들다", "오병이어", db)
    assert result["record"]["concern"] == "두 번 힘들다"


def test_find_connection_case2_similar_concern():
    db = _tmp_db()
    save_prayer("지훈", "아무것도 하기 싫다", "겟세마네", "겟세마네", "마 26:36-46", db)
    result = find_connection("지훈", "아무것도 못하겠다", "오병이어", db)
    assert result is not None
    assert result["type"] == "similar_concern"


def test_find_connection_case1_takes_priority_over_case2():
    db = _tmp_db()
    save_prayer("지훈", "비슷한 고민", "겟세마네", "겟세마네", "마 26:36-46", db)
    save_prayer("지훈", "같은 에피소드", "오병이어", "오병이어", "마 14:13-21", db)
    result = find_connection("지훈", "비슷한 고민", "오병이어", db)
    assert result["type"] == "same_episode"


def test_find_connection_is_isolated_by_user():
    db = _tmp_db()
    save_prayer("지훈", "힘들다", "오병이어", "오병이어", "마 14:13-21", db)
    result = find_connection("수진", "힘들다", "오병이어", db)
    assert result is None


def test_find_connection_case2_returns_none_when_score_zero():
    db = _tmp_db()
    save_prayer("지훈", "완전히 다른 주제", "겟세마네", "겟세마네", "마 26:36-46", db)
    result = find_connection("지훈", "xyz abc def", "오병이어", db)
    assert result is None
