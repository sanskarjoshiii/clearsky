"""Phase 4: WhatsApp verification, signatures, payload parsing, Graph API client, voice helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
import struct
from typing import Any

import httpx
import pytest

from clearsky.channels import voice
from clearsky.channels.templates import PICKUP_REMINDER, VILLAGE_ALERT, button_id, parse_button_id
from clearsky.channels.whatsapp import (
    WhatsAppClient,
    WhatsAppError,
    parse_inbound,
    verify_challenge,
    verify_signature,
)
from clearsky.config import reset_settings
from clearsky.models.entities import Button


def sign(body: bytes, secret: str = "s3cret") -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def wa_payload(*messages: dict[str, Any], statuses: int = 0) -> dict[str, Any]:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [{"wa_id": "919800000001", "profile": {"name": "Gurpreet"}}],
                            "messages": list(messages),
                            "statuses": [{"id": f"st{i}", "status": "delivered"} for i in range(statuses)],
                        },
                    }
                ],
            }
        ],
    }


def test_verify_challenge() -> None:
    params = {"hub.mode": "subscribe", "hub.verify_token": "tok", "hub.challenge": "123"}
    assert verify_challenge(params, "tok") == "123"
    assert verify_challenge(params, "other") is None
    assert verify_challenge({**params, "hub.mode": "x"}, "tok") is None
    assert verify_challenge(None, "tok") is None


def test_verify_signature() -> None:
    body = b'{"a":1}'
    assert verify_signature(body, sign(body), "s3cret")
    assert not verify_signature(body, sign(body, "wrong"), "s3cret")
    assert not verify_signature(body + b" ", sign(body), "s3cret")
    assert not verify_signature(body, None, "s3cret")
    assert not verify_signature(body, "md5=abc", "s3cret")


def test_parse_inbound_all_types() -> None:
    payload = wa_payload(
        {
            "from": "919800000001",
            "id": "m1",
            "timestamp": "1700000000",
            "type": "text",
            "text": {"body": "8 acre"},
        },
        {
            "from": "919800000001",
            "id": "m2",
            "type": "audio",
            "audio": {"id": "media1", "mime_type": "audio/ogg"},
        },
        {
            "from": "919800000001",
            "id": "m3",
            "type": "interactive",
            "interactive": {"type": "button_reply", "button_reply": {"id": "confirm:F1", "title": "HAAN"}},
        },
        {
            "from": "919800000001",
            "id": "m4",
            "type": "button",
            "button": {"payload": "alertbook:F2", "text": "HAAN"},
        },
        {
            "from": "919800000001",
            "id": "m5",
            "type": "location",
            "location": {"latitude": 30.2, "longitude": 76.0},
        },
        {"from": "919800000001", "id": "m6", "type": "sticker", "sticker": {}},
        {"id": "m7", "type": "text"},  # no sender → skipped
        statuses=2,
    )
    msgs, statuses = parse_inbound(payload)
    assert statuses == 2
    assert [m.type for m in msgs] == ["text", "audio", "button", "button", "location", "unsupported"]
    text, audio, inter, tmpl, loc, _ = msgs
    assert text.phone == "+919800000001" and text.text == "8 acre" and text.profile_name == "Gurpreet"
    assert text.timestamp == 1700000000
    assert audio.media_id == "media1"
    assert inter.button_id == "confirm:F1" and tmpl.button_id == "alertbook:F2"
    assert (loc.lat, loc.lng) == (30.2, 76.0)
    assert parse_inbound({}) == ([], 0)


def test_button_ids_and_templates() -> None:
    assert button_id("confirm", "F-1") == "confirm:F-1"
    assert parse_button_id("confirm:F-1") == ("confirm", "F-1")
    assert (
        parse_button_id("evil:F-1") is None and parse_button_id(None) is None and parse_button_id("x") is None
    )
    text = PICKUP_REMINDER.render(["Gurpreet", "24 Oct"])
    assert "Gurpreet ji" in text and "24 Oct" in text and "{{" not in text
    assert all(len(b) <= 20 for t in (PICKUP_REMINDER, VILLAGE_ALERT) for b in t.buttons)


@pytest.fixture
def wa_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WA_PHONE_NUMBER_ID", "PNID")
    monkeypatch.setenv("WA_ACCESS_TOKEN", "TOKEN")
    reset_settings()


def _client(handler: Any) -> WhatsAppClient:
    return WhatsAppClient(http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_client_payload_shapes(wa_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, Any]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.headers["authorization"] == "Bearer TOKEN"
        assert req.url.path.endswith("/PNID/messages")
        seen.append(json.loads(req.content))
        return httpx.Response(200, json={"messages": [{"id": "wamid"}]})

    c = _client(handler)
    c.send_text("+919800000001", "hello")
    c.send_audio_link("+919800000001", "https://x/a.mp3")
    c.send_buttons(
        "+919800000001",
        "Kal katai?",
        [Button(id="confirm:F1", title="HAAN"), Button(id="later:F1", title="NAHI and a very long title")],
    )
    c.send_template(
        "+919800000001", "pickup_reminder", "hi", ["Gurpreet", "24 Oct"], ["confirm:F1", "later:F1"]
    )
    text, audio, buttons, template = seen
    assert text["to"] == "919800000001" and text["text"]["body"] == "hello"
    assert text["messaging_product"] == "whatsapp"
    assert audio["audio"]["link"] == "https://x/a.mp3"
    btns = buttons["interactive"]["action"]["buttons"]
    assert btns[0]["reply"] == {"id": "confirm:F1", "title": "HAAN"} and len(btns[1]["reply"]["title"]) == 20
    comps = template["template"]["components"]
    assert comps[0]["parameters"][1]["text"] == "24 Oct"
    assert comps[2]["index"] == "1" and comps[2]["parameters"][0]["payload"] == "later:F1"


def test_client_retries_then_fails(wa_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("clearsky.channels.whatsapp.time.sleep", lambda s: None)
    calls = {"n": 0}

    def flaky(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503 if calls["n"] < 3 else 200, json={})

    _client(flaky).send_text("+91980", "hi")
    assert calls["n"] == 3
    with pytest.raises(WhatsAppError):
        _client(lambda r: httpx.Response(400, text="bad")).send_text("+91980", "hi")


def test_download_media(wa_env: None) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.host == "graph.facebook.com":
            return httpx.Response(200, json={"url": "https://cdn.example/media1", "mime_type": "audio/ogg"})
        return httpx.Response(200, content=b"OggS-bytes")

    data, mime = _client(handler).download_media("media1")
    assert data == b"OggS-bytes" and mime == "audio/ogg"


def fake_ogg(seconds: float) -> bytes:
    page = bytearray(b"OggS" + b"\x00\x04" + struct.pack("<q", int(seconds * 48000)) + b"\x00" * 16)
    return b"OggS\x00\x02" + b"\x00" * 8 + b"OpusHead" + b"\x00" * 30 + bytes(page)


def test_ogg_duration_and_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    assert voice.ogg_duration_seconds(fake_ogg(12.5)) == 12.5
    assert voice.ogg_duration_seconds(b"not ogg") is None
    assert voice.check_length(fake_ogg(30)) == 30
    with pytest.raises(voice.VoiceTooLong):
        voice.check_length(fake_ogg(75))


def test_transcribe_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(voice.VoiceUnavailable):
        voice.transcribe(fake_ogg(5), "m1")  # STT_PROVIDER=none
    monkeypatch.setenv("STT_PROVIDER", "openai")
    reset_settings()
    with pytest.raises(voice.VoiceUnavailable, match="STT_MODEL_ID"):
        voice.transcribe(fake_ogg(5), "m1")
    monkeypatch.setenv("STT_MODEL_ID", "team-stt-model")
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("STT_BASE_URL", "https://stt.example/v1")
    reset_settings()
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kw: Any) -> httpx.Response:
        captured.update(url=url, **kw)
        return httpx.Response(200, json={"text": " 8 acre 24 tareekh "}, request=httpx.Request("POST", url))

    monkeypatch.setattr(voice.httpx, "post", fake_post)
    assert voice.transcribe(fake_ogg(5), "m1") == "8 acre 24 tareekh"
    assert captured["url"] == "https://stt.example/v1/audio/transcriptions"
    assert (
        captured["data"]["model"] == "team-stt-model" and captured["headers"]["Authorization"] == "Bearer k"
    )


def test_synthesize_off_without_bucket() -> None:
    assert voice.synthesize("Namaste", "m1") is None
