import logging
from collections.abc import Awaitable, Callable

import discord

from app.services.llm import ask_claude

DISCORD_MAX_LENGTH = 2000

logger = logging.getLogger(__name__)


class DMBot(discord.Client):
    def __init__(self, ask_fn: Callable[[str], Awaitable[str]] = ask_claude):
        intents = discord.Intents.default()
        intents.message_content = True  # privileged — must be enabled in Discord Dev Portal
        super().__init__(intents=intents)
        self._ask = ask_fn

    async def on_ready(self):
        logger.info(f"Discord bot logged in as {self.user}")

    async def on_message(self, message: discord.Message):
        logger.debug(f"on_message fired — author.bot={message.author.bot}, channel type={type(message.channel).__name__}, content={message.content!r}")

        if message.author.bot:
            logger.debug("Ignored: message is from a bot")
            return
        if not isinstance(message.channel, discord.DMChannel):
            logger.debug(f"Ignored: channel is {type(message.channel).__name__}, not DMChannel")
            return

        logger.info(f"Processing DM from {message.author}: {message.content!r}")

        async with message.channel.typing():
            try:
                reply = await self._ask(message.content)
            except Exception as e:
                logger.error(f"ask_claude failed: {e}", exc_info=True)
                await message.channel.send(f"Sorry, something went wrong: {e}")
                return

        for chunk in _chunk(reply):
            await message.channel.send(chunk)


def _chunk(text: str) -> list[str]:
    """Split text into chunks that fit within Discord's message length limit."""
    return [text[i : i + DISCORD_MAX_LENGTH] for i in range(0, len(text), DISCORD_MAX_LENGTH)]
