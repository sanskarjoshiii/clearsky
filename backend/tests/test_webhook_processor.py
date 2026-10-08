"""Phase 4: webhook → dedupe → (SQS | inline) → processor → agent → reply; notify rules."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import boto3
import pytest

from clearsky.channels import notify
from clearsky.channels.templates import VILLAGE_ALERT
from clearsky.channels.whatsapp import Inbound
from clearsky.config import reset_settings
from clearsky.handlers import processor, webhook
from clearsky.models import FieldStatus
from clearsky.models.entities import Button
from clearsky.repo import BookingsRepo, ConversationsRepo, FieldsRepo
from clearsky.repo.processed import ProcessedMessagesRepo
from clearsky.seed.generate import generate
from clearsky.seed.load import load
from tests import factories as fx
from tests.apiclient import Ctx, event
from tests.test_whatsapp import sign, wa_payload

PHONE = "+919800000001"
MSG = "Mera 8 acre dhaan 24 tareekh ko katega, Bhawanigarh. Naam Gurpreet."


@pytest.fixture
def seeded(ddb: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WA_APP_SECRET", "s3cret")
    monkeypatch.setenv("WA_VERIFY_TOKEN", "tok")
    reset_settings()
    load(generate(42), prebook=False)


def text_msg(msg_id: str, body: str) -> dict[str, Any]:
    return {"from": PHONE.lstrip("+"), "id": msg_id, "type": "text", "text": {"body": body}}


def post(payload: dict[str, Any], signature: str | None = None) -> dict[str, Any]:
    raw = json.dumps(payload)
    ev = event(
        "POST",
        "/webhook/whatsapp",
        raw_body=raw,
        headers={"x-hub-signature-256": signature or sign(raw.encode())},
    )
    return webhook.handler(ev, Ctx())


def texts(phone: str = PHONE) -> list[tuple[str, str]]:
    return [(t.role, t.text) for t in ConversationsRepo().last(phone, 50)]


def test_webhook_get_verification(seeded: None) -> None:
    ok = webhook.handler(
        event(
            "GET",
            "/webhook/whatsapp",
            query={"hub.mode": "subscribe", "hub.verify_token": "tok", "hub.challenge": "42"},
        ),
        Ctx(),
    )
    assert ok["statusCode"] == 200 and ok["body"] == "42"
    bad = webhook.handler(
        event(
            "GET",
            "/webhook/whatsapp",
            query={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "42"},
        ),
        Ctx(),
    )
    assert bad["statusCode"] == 403


def test_webhook_rejects_bad_signature(seeded: None) -> None:
    assert post(wa_payload(text_msg("m1", "hi")), signature="sha256=deadbeef")["statusCode"] == 401
    assert ConversationsRepo().last(PHONE, 5) == []


def test_webhook_inline_booking_and_dedupe(seeded: None) -> None:
    resp = post(wa_payload(text_msg("wamid.1", MSG)))
    assert resp["statusCode"] == 200 and json.loads(resp["body"]) == {"queued": 1}
    convo = texts()
    assert convo[0] == ("user", MSG) and convo[-1][1].startswith("✅ Gurpreet ji")
    assert ProcessedMessagesRepo().status("wamid.1") == "done"
    # Meta retries the same message id → ignored
    again = post(wa_payload(text_msg("wamid.1", MSG)))
    assert json.loads(again["body"]) == {"queued": 0}
    assert len(BookingsRepo().list_all()) == 1


def test_webhook_enqueues_when_queue_configured(seeded: None, monkeypatch: pytest.MonkeyPatch) -> None:
    sqs = boto3.client("sqs", region_name="ap-south-1")
    url = sqs.create_queue(QueueName="inbound")["QueueUrl"]
    monkeypatch.setenv("INBOUND_QUEUE_URL", url)
    reset_settings()
    post(wa_payload(text_msg("wamid.2", MSG)))
    msgs = sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=10)["Messages"]
    assert len(msgs) == 1 and ConversationsRepo().last(PHONE, 5) == []  # not processed yet
    result = processor.handler({"Records": [{"messageId": "x", "body": msgs[0]["Body"]}]}, Ctx())
    assert result == {"batchItemFailures": []}
    assert texts()[-1][1].startswith("✅")
    assert ProcessedMessagesRepo().status("wamid.2") == "done"


def test_status_callbacks_are_ignored(seeded: None) -> None:
    resp = post(wa_payload(statuses=3))
    assert json.loads(resp["body"]) == {"queued": 0}


def inbound(**kw: Any) -> Inbound:
    return Inbound(msg_id=kw.pop("msg_id", "m-x"), phone=kw.pop("phone", PHONE), **kw)


def test_button_confirm_books_unbooked_field(seeded: None) -> None:
    fx.farmer(PHONE, village_id="V002", name="Balwinder")
    fx.field("F9", phone=PHONE, village_id="V002", harvest=date(2026, 10, 21), lat=30.266, lng=76.039)
    sent = processor.process_inbound(inbound(type="button", button_id="confirm:F9", text="HAAN"))
    assert sent[0].startswith("✅ Balwinder ji")
    f = FieldsRepo().get("F9")
    assert f is not None and f.harvest_confirmed and f.status == FieldStatus.BOOKED


def test_button_later_then_new_date(seeded: None) -> None:
    processor.process_inbound(inbound(type="text", text=MSG, msg_id="a"))
    [f] = FieldsRepo().by_farmer(PHONE)
    sent = processor.process_inbound(inbound(type="button", button_id=f"later:{f.field_id}", text="NAHI"))
    assert "Nayi katai" in sent[0]
    moved = processor.process_inbound(inbound(type="text", text="28 tareekh", msg_id="b"))
    assert moved[0].startswith("✅") and "29 Oct" in moved[0]


def test_button_for_someone_elses_field_is_ignored(seeded: None) -> None:
    fx.farmer("+919800000002", village_id="V002")
    fx.field("FX", phone="+919800000002", village_id="V002")
    sent = processor.process_inbound(inbound(type="button", button_id="alertbook:FX"))
    assert sent[0].startswith("Sat Sri Akal")
    assert FieldsRepo().get("FX").status == FieldStatus.REGISTERED  # type: ignore[union-attr]


def test_location_updates_latest_field(seeded: None) -> None:
    assert "Pehle apne khet" in processor.process_inbound(inbound(type="location", lat=30.1, lng=76.1))[0]
    processor.process_inbound(inbound(type="text", text=MSG, msg_id="c"))
    sent = processor.process_inbound(inbound(type="location", lat=30.27, lng=76.05))
    assert sent[0].startswith("📍")
    [f] = FieldsRepo().by_farmer(PHONE)
    assert (f.lat, f.lng) == (30.27, 76.05)


def test_voice_note_without_stt_asks_to_type(seeded: None, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def download_media(self, media_id: str) -> tuple[bytes, str]:
            return b"OggS", "audio/ogg"

    notify.set_client(FakeClient())  # type: ignore[arg-type]
    try:
        sent = processor.process_inbound(inbound(type="audio", media_id="med"))
    finally:
        notify.set_client(None)
    assert sent == [processor.TEXTS["listening"], processor.TEXTS["voice_unavailable"]]


def test_voice_note_transcribed_goes_to_agent(seeded: None, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def download_media(self, media_id: str) -> tuple[bytes, str]:
            return b"OggS", "audio/ogg"

    monkeypatch.setattr(processor.voice, "transcribe", lambda data, msg_id, mime: MSG)
    notify.set_client(FakeClient())  # type: ignore[arg-type]
    try:
        sent = processor.process_inbound(inbound(type="audio", media_id="med"))
    finally:
        notify.set_client(None)
    assert sent[0] == processor.TEXTS["listening"] and sent[1].startswith("✅")


def test_rate_limit(seeded: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "2")
    reset_settings()
    for i in range(3):
        processor.process_inbound(inbound(type="text", text="namaste", msg_id=f"r{i}"))
    sent = processor.process_inbound(inbound(type="text", text="namaste", msg_id="r9"))
    assert sent == [processor.TEXTS["rate_limited"]]


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def send_text(self, phone: str, text: str) -> None:
        self.calls.append(("text", phone))

    def send_buttons(self, phone: str, body: str, buttons: list[Button]) -> None:
        self.calls.append(("buttons", phone))

    def send_template(self, phone: str, name: str, lang: str, params: list[str], payloads: list[str]) -> None:
        self.calls.append(("template", (phone, name, payloads)))

    def send_audio_link(self, phone: str, url: str) -> None:
        self.calls.append(("audio", phone))


def test_cloud_mode_rules(seeded: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WA_MODE", "cloud")
    reset_settings()
    client = RecordingClient()
    notify.set_client(client)  # type: ignore[arg-type]
    try:
        # synthetic seeded farmer: recorded, never sent
        notify.send_text("+919999900001", "hi")
        assert client.calls == []
        # real farmer outside the 24 h window → template with button payloads
        from clearsky.repo import FarmersRepo

        real = fx.farmer("+919811111111", village_id="V002").model_copy(update={"synthetic": False})
        FarmersRepo().put(real)
        btn = [Button(id="alertbook:F1", title="HAAN, book karo")]
        notify.send_proactive("+919811111111", VILLAGE_ALERT, ["Bhawanigarh"], btn)
        assert client.calls[-1] == ("template", ("+919811111111", "village_alert", ["alertbook:F1"]))
        # after the farmer writes, inside the window → interactive buttons
        from clearsky.agent import memory

        memory.save_turn("+919811111111", "user", "hello")
        notify.send_proactive("+919811111111", VILLAGE_ALERT, ["Bhawanigarh"], btn)
        assert client.calls[-1] == ("buttons", "+919811111111")
    finally:
        notify.set_client(None)
    assert texts("+919999900001") == [("assistant", "hi")]
