import discord
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.bot.client import DMBot, _chunk


@pytest.fixture
def mock_ask():
    return AsyncMock(return_value="Mocked Claude reply")


@pytest.fixture
def bot(mock_ask):
    return DMBot(ask_fn=mock_ask)


def make_dm_message(content: str = "read my inbox") -> MagicMock:
    message = MagicMock(spec=discord.Message)
    message.author.bot = False
    message.content = content
    dm_channel = MagicMock(spec=discord.DMChannel)
    dm_channel.typing.return_value.__aenter__ = AsyncMock(return_value=None)
    dm_channel.typing.return_value.__aexit__ = AsyncMock(return_value=False)
    message.channel = dm_channel
    return message


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
    message = make_dm_message("read my inbox")
    await bot.on_message(message)
    mock_ask.assert_awaited_once_with("read my inbox")
    message.channel.send.assert_awaited_once_with("Mocked Claude reply")


async def test_sends_error_message_on_failure(bot):
    bot._ask = AsyncMock(side_effect=Exception("API error"))
    message = make_dm_message()
    await bot.on_message(message)
    message.channel.send.assert_awaited_once()
    assert "went wrong" in message.channel.send.call_args[0][0]


async def test_chunks_long_reply(bot):
    long_reply = "x" * 4500
    bot._ask = AsyncMock(return_value=long_reply)
    message = make_dm_message()
    await bot.on_message(message)
    assert message.channel.send.await_count == 3  # 2000 + 2000 + 500


def test_chunk_short_text():
    assert _chunk("hello") == ["hello"]


def test_chunk_exact_limit():
    text = "a" * 2000
    assert _chunk(text) == [text]


def test_chunk_long_text():
    text = "a" * 4500
    chunks = _chunk(text)
    assert len(chunks) == 3
    assert len(chunks[0]) == 2000
    assert len(chunks[1]) == 2000
    assert len(chunks[2]) == 500
