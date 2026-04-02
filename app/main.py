import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bot.client import DMBot
from app.config import ANTHROPIC_API_KEY, DISCORD_BOT_TOKEN

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
    if not DISCORD_BOT_TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set. Add it to your .env file.")

    bot = DMBot()
    task = asyncio.create_task(bot.start(DISCORD_BOT_TOKEN))
    try:
        yield
    finally:
        await bot.close()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Email Agent API", version="0.5.0", lifespan=lifespan)


@app.get("/health")
def health_check():
    return {"status": "ok"}
