from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import ANTHROPIC_API_KEY


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
    yield


app = FastAPI(title="Email Agent API", version="0.4.0", lifespan=lifespan)


@app.get("/health")
def health_check():
    return {"status": "ok"}
