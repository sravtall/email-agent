import discord
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.bot.client import DMBot


@pytest.fixture
def mock_ask():
    return AsyncMock(return_value="Mocked Claude reply")


@pytest.fixture
def bot(mock_ask):
    return DMBot(ask_fn=mock_ask)


async def test_ignores_bot_messages(bot):
    message = MagicMock(spec=discord.Message)
    message.author.bot = True
    await bot.on_message(message)
    bot._ask.assert_not_awaited()


async def test_ignores_guild_messages(bot):
    message = MagicMock(spec=discord.Message)
    message.author.bot = False
    message.channel = MagicMock(spec=discord.TextChannel)
    await bot.on_message(message)
    bot._ask.assert_not_awaited()


async def test_replies_to_dm(bot, mock_ask):
    message = MagicMock(spec=discord.Message)
    message.author.bot = False
    message.content = "read my inbox"

    dm_channel = MagicMock(spec=discord.DMChannel)
    dm_channel.typing.return_value.__aenter__ = AsyncMock(return_value=None)
    dm_channel.typing.return_value.__aexit__ = AsyncMock(return_value=False)
    message.channel = dm_channel

    await bot.on_message(message)

    mock_ask.assert_awaited_once_with("read my inbox")
    dm_channel.send.assert_awaited_once_with("Mocked Claude reply")
