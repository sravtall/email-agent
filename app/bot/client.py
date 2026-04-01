from collections.abc import Awaitable, Callable

import discord

from app.services.llm import ask_claude


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
            reply = await self._ask(message.content)
        await message.channel.send(reply)
