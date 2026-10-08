"""Inbound farmer message processing (SQS → Lambda), IMPLEMENTATION.md §2.1–2.2.

`process_inbound` is the single entry point used by the SQS Lambda, the local webhook path, and the
dashboard's farmer simulator, so every route exercises the same code.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from clearsky import clock
from clearsky.agent import memory, rules
from clearsky.agent import tools as tool_impl
from clearsky.agent.agent import run_turn
from clearsky.channels import notify, voice
from clearsky.channels.templates import ALERT_BOOK, CONFIRM, LATER, parse_button_id
from clearsky.channels.whatsapp import Inbound
from clearsky.config import get_settings
from clearsky.logging import get_logger, mask_phone
from clearsky.repo import ConversationsRepo, FarmersRepo, FieldsRepo
from clearsky.repo.processed import ProcessedMessagesRepo

log = get_logger(child="processor")

TEXTS = {
    "listening": "🎙️ Sun raha hoon…",
    "voice_unavailable": "Maaf kijiye, abhi voice note samajh nahi pa raha. Kripya likh kar bhejiye. 🙏",
    "voice_unclear": "Awaaz saaf nahi aayi, kripya dobara bolein ya likhein.",
    "voice_too_long": "Kripya 1 minute se chhota voice note bhejiye.",
    "rate_limited": "Bahut saare message aa gaye hain. Thodi der baad likhiye. 🙏",
    "location_saved": "📍 Location mil gayi, dhanyavaad! Baler ko sahi jagah pata chal jayegi.",
    "location_no_field": "📍 Location mil gayi. Pehle apne khet ki jaankari bhejiye (acre aur katai ki tareekh).",
}


def _lang(phone: str) -> str:
    farmer = FarmersRepo().get(phone)
    if farmer is None:
        return rules.HINGLISH
    return {"hi": rules.HINGLISH, "pa": rules.PA, "en": rules.EN}.get(farmer.language.value, rules.HINGLISH)


def _rate_limited(phone: str) -> bool:
    since = (datetime.now(UTC) - timedelta(hours=1)).isoformat(timespec="microseconds")
    n = sum(1 for t in ConversationsRepo().since(phone, since) if t.role == "user")
    return n > get_settings().rate_limit_per_hour


def process_inbound(msg: Inbound) -> list[str]:
    """Handle one inbound message; returns the reply texts sent (for logs and the simulator)."""
    phone = msg.phone
    sent: list[str] = []

    def say(text: str, record: bool = True) -> None:
        notify.send_text(phone, text, record=record)
        sent.append(text)

    if _rate_limited(phone):
        memory.save_turn(phone, "user", msg.text or f"[{msg.type}]", kind=msg.type)
        say(TEXTS["rate_limited"])
        return sent

    if msg.type == "button":
        memory.save_turn(phone, "user", msg.text or msg.button_id or "", kind="button")
        say(_handle_button(phone, msg.button_id))
        return sent

    if msg.type == "location":
        memory.save_turn(phone, "user", f"📍 {msg.lat},{msg.lng}", kind="location")
        say(_handle_location(phone, msg.lat, msg.lng))
        return sent

    text = msg.text
    was_voice = msg.type == "audio"
    if was_voice:
        say(TEXTS["listening"])
        try:
            if not msg.media_id:
                raise voice.VoiceUnavailable("no media id")
            data, mime = notify.client().download_media(msg.media_id)
            text = voice.transcribe(data, msg.msg_id, mime)
        except voice.VoiceTooLong:
            memory.save_turn(phone, "user", "[voice note]", kind="voice_in")
            say(TEXTS["voice_too_long"])
            return sent
        except Exception as e:  # STT off, download failed, provider error
            log.warning("voice failed", extra={"phone": mask_phone(phone), "error": type(e).__name__})
            memory.save_turn(phone, "user", "[voice note]", kind="voice_in")
            say(
                TEXTS["voice_unavailable"]
                if isinstance(e, voice.VoiceUnavailable)
                else TEXTS["voice_unclear"]
            )
            return sent
        if not text:
            memory.save_turn(phone, "user", "[voice note]", kind="voice_in")
            say(TEXTS["voice_unclear"])
            return sent

    if msg.type == "unsupported" or not text.strip():
        memory.save_turn(phone, "user", f"[{msg.text or 'message'}]", kind="unsupported")
        say(rules.t("intro", _lang(phone)))
        return sent

    reply = run_turn(phone, text)  # saves the user turn and the reply turn
    say(reply.text, record=False)
    if was_voice:
        try:
            url = voice.synthesize(reply.text, msg.msg_id)
            if url:
                notify.send_audio(phone, url, reply.text)
        except Exception as e:
            log.warning("tts failed", extra={"phone": mask_phone(phone), "error": type(e).__name__})
    return sent


def _handle_button(phone: str, button_id: str | None) -> str:
    lang = _lang(phone)
    parsed = parse_button_id(button_id)
    if parsed is None:
        return rules.t("intro", lang)
    action, field_id = parsed
    farmer = FarmersRepo().get(phone)
    name = farmer.name if farmer else ""
    field = FieldsRepo().get(field_id)
    if field is None or field.phone != phone:
        return rules.t("intro", lang)
    if action == LATER:
        return rules.t("ask_new_date", lang)
    if action == CONFIRM:
        tool_impl.confirm_harvest(phone, field_id)
        if field.status.value == "BOOKED":
            return rules.t("harvest_confirmed", lang)
    booked = tool_impl.book_pickup(phone, field_id)  # CONFIRM on an unbooked field, or ALERT_BOOK
    if action == ALERT_BOOK and booked.get("already_booked"):
        return rules.t("harvest_confirmed", lang)
    return rules._result_text(booked, name, field.acres, lang)


def _handle_location(phone: str, lat: float | None, lng: float | None) -> str:
    if lat is None or lng is None:
        return TEXTS["location_no_field"]
    fields = [
        f for f in FieldsRepo().by_farmer(phone) if f.status.value in ("REGISTERED", "HARVESTED", "BOOKED")
    ]
    if not fields:
        return TEXTS["location_no_field"]
    latest = max(fields, key=lambda f: f.created_at)
    FieldsRepo().update(
        latest.field_id, {"lat": float(lat), "lng": float(lng), "updated_at": clock.now().isoformat()}
    )
    return TEXTS["location_saved"]


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """SQS trigger (batch size 1). A failure raises so SQS retries, then the DLQ catches it."""
    failures = []
    processed = ProcessedMessagesRepo()
    for record in event.get("Records", []):
        msg = Inbound.model_validate(json.loads(record["body"]))
        try:
            process_inbound(msg)
            processed.mark(msg.msg_id, "done")
        except Exception:
            log.exception("process failed", extra={"phone": mask_phone(msg.phone)})
            failures.append({"itemIdentifier": record.get("messageId", "")})
    return {"batchItemFailures": failures}
