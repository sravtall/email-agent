import os
import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Email Agent API", version="0.2.0")

SYSTEM_PROMPT = """You are an email assistant agent. Users send you SMS commands to manage their email inbox.
Interpret the command and respond with what action you would take or what information you would provide.
Keep responses concise — they will be sent back as SMS messages."""


def get_anthropic_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=api_key)


class SMSCommand(BaseModel):
    sender: str
    message: str


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/sms")
def receive_sms(command: SMSCommand):
    """Receive an SMS command, pass it to Claude, and return the response."""
    client = get_anthropic_client()

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": command.message}],
    )

    reply = next((b.text for b in response.content if b.type == "text"), "")

    return {
        "received_from": command.sender,
        "message": command.message,
        "reply": reply,
        "status": "processed",
    }
