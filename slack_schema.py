"""
slack_schema.py
JSON persistence layer for Slack message data tied to HaloPSA client accounts.
Stored in slack_data.json (gitignored).

Schema:
  message_id      — UUID4 string, unique per message
  client_id       — int, HaloPSA account ID
  client_name     — str
  channel         — str, Slack channel name (without #)
  sender_id       — str, Slack user ID (e.g. "U01ABC123")
  sender_name     — str
  sender_type     — "client_user" | "msp_agent"
  message_text    — str
  timestamp       — ISO 8601 UTC datetime string
  thread_ts       — str | None, parent message timestamp if this is a reply
  is_reply        — bool
  sentiment       — "positive" | "neutral" | "negative"
  ticket_reference — int | None, HaloPSA ticket ID if referenced
  tags            — list[str]
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field

_SLACK_DATA_PATH = os.path.join(os.path.dirname(__file__), "slack_data.json")

VALID_SENDER_TYPES = {"client_user", "msp_agent"}
VALID_SENTIMENTS = {"positive", "neutral", "negative"}


@dataclass
class SlackMessage:
    client_id: int
    client_name: str
    channel: str
    sender_id: str
    sender_name: str
    sender_type: str  # "client_user" | "msp_agent"
    message_text: str
    timestamp: str  # ISO 8601 UTC
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    thread_ts: str | None = None
    is_reply: bool = False
    sentiment: str = "neutral"  # "positive" | "neutral" | "negative"
    ticket_reference: int | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SlackMessage":
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            client_id=data["client_id"],
            client_name=data["client_name"],
            channel=data["channel"],
            sender_id=data["sender_id"],
            sender_name=data["sender_name"],
            sender_type=data["sender_type"],
            message_text=data["message_text"],
            timestamp=data["timestamp"],
            thread_ts=data.get("thread_ts"),
            is_reply=data.get("is_reply", False),
            sentiment=data.get("sentiment", "neutral"),
            ticket_reference=data.get("ticket_reference"),
            tags=data.get("tags", []),
        )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def load_slack_data() -> list[SlackMessage]:
    """Read slack_data.json; return empty list if absent or corrupt."""
    if not os.path.exists(_SLACK_DATA_PATH):
        return []
    try:
        with open(_SLACK_DATA_PATH, "r") as f:
            raw = json.load(f)
        return [SlackMessage.from_dict(m) for m in raw.get("messages", [])]
    except (json.JSONDecodeError, OSError, KeyError, TypeError):
        return []


def save_slack_data(messages: list[SlackMessage]) -> None:
    """Write messages atomically via os.replace() on a temp file."""
    dir_name = os.path.dirname(_SLACK_DATA_PATH) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump({"messages": [m.to_dict() for m in messages]}, f, indent=2)
        os.replace(tmp_path, _SLACK_DATA_PATH)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------


def add_message(message: SlackMessage) -> None:
    """Append a new message. Raises ValueError if message_id already exists."""
    messages = load_slack_data()
    existing_ids = {m.message_id for m in messages}
    if message.message_id in existing_ids:
        raise ValueError(f"Message with id {message.message_id!r} already exists.")
    messages.append(message)
    save_slack_data(messages)


def upsert_message(message: SlackMessage) -> None:
    """Insert or replace a message by message_id."""
    messages = load_slack_data()
    idx = next((i for i, m in enumerate(messages) if m.message_id == message.message_id), None)
    if idx is not None:
        messages[idx] = message
    else:
        messages.append(message)
    save_slack_data(messages)


def get_message_by_id(message_id: str) -> SlackMessage | None:
    """Return the message with the given ID, or None if not found."""
    for m in load_slack_data():
        if m.message_id == message_id:
            return m
    return None


def get_messages_for_client(client_id: int) -> list[SlackMessage]:
    """Return all messages associated with a HaloPSA client ID."""
    return [m for m in load_slack_data() if m.client_id == client_id]


def get_messages_by_channel(channel: str) -> list[SlackMessage]:
    """Return all messages in a given channel (case-insensitive)."""
    channel_lower = channel.lower()
    return [m for m in load_slack_data() if m.channel.lower() == channel_lower]


def get_messages_by_sentiment(sentiment: str) -> list[SlackMessage]:
    """Return all messages with a given sentiment ('positive', 'neutral', 'negative')."""
    return [m for m in load_slack_data() if m.sentiment == sentiment]


def delete_message(message_id: str) -> bool:
    """Remove a message by ID. Returns True if deleted, False if not found."""
    messages = load_slack_data()
    filtered = [m for m in messages if m.message_id != message_id]
    if len(filtered) == len(messages):
        return False
    save_slack_data(filtered)
    return True


def delete_messages_for_client(client_id: int) -> int:
    """Remove all messages for a client. Returns count of deleted messages."""
    messages = load_slack_data()
    kept = [m for m in messages if m.client_id != client_id]
    deleted = len(messages) - len(kept)
    save_slack_data(kept)
    return deleted
