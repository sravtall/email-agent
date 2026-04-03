import discord
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.bot.client import DMBot, _chunk


@pytest.fixture
def bot():
    return DMBot()


def make_dm_message(content: str = "read my inbox", author_id: int = 1) -> MagicMock:
    message = MagicMock(spec=discord.Message)
    message.author.bot = False
    message.author.id = author_id
    message.content = content
    dm_channel = MagicMock(spec=discord.DMChannel)
    dm_channel.typing.return_value.__aenter__ = AsyncMock(return_value=None)
    dm_channel.typing.return_value.__aexit__ = AsyncMock(return_value=False)
    message.channel = dm_channel
    return message


async def test_ignores_bot_messages(bot):
    message = MagicMock(spec=discord.Message)
    message.author.bot = True
    with patch("app.bot.client.run_agent", new_callable=AsyncMock) as mock_agent:
        await bot.on_message(message)
        mock_agent.assert_not_awaited()


async def test_ignores_guild_messages(bot):
    message = MagicMock(spec=discord.Message)
    message.author.bot = False
    message.channel = MagicMock(spec=discord.TextChannel)
    with patch("app.bot.client.run_agent", new_callable=AsyncMock) as mock_agent:
        await bot.on_message(message)
        mock_agent.assert_not_awaited()


async def test_replies_to_dm(bot):
    message = make_dm_message("read my inbox", author_id=42)
    with patch("app.bot.client.run_agent", new_callable=AsyncMock,
               return_value=("Mocked reply", [])) as mock_agent:
        await bot.on_message(message)
        mock_agent.assert_awaited_once_with("read my inbox", [])
        message.channel.send.assert_awaited_once_with("Mocked reply")


async def test_history_passed_on_second_message(bot):
    first_history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    message = make_dm_message("follow-up", author_id=99)
    with patch("app.bot.client.run_agent", new_callable=AsyncMock,
               return_value=("reply", first_history)):
        await bot.on_message(message)

    message2 = make_dm_message("another message", author_id=99)
    with patch("app.bot.client.run_agent", new_callable=AsyncMock,
               return_value=("reply2", first_history)) as mock_agent:
        await bot.on_message(message2)
        mock_agent.assert_awaited_once_with("another message", first_history)


async def test_sends_error_message_on_failure(bot):
    message = make_dm_message()
    with patch("app.bot.client.run_agent", new_callable=AsyncMock,
               side_effect=Exception("API error")):
        await bot.on_message(message)
    message.channel.send.assert_awaited_once()
    assert "went wrong" in message.channel.send.call_args[0][0]


async def test_chunks_long_reply(bot):
    long_reply = "x" * 4500
    message = make_dm_message()
    with patch("app.bot.client.run_agent", new_callable=AsyncMock,
               return_value=(long_reply, [])):
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
