"""Conversation memory: last N turns from DynamoDB, converted to Strands/Bedrock messages."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from clearsky.config import get_settings
from clearsky.models import ConversationTurn
from clearsky.models.entities import Button
from clearsky.repo import ConversationsRepo


def load_turns(phone: str, n: int | None = None) -> list[ConversationTurn]:
    return ConversationsRepo().last(phone, n or get_settings().history_turns)


def save_turn(
    phone: str,
    role: str,
    text: str,
    *,
    kind: str = "text",
    buttons: list[Button] | None = None,
    media_url: str | None = None,
) -> ConversationTurn:
    # Real wall-clock time keeps the sort key unique and ordered even when the demo clock jumps.
    ts = datetime.now(UTC).isoformat(timespec="microseconds")
    turn = ConversationTurn(
        phone=phone, ts=ts, role=role, text=text, kind=kind, buttons=buttons or [], media_url=media_url
    )
    ConversationsRepo().add(turn)
    return turn


def to_messages(turns: list[ConversationTurn]) -> list[dict[str, Any]]:
    """Bedrock Converse rules: text only, starts with a user turn, roles alternate.

    Leading assistant turns are dropped; consecutive turns with the same role are merged.
    """
    msgs: list[dict[str, Any]] = []
    for t in turns:
        role = "assistant" if t.role == "assistant" else "user"
        text = t.text.strip()
        if not text:
            continue
        if not msgs and role == "assistant":
            continue
        if msgs and msgs[-1]["role"] == role:
            msgs[-1]["content"][0]["text"] += "\n" + text
        else:
            msgs.append({"role": role, "content": [{"text": text}]})
    # The new user message is appended by the agent call, so history must end on an assistant turn.
    if msgs and msgs[-1]["role"] == "user":
        msgs.pop()
    return msgs
