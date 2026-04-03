import logging

import discord

from app.services.agent import run_agent

DISCORD_MAX_LENGTH = 2000

logger = logging.getLogger(__name__)


class DMBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # privileged — must be enabled in Discord Dev Portal
        super().__init__(intents=intents)
        # Per-user conversation history keyed by Discord user ID.
        self._histories: dict[int, list[dict]] = {}

    async def on_ready(self):
        logger.info(f"Discord bot logged in as {self.user}")

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not isinstance(message.channel, discord.DMChannel):
            return

        logger.info(f"DM from {message.author}: {message.content!r}")

        history = self._histories.get(message.author.id, [])

        async with message.channel.typing():
            try:
                reply, updated_history = await run_agent(message.content, history)
                self._histories[message.author.id] = updated_history
            except Exception as e:
                logger.error(f"run_agent failed: {e}", exc_info=True)
                await message.channel.send(f"Sorry, something went wrong: {e}")
                return

        for chunk in _chunk(reply):
            await message.channel.send(chunk)


def _chunk(text: str) -> list[str]:
    """Split text into chunks that fit within Discord's message length limit."""
    return [text[i : i + DISCORD_MAX_LENGTH] for i in range(0, len(text), DISCORD_MAX_LENGTH)]
