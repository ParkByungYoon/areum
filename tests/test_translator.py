import sys
sys.path.insert(0, ".")
from unittest.mock import patch, MagicMock
from core.translator import generate_connection

SAMPLE_VERSE = {
    "book": "누가복음",
    "chapter": 15,
    "verse": 20,
    "text": "아들이 아직도 먼 거리에 있을 때에, 그의 아버지가 그를 보고 측은히 여겨 달려가 목을 안고 입을 맞추었다.",
}


def test_generate_connection_returns_string():
    mock_response = MagicMock()
    mock_response.content[0].text = "지금 혼자라는 느낌이 드시는군요. 이 말씀이 생각났어요."
    with patch("core.translator.client.messages.create", return_value=mock_response):
        result = generate_connection("혼자인 것 같아서 외로워요", SAMPLE_VERSE)
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_connection_strips_whitespace():
    mock_response = MagicMock()
    mock_response.content[0].text = "  연결 메시지  \n"
    with patch("core.translator.client.messages.create", return_value=mock_response):
        result = generate_connection("힘들어요", SAMPLE_VERSE)
    assert result == "연결 메시지"
