"""Unit tests for gmail_tools — all Gmail API calls are mocked."""
import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode()


def _make_service():
    """Return a fully-wired mock of the Gmail service object."""
    svc = MagicMock()
    return svc


# Patch token.json existence so _get_service() doesn't error on missing file
FAKE_TOKEN = json.dumps({
    "token": "fake",
    "refresh_token": "fake_refresh",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_id": "fake_client",
    "client_secret": "fake_secret",
    "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
})


# ---------------------------------------------------------------------------
# fetch_recent_emails
# ---------------------------------------------------------------------------

class TestFetchRecentEmails:
    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_returns_correct_fields(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc

        svc.users().messages().list().execute.return_value = {
            "messages": [{"id": "abc123"}]
        }
        svc.users().messages().get().execute.return_value = {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Hello"},
                    {"name": "From", "value": "alice@example.com"},
                ]
            },
            "snippet": "Short preview",
        }

        from app.services.gmail_tools import fetch_recent_emails
        result = fetch_recent_emails(n=1)

        assert len(result) == 1
        assert result[0]["id"] == "abc123"
        assert result[0]["subject"] == "Hello"
        assert result[0]["sender"] == "alice@example.com"
        assert result[0]["snippet"] == "Short preview"

    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_empty_inbox(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc
        svc.users().messages().list().execute.return_value = {}

        from app.services.gmail_tools import fetch_recent_emails
        assert fetch_recent_emails() == []

    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_missing_token_raises(self, mock_token_file):
        mock_token_file.exists.return_value = False
        from app.services.gmail_tools import fetch_recent_emails
        with pytest.raises(FileNotFoundError):
            fetch_recent_emails()

    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_promotions_category_uses_correct_labels(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc
        svc.users().messages().list().execute.return_value = {}

        from app.services.gmail_tools import fetch_recent_emails
        fetch_recent_emails(n=5, category="promotions")

        list_call = svc.users().messages().list.call_args
        assert "CATEGORY_PROMOTIONS" in list_call.kwargs["labelIds"]
        assert "INBOX" in list_call.kwargs["labelIds"]

    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_unknown_category_falls_back_to_inbox(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc
        svc.users().messages().list().execute.return_value = {}

        from app.services.gmail_tools import fetch_recent_emails
        fetch_recent_emails(category="nonexistent")

        list_call = svc.users().messages().list.call_args
        assert list_call.kwargs["labelIds"] == ["INBOX"]


# ---------------------------------------------------------------------------
# get_email_body
# ---------------------------------------------------------------------------

class TestGetEmailBody:
    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_plain_text_payload(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc
        svc.users().messages().get().execute.return_value = {
            "payload": {
                "mimeType": "text/plain",
                "body": {"data": _b64("Hello world")},
            }
        }

        from app.services.gmail_tools import get_email_body
        assert get_email_body("abc123") == "Hello world"

    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_multipart_picks_text_plain(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc
        svc.users().messages().get().execute.return_value = {
            "payload": {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": _b64("Plain text part")}},
                    {"mimeType": "text/html", "body": {"data": _b64("<b>HTML part</b>")}},
                ],
            }
        }

        from app.services.gmail_tools import get_email_body
        assert get_email_body("abc123") == "Plain text part"

    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_no_body_returns_empty(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc
        svc.users().messages().get().execute.return_value = {
            "payload": {"mimeType": "text/html", "body": {"data": _b64("<b>html</b>")}}
        }

        from app.services.gmail_tools import get_email_body
        assert get_email_body("abc123") == ""


# ---------------------------------------------------------------------------
# send_reply
# ---------------------------------------------------------------------------

class TestSendReply:
    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_sends_with_correct_thread(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc
        svc.users().messages().get().execute.return_value = {
            "threadId": "thread99",
            "payload": {
                "headers": [
                    {"name": "From", "value": "bob@example.com"},
                    {"name": "Subject", "value": "Test subject"},
                    {"name": "Message-ID", "value": "<orig@mail>"},
                    {"name": "References", "value": ""},
                ]
            },
        }
        svc.users().messages().send().execute.return_value = {"id": "sent1", "threadId": "thread99"}

        from app.services.gmail_tools import send_reply
        result = send_reply("orig_id", "My reply")

        assert result["threadId"] == "thread99"
        send_call = svc.users().messages().send.call_args
        body = send_call.kwargs["body"]
        assert body["threadId"] == "thread99"
        raw = base64.urlsafe_b64decode(body["raw"]).decode()
        assert "Re: Test subject" in raw
        assert "My reply" in raw

    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_does_not_double_re_prefix(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc
        svc.users().messages().get().execute.return_value = {
            "threadId": "t1",
            "payload": {
                "headers": [
                    {"name": "From", "value": "x@x.com"},
                    {"name": "Subject", "value": "Re: Already replied"},
                    {"name": "Message-ID", "value": "<id>"},
                    {"name": "References", "value": ""},
                ]
            },
        }
        svc.users().messages().send().execute.return_value = {"id": "s1", "threadId": "t1"}

        from app.services.gmail_tools import send_reply
        send_reply("msg1", "body")
        body = svc.users().messages().send.call_args.kwargs["body"]
        raw = base64.urlsafe_b64decode(body["raw"]).decode()
        assert "Re: Re:" not in raw


# ---------------------------------------------------------------------------
# send_email
# ---------------------------------------------------------------------------

class TestSendEmail:
    def _decode_mime(self, svc) -> "email.message.Message":
        import email as stdlib_email
        body = svc.users().messages().send.call_args.kwargs["body"]
        raw = base64.urlsafe_b64decode(body["raw"])
        return stdlib_email.message_from_bytes(raw)

    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_sends_correct_headers(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc
        svc.users().messages().send().execute.return_value = {"id": "new1"}

        from app.services.gmail_tools import send_email
        result = send_email("bob@example.com", "Hello", "Hi Bob!")

        assert result["id"] == "new1"
        msg = self._decode_mime(svc)
        assert msg["To"] == "bob@example.com"
        assert msg["Subject"] == "Hello"

    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_sends_html_and_plain_parts(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc
        svc.users().messages().send().execute.return_value = {"id": "new2"}

        from app.services.gmail_tools import send_email
        send_email("alice@example.com", "Test", "Hello\n\nSecond paragraph")

        msg = self._decode_mime(svc)
        parts = {p.get_content_type(): p.get_payload(decode=True).decode() for p in msg.walk()
                 if not p.is_multipart()}
        assert "text/plain" in parts
        assert "text/html" in parts
        assert "<p>" in parts["text/html"]
        assert "Hello" in parts["text/plain"]

    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_no_thread_id_in_payload(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc
        svc.users().messages().send().execute.return_value = {"id": "new3"}

        from app.services.gmail_tools import send_email
        send_email("alice@example.com", "Test", "body")

        body = svc.users().messages().send.call_args.kwargs["body"]
        assert "threadId" not in body


# ---------------------------------------------------------------------------
# mark_as_read
# ---------------------------------------------------------------------------

class TestMarkAsRead:
    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_removes_unread_label(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc
        svc.users().messages().modify().execute.return_value = {"id": "msg1"}

        from app.services.gmail_tools import mark_as_read
        result = mark_as_read("msg1")

        assert result["id"] == "msg1"
        modify_call = svc.users().messages().modify.call_args
        assert modify_call.kwargs["body"]["removeLabelIds"] == ["UNREAD"]
        assert modify_call.kwargs["id"] == "msg1"


# ---------------------------------------------------------------------------
# label_email
# ---------------------------------------------------------------------------

class TestLabelEmail:
    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_uses_existing_label(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc
        svc.users().labels().list().execute.return_value = {
            "labels": [{"id": "Label_1", "name": "urgent"}]
        }
        svc.users().messages().modify().execute.return_value = {"id": "msg1"}

        from app.services.gmail_tools import label_email
        label_email("msg1", "urgent")

        modify_call = svc.users().messages().modify.call_args
        assert modify_call.kwargs["body"]["addLabelIds"] == ["Label_1"]
        svc.users().labels().create.assert_not_called()

    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_creates_label_when_missing(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc
        svc.users().labels().list().execute.return_value = {"labels": []}
        svc.users().labels().create().execute.return_value = {"id": "Label_new", "name": "new-label"}
        svc.users().messages().modify().execute.return_value = {"id": "msg1"}

        from app.services.gmail_tools import label_email
        label_email("msg1", "new-label")

        create_calls = [
            c for c in svc.users().labels().create.call_args_list
            if c.kwargs.get("body") == {"name": "new-label"}
        ]
        assert len(create_calls) == 1
        modify_call = svc.users().messages().modify.call_args
        assert modify_call.kwargs["body"]["addLabelIds"] == ["Label_new"]

    @patch("app.services.gmail_tools.build")
    @patch("app.services.gmail_tools.Credentials.from_authorized_user_file")
    @patch("app.services.gmail_tools._TOKEN_FILE")
    def test_label_lookup_case_insensitive(self, mock_token_file, mock_creds, mock_build):
        mock_token_file.exists.return_value = True
        mock_token_file.__str__ = lambda s: "token.json"
        mock_creds.return_value = MagicMock(expired=False)

        svc = _make_service()
        mock_build.return_value = svc
        svc.users().labels().list().execute.return_value = {
            "labels": [{"id": "Label_X", "name": "Urgent"}]
        }
        svc.users().messages().modify().execute.return_value = {"id": "msg1"}

        from app.services.gmail_tools import label_email
        label_email("msg1", "URGENT")

        modify_call = svc.users().messages().modify.call_args
        assert modify_call.kwargs["body"]["addLabelIds"] == ["Label_X"]
