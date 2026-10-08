"""Every outbound farmer message goes through here.

- WA_MODE=simulator: the message is only recorded (Conversations table); the dashboard's farmer
  simulator shows it. Nothing leaves the system.
- WA_MODE=cloud: the message is recorded AND sent through the WhatsApp Cloud API. Seeded
  `synthetic` farmers are never messaged (placeholder numbers belong to real strangers).
- Proactive messages (reminders, alerts, "field cleared") use a template outside the 24-hour
  window, and free-form/interactive messages inside it (IMPLEMENTATION.md §8).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from clearsky.agent import memory
from clearsky.channels.templates import Template
from clearsky.channels.whatsapp import WhatsAppClient, WhatsAppError
from clearsky.config import get_settings
from clearsky.logging import get_logger, mask_phone
from clearsky.models.entities import Button
from clearsky.repo import ConversationsRepo, FarmersRepo

log = get_logger(child="notify")
_client: WhatsAppClient | None = None


def is_cloud() -> bool:
    return get_settings().wa_mode == "cloud"


def client() -> WhatsAppClient:
    global _client
    if _client is None:
        _client = WhatsAppClient()
    return _client


def set_client(c: WhatsAppClient | None) -> None:
    """Tests inject a fake client."""
    global _client
    _client = c


def _deliverable(phone: str) -> bool:
    if not is_cloud():
        return False
    farmer = FarmersRepo().get(phone)
    if farmer is not None and farmer.synthetic:
        log.info("skip synthetic farmer", extra={"to": mask_phone(phone)})
        return False
    return True


def _safe(action: str, phone: str, fn: object) -> bool:
    try:
        fn()  # type: ignore[operator]
        return True
    except (WhatsAppError, Exception) as e:  # never let a send failure break a booking flow
        log.error("send failed", extra={"action": action, "to": mask_phone(phone), "error": type(e).__name__})
        return False


def within_session(phone: str) -> bool:
    """True if the farmer wrote to us in the last 24 hours (free-form messages allowed)."""
    ts = ConversationsRepo().last_user_ts(phone)
    if not ts:
        return False
    last = datetime.fromisoformat(ts)
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    return datetime.now(UTC) - last < timedelta(hours=23, minutes=50)


def send_text(phone: str, text: str, *, record: bool = True) -> bool:
    if record:
        memory.save_turn(phone, "assistant", text)
    if _deliverable(phone):
        return _safe("text", phone, lambda: client().send_text(phone, text))
    return True


def send_buttons(phone: str, body: str, buttons: list[Button], *, record: bool = True) -> bool:
    if record:
        memory.save_turn(phone, "assistant", body, kind="buttons", buttons=buttons)
    if _deliverable(phone):
        return _safe("buttons", phone, lambda: client().send_buttons(phone, body, buttons))
    return True


def send_audio(phone: str, url: str, transcript: str, *, record: bool = True) -> bool:
    if record:
        memory.save_turn(phone, "assistant", transcript, kind="audio", media_url=url)
    if _deliverable(phone):
        return _safe("audio", phone, lambda: client().send_audio_link(phone, url))
    return True


def send_proactive(
    phone: str, template: Template, params: list[str], buttons: list[Button] | None = None
) -> bool:
    """A message we start (not a reply). Template outside the 24 h window; interactive inside it."""
    text = template.render(params)
    buttons = buttons or []
    memory.save_turn(phone, "assistant", text, kind="buttons" if buttons else "template", buttons=buttons)
    if not _deliverable(phone):
        return True
    if within_session(phone):
        if buttons:
            return _safe("buttons", phone, lambda: client().send_buttons(phone, text, buttons))
        return _safe("text", phone, lambda: client().send_text(phone, text))
    lang = get_settings().wa_template_language
    return _safe(
        "template",
        phone,
        lambda: client().send_template(phone, template.name, lang, params, [b.id for b in buttons]),
    )
