import anthropic
from app.config import ANTHROPIC_API_KEY

SYSTEM_PROMPT = """You are an email assistant agent. Users send you messages to manage their email inbox.
Interpret the command and respond with what action you would take or what information you would provide.
Keep responses concise."""

_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


async def ask_claude(message: str) -> str:
    response = await _client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": message}],
    )
    return next((b.text for b in response.content if b.type == "text"), "")
