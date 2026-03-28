from fastapi import FastAPI
from app.routers import sms

app = FastAPI(title="Email Agent API", version="0.3.0")

app.include_router(sms.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
