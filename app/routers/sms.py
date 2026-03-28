from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from app.config import TWILIO_AUTH_TOKEN
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


@router.post("/sms/twilio")
async def twilio_webhook(
    request: Request,
    Body: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
):
    """Twilio webhook — validates signature, calls Claude, returns TwiML."""
    if TWILIO_AUTH_TOKEN:
        validator = RequestValidator(TWILIO_AUTH_TOKEN)
        signature = request.headers.get("X-Twilio-Signature", "")
        form_data = dict(await request.form())
        if not validator.validate(str(request.url), form_data, signature):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    reply = ask_claude(Body)

    twiml = MessagingResponse()
    twiml.message(reply)
    return Response(content=str(twiml), media_type="application/xml")
