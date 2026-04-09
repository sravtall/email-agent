"""Email agent: routes natural-language messages to Gmail tool calls via Claude."""
import asyncio
import logging
from typing import Any

import anthropic

from app.config import ANTHROPIC_API_KEY
from app.services import gmail_tools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an email assistant that manages a Gmail inbox via SMS commands.

RESPONSE FORMAT:
- Keep replies under 160 characters whenever possible.
- Be direct. No greetings, no sign-offs.
- When listing emails, use compact lines: "1. Alice - Meeting notes"

CONFIRMATION RULE:
- Before calling send_email, send_reply, label_email, or empty_spam you MUST ask the user to confirm.
- Format: "Send to <recipient>: '<preview>'? Reply YES to confirm."
- Only call the tool when the user's message is an explicit YES / confirm / go ahead / do it.
- If they say NO or anything else, cancel and say so in one short line.

TOOL NOTES:
- fetch_recent_emails: lists inbox, returns id/subject/sender/snippet per email.
- get_email_body: reads full body of one email by id.
- send_email: composes and sends a new email (confirm first).
- send_reply: sends an in-thread reply (confirm first).
- mark_as_read: marks an email as read, no confirmation needed.
- empty_spam: moves all spam to trash (confirm first).
- label_email: applies a label to an email (confirm first).
"""

GMAIL_TOOLS: list[dict] = [
    {
        "name": "fetch_recent_emails",
        "description": (
            "Fetch the most recent emails from a Gmail inbox category. "
            "Returns subject, sender, snippet, and message ID for each."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "n": {
                    "type": "integer",
                    "description": "How many recent emails to fetch (default 5).",
                },
                "category": {
                    "type": "string",
                    "description": (
                        "Inbox tab to read from. "
                        "Options: inbox (default), primary, promotions, social, updates, forums."
                    ),
                    "enum": ["inbox", "primary", "promotions", "social", "updates", "forums"],
                },
                "filter_spam": {
                    "type": "boolean",
                    "description": "Exclude spam emails from results (default true).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_email_body",
        "description": "Retrieve the full plain-text body of an email by its Gmail message ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The Gmail message ID of the email to read.",
                }
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "send_email",
        "description": (
            "Compose and send a new email to any recipient. "
            "MUST be confirmed by the user before calling."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address.",
                },
                "subject": {
                    "type": "string",
                    "description": "Subject line of the email.",
                },
                "body": {
                    "type": "string",
                    "description": "Plain-text body of the email.",
                },
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "send_reply",
        "description": (
            "Send a reply to an email keeping it in the same thread. "
            "MUST be confirmed by the user before calling."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The Gmail message ID of the email to reply to.",
                },
                "body": {
                    "type": "string",
                    "description": "The plain-text body of the reply.",
                },
            },
            "required": ["message_id", "body"],
        },
    },
    {
        "name": "empty_spam",
        "description": (
            "Move all emails in the spam folder to trash. "
            "Capped at 50 emails per call for safety. "
            "MUST be confirmed by the user before calling."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "max_emails": {
                    "type": "integer",
                    "description": "Maximum number of spam emails to trash (default 50).",
                }
            },
            "required": [],
        },
    },
    {
        "name": "mark_as_read",
        "description": "Mark an email as read by removing the UNREAD label.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The Gmail message ID of the email to mark as read.",
                }
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "label_email",
        "description": (
            "Apply a Gmail label to an email by message ID. "
            "Creates the label if it doesn't exist. "
            "MUST be confirmed by the user before calling."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The Gmail message ID of the email to label.",
                },
                "label": {
                    "type": "string",
                    "description": "Label name to apply, e.g. 'urgent', 'follow-up'.",
                },
            },
            "required": ["message_id", "label"],
        },
    },
]

_TOOL_MAP = {
    "fetch_recent_emails": gmail_tools.fetch_recent_emails,
    "get_email_body": gmail_tools.get_email_body,
    "send_email": gmail_tools.send_email,
    "send_reply": gmail_tools.send_reply,
    "empty_spam": gmail_tools.empty_spam,
    "mark_as_read": gmail_tools.mark_as_read,
    "label_email": gmail_tools.label_email,
}

_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


async def _call_tool(name: str, tool_input: dict) -> Any:
    fn = _TOOL_MAP[name]
    return await asyncio.to_thread(fn, **tool_input)


async def run_agent(
    user_message: str,
    history: list[dict] | None = None,
) -> tuple[str, list[dict]]:
    """Run one user turn through the email agent.

    Returns (reply_text, updated_history).
    Pass history back on subsequent calls to maintain conversation context.
    """
    messages = list(history or [])
    messages.append({"role": "user", "content": user_message})

    while True:
        response = await _client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=GMAIL_TOOLS,
            messages=messages,
        )

        # Always append the full content list — tool_use blocks must be preserved.
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            text = next((b.text for b in response.content if b.type == "text"), "")
            return text, messages

        if response.stop_reason != "tool_use":
            text = next((b.text for b in response.content if b.type == "text"), "")
            return text, messages

        # Execute every tool call and collect results.
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            logger.info("tool=%s input=%s", block.name, block.input)
            try:
                result = await _call_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })
            except Exception as exc:
                logger.error("tool %s failed: %s", block.name, exc)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": f"Error: {exc}",
                    "is_error": True,
                })

        messages.append({"role": "user", "content": tool_results})
