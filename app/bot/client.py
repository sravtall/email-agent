from collections.abc import Awaitable, Callable

import discord

from app.services.llm import ask_claude

DISCORD_MAX_LENGTH = 2000


class DMBot(discord.Client):
    def __init__(self, ask_fn: Callable[[str], Awaitable[str]] = ask_claude):
        intents = discord.Intents.default()
        intents.message_content = True  # privileged — must be enabled in Discord Dev Portal
        super().__init__(intents=intents)
        self._ask = ask_fn

    async def on_ready(self):
        print(f"Discord bot logged in as {self.user}")

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not isinstance(message.channel, discord.DMChannel):
            return

        async with message.channel.typing():
            try:
                reply = await self._ask(message.content)
            except Exception as e:
                await message.channel.send(f"Sorry, something went wrong: {e}")
                return

        for chunk in _chunk(reply):
            await message.channel.send(chunk)


def _chunk(text: str) -> list[str]:
    """Split text into chunks that fit within Discord's message length limit."""
    return [text[i : i + DISCORD_MAX_LENGTH] for i in range(0, len(text), DISCORD_MAX_LENGTH)]
