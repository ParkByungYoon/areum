import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

SYSTEM_PROMPT = """기독교인의 고민을 듣고 성경 말씀을 따뜻하게 연결해주는 역할입니다.

규칙:
- AI가 해석하거나 방향을 제시하지 않는다. 연결만 한다.
- 2~3문장으로 간결하게.
- 말씀을 직접 인용하지 말고, 고민과 말씀의 연결점을 짧게 표현한다.
- 따뜻하되 과하지 않게."""


def generate_connection(user_concern: str, verse: dict) -> str:
    prompt = (
        f"사용자의 고민: {user_concern}\n\n"
        f"말씀: 누가복음 {verse['chapter']}:{verse['verse']}\n"
        f"{verse['text']}\n\n"
        "이 말씀과 고민을 연결하는 짧은 메시지를 작성하세요."
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()
