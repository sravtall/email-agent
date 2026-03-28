from fastapi import APIRouter
from pydantic import BaseModel
from app.services.llm import ask_claude

router = APIRouter(tags=["sms"])


class SMSCommand(BaseModel):
    sender: str
    message: str


@router.post("/sms")
def receive_sms(command: SMSCommand):
    """JSON endpoint for local/CLI testing."""
    reply = ask_claude(command.message)
    return {
        "received_from": command.sender,
        "message": command.message,
        "reply": reply,
        "status": "processed",
    }
