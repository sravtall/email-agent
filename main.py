from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Email Agent API", version="0.1.0")


class SMSCommand(BaseModel):
    sender: str
    message: str


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/sms")
def receive_sms(command: SMSCommand):
    """Receive an SMS command and route it to the appropriate email action."""
    return {
        "received_from": command.sender,
        "message": command.message,
        "status": "received",
    }
