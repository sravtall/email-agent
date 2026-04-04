"""Gmail API helpers used by the email agent."""
import base64
import email as email_lib
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

_ROOT = Path(__file__).parent.parent.parent
_TOKEN_FILE = _ROOT / "token.json"
_CREDENTIALS_FILE = _ROOT / "credentials.json"


def _get_service() -> Any:
    if not _TOKEN_FILE.exists():
        raise FileNotFoundError(
            "token.json not found. Run auth.py first to complete the OAuth flow."
        )
    creds = Credentials.from_authorized_user_file(str(_TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _TOKEN_FILE.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def fetch_recent_emails(n: int = 5) -> list[dict]:
    """Return the n most recent inbox messages (subject, sender, snippet, id)."""
    service = _get_service()
    result = service.users().messages().list(userId="me", maxResults=n, labelIds=["INBOX"]).execute()
    messages = result.get("messages", [])
    emails = []
    for msg in messages:
        detail = service.users().messages().get(userId="me", id=msg["id"], format="metadata",
                                                 metadataHeaders=["Subject", "From"]).execute()
        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        emails.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "(no subject)"),
            "sender": headers.get("From", "(unknown)"),
            "snippet": detail.get("snippet", ""),
        })
    return emails


def get_email_body(message_id: str) -> str:
    """Return the plain-text body of the given message."""
    service = _get_service()
    detail = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    return _extract_body(detail["payload"])


def _extract_body(payload: dict) -> str:
    mime_type = payload.get("mimeType", "")
    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    if mime_type.startswith("multipart/"):
        for part in payload.get("parts", []):
            body = _extract_body(part)
            if body:
                return body
    return ""


def send_reply(message_id: str, body: str) -> dict:
    """Send a reply to the given message, keeping it in the same thread."""
    service = _get_service()
    original = service.users().messages().get(
        userId="me", id=message_id, format="metadata",
        metadataHeaders=["Subject", "From", "Message-ID", "References"]
    ).execute()

    headers = {h["name"]: h["value"] for h in original["payload"]["headers"]}
    to = headers.get("From", "")
    subject = headers.get("Subject", "")
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    message_id_header = headers.get("Message-ID", "")
    references = headers.get("References", "")
    thread_id = original["threadId"]

    raw_message = (
        f"To: {to}\r\n"
        f"Subject: {subject}\r\n"
        f"In-Reply-To: {message_id_header}\r\n"
        f"References: {references} {message_id_header}".strip() + "\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"{body}"
    )
    encoded = base64.urlsafe_b64encode(raw_message.encode("utf-8")).decode("utf-8")
    sent = service.users().messages().send(
        userId="me",
        body={"raw": encoded, "threadId": thread_id}
    ).execute()
    return sent


def send_email(to: str, subject: str, body: str) -> dict:
    """Send a new email (not a reply)."""
    service = _get_service()
    raw_message = (
        f"To: {to}\r\n"
        f"Subject: {subject}\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"{body}"
    )
    encoded = base64.urlsafe_b64encode(raw_message.encode("utf-8")).decode("utf-8")
    sent = service.users().messages().send(
        userId="me",
        body={"raw": encoded}
    ).execute()
    return sent


def label_email(message_id: str, label: str) -> dict:
    """Apply a Gmail label (by name) to the given message, creating it if needed."""
    service = _get_service()
    label_id = _get_or_create_label(service, label)
    result = service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [label_id]}
    ).execute()
    return result


def _get_or_create_label(service: Any, name: str) -> str:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for lbl in labels:
        if lbl["name"].lower() == name.lower():
            return lbl["id"]
    created = service.users().labels().create(
        userId="me", body={"name": name}
    ).execute()
    return created["id"]
