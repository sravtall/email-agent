from fastapi import FastAPI
from app.config import ANTHROPIC_API_KEY
from app.routers import sms

app = FastAPI(title="Email Agent API", version="0.3.0")

app.include_router(sms.router)


@app.on_event("startup")
def check_config():
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")


@app.get("/health")
def health_check():
    return {"status": "ok"}
