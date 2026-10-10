"""WhatsApp Cloud API: webhook verification, signature check, inbound parsing, sending, media download.

IMPLEMENTATION.md §8. Graph API version comes from WA_API_VERSION; secrets from SSM/env:
WA_PHONE_NUMBER_ID, WA_ACCESS_TOKEN, WA_APP_SECRET, WA_VERIFY_TOKEN.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any

import httpx
from pydantic import BaseModel

from clearsky.config import get_secret, get_settings
from clearsky.logging import get_logger, mask_phone
from clearsky.models.entities import Button

log = get_logger(child="whatsapp")
GRAPH = "https://graph.facebook.com"


class Inbound(BaseModel):
    """One inbound farmer message, normalised from the webhook payload."""

    msg_id: str
    phone: str  # E.164 with "+"
    type: str  # text | audio | button | location | unsupported
    text: str = ""
    media_id: str | None = None
    mime_type: str | None = None
    button_id: str | None = None
    lat: float | None = None
    lng: float | None = None
    profile_name: str | None = None
    timestamp: int = 0


# ------------------------------------------------------------------ webhook


def verify_challenge(params: dict[str, str] | None, verify_token: str) -> str | None:
    """GET /webhook/whatsapp: return hub.challenge if the verify token matches, else None."""
    p = params or {}
    if p.get("hub.mode") == "subscribe" and hmac.compare_digest(p.get("hub.verify_token", ""), verify_token):
        return p.get("hub.challenge", "")
    return None


def verify_signature(raw_body: bytes, header: str | None, app_secret: str) -> bool:
    """X-Hub-Signature-256: 'sha256=' + HMAC-SHA256(raw body, app secret). Constant-time compare."""
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(header.removeprefix("sha256="), expected)


def parse_inbound(payload: dict[str, Any]) -> tuple[list[Inbound], int]:
    """(messages, number of status callbacks). Unknown shapes are skipped, never raised."""
    messages: list[Inbound] = []
    statuses = 0
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value", {}) or {}
            statuses += len(value.get("statuses", []) or [])
            names = {
                c.get("wa_id"): (c.get("profile") or {}).get("name") for c in value.get("contacts", []) or []
            }
            for m in value.get("messages", []) or []:
                parsed = _parse_message(m, names)
                if parsed is not None:
                    messages.append(parsed)
    return messages, statuses


def _parse_message(m: dict[str, Any], names: dict[str, str | None]) -> Inbound | None:
    sender = str(m.get("from", ""))
    if not sender or not m.get("id"):
        return None
    base: dict[str, Any] = {
        "msg_id": m["id"],
        "phone": sender if sender.startswith("+") else f"+{sender}",
        "profile_name": names.get(sender),
        "timestamp": int(m.get("timestamp", 0) or 0),
    }
    kind = m.get("type")
    if kind == "text":
        return Inbound(type="text", text=(m.get("text") or {}).get("body", ""), **base)
    if kind in ("audio", "voice"):
        audio = m.get("audio") or m.get("voice") or {}
        return Inbound(type="audio", media_id=audio.get("id"), mime_type=audio.get("mime_type"), **base)
    if kind == "interactive":
        inter = m.get("interactive") or {}
        reply = inter.get("button_reply") or inter.get("list_reply") or {}
        return Inbound(type="button", button_id=reply.get("id"), text=reply.get("title", ""), **base)
    if kind == "button":  # quick-reply button on a template message
        btn = m.get("button") or {}
        return Inbound(type="button", button_id=btn.get("payload"), text=btn.get("text", ""), **base)
    if kind == "location":
        loc = m.get("location") or {}
        return Inbound(type="location", lat=loc.get("latitude"), lng=loc.get("longitude"), **base)
    return Inbound(type="unsupported", text=str(kind), **base)


# ------------------------------------------------------------------ sending


class WhatsAppError(RuntimeError):
    pass


class WhatsAppClient:
    """Thin Graph API client with timeouts and retries on 429/5xx."""

    def __init__(self, http: httpx.Client | None = None) -> None:
        s = get_settings()
        self.version = s.wa_api_version
        self.phone_number_id = get_secret("WA_PHONE_NUMBER_ID")
        self.token = get_secret("WA_ACCESS_TOKEN")
        self.http = http or httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0))

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{GRAPH}/{self.version}/{self.phone_number_id}/messages"
        payload = {"messaging_product": "whatsapp", "recipient_type": "individual", **body}
        for attempt in range(3):
            resp = self.http.post(url, json=payload, headers=self._headers)
            if resp.status_code < 400:
                return dict(resp.json())
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(0.5 * 2**attempt)
                continue
            try:  # Meta's reason (e.g. code 190 = expired token, 131030 = recipient not allowed)
                err = resp.json().get("error", {})
            except ValueError:
                err = {}
            log.error(
                "whatsapp send failed",
                extra={
                    "status": resp.status_code,
                    "to": mask_phone(body.get("to")),
                    "meta_code": err.get("code"),
                    "meta_message": str(err.get("message", ""))[:200],
                },
            )
            raise WhatsAppError(f"Graph API {resp.status_code}: {resp.text[:300]}")
        raise WhatsAppError("unreachable")

    @staticmethod
    def _to(phone: str) -> str:
        return phone.lstrip("+")

    def send_text(self, phone: str, text: str) -> dict[str, Any]:
        return self._post(
            {"to": self._to(phone), "type": "text", "text": {"preview_url": False, "body": text}}
        )

    def send_audio_link(self, phone: str, url: str) -> dict[str, Any]:
        return self._post({"to": self._to(phone), "type": "audio", "audio": {"link": url}})

    def send_buttons(self, phone: str, body: str, buttons: list[Button]) -> dict[str, Any]:
        return self._post(
            {
                "to": self._to(phone),
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": body},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": b.id, "title": b.title[:20]}}
                            for b in buttons[:3]
                        ]
                    },
                },
            }
        )

    def send_template(
        self,
        phone: str,
        name: str,
        language: str,
        body_params: list[str],
        button_payloads: list[str] | None = None,
    ) -> dict[str, Any]:
        components: list[dict[str, Any]] = []
        if body_params:
            components.append(
                {"type": "body", "parameters": [{"type": "text", "text": p} for p in body_params]}
            )
        for i, payload in enumerate(button_payloads or []):
            components.append(
                {
                    "type": "button",
                    "sub_type": "quick_reply",
                    "index": str(i),
                    "parameters": [{"type": "payload", "payload": payload}],
                }
            )
        return self._post(
            {
                "to": self._to(phone),
                "type": "template",
                "template": {"name": name, "language": {"code": language}, "components": components},
            }
        )

    def download_media(self, media_id: str) -> tuple[bytes, str]:
        """(bytes, mime type). Two calls: media id → short-lived URL → bytes (both need the token)."""
        meta = self.http.get(f"{GRAPH}/{self.version}/{media_id}", headers=self._headers)
        if meta.status_code >= 400:
            raise WhatsAppError(f"media lookup {meta.status_code}")
        info = meta.json()
        data = self.http.get(info["url"], headers=self._headers)
        if data.status_code >= 400:
            raise WhatsAppError(f"media download {data.status_code}")
        return data.content, str(info.get("mime_type", "audio/ogg"))
