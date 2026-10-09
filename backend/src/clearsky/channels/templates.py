"""WhatsApp message templates (needed outside the 24-hour customer-service window).

The exact text to submit in Meta Business Manager is in docs/whatsapp_templates.md and must match
`BODY` here ({{1}}, {{2}} are positional parameters). Inside the 24-hour window, and in the simulator,
the same text is sent as a free-form/interactive message instead.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Template:
    name: str
    body: str  # Meta format with {{n}} placeholders
    buttons: tuple[str, ...] = ()  # quick-reply titles (≤ 20 chars each)

    def render(self, params: list[str]) -> str:
        text = self.body
        for i, p in enumerate(params, start=1):
            text = text.replace("{{" + str(i) + "}}", p)
        return text


PICKUP_REMINDER = Template(
    "pickup_reminder",
    "Namaste {{1}} ji 🌾 Kya kal ({{2}}) aapke dhaan ki katai hai? Katai ke baad baler aapka khet saaf karega. "
    "Kripya HAAN ya NAHI dabaiye.",
    ("HAAN", "NAHI"),
)
BALER_TOMORROW = Template(
    "baler_tomorrow",
    "Namaste {{1}} ji 🚜 Kal ({{2}}) baler aapke khet aayega. Parali na jalayein. Koi badlav ho to yahin likhein.",
)
VILLAGE_ALERT = Template(
    "village_alert",
    "Namaste ji 🌾 {{1}} mein baler khali hai. Parali jalane ki jagah muft mein khet saaf karwaiye. "
    "Booking ke liye HAAN dabaiye.",
    ("HAAN, book karo",),
)
FIELD_CLEARED = Template(
    "field_cleared",
    "✅ {{1}} ji, aapka khet aaj saaf ho gaya. Parali na jalane ke liye dhanyavaad! 🙏",
)

# Offer lifecycle (issue #3): the farmer hears "confirmed" only after a baler accepted.
BOOKING_CONFIRMED = Template(
    "booking_confirmed",
    "✅ {{1}} ji, {{2}} ko baler {{3}} aapka khet saaf karne aayega. Parali na jalayein. 🙏",
)
BOOKING_CHANGED = Template(
    "booking_changed",
    "📨 {{1}} ji, aapki pickup ki tareekh badal kar {{2}} ho gayi hai. Baler ke confirm karte hi batayenge.",
)
BOOKING_DELAYED = Template(
    "booking_delayed",
    "{{1}} ji, abhi tak kisi baler ne aapki pickup confirm nahi ki. Officer ko bata diya hai, "
    "jaldi sampark hoga. Kripya parali na jalayein. 🙏",
)

ALL = {
    t.name: t
    for t in (
        PICKUP_REMINDER,
        BALER_TOMORROW,
        VILLAGE_ALERT,
        FIELD_CLEARED,
        BOOKING_CONFIRMED,
        BOOKING_CHANGED,
        BOOKING_DELAYED,
    )
}

# Button ids: "<action>:<field_id>". They come back as interactive reply ids or template payloads.
CONFIRM = "confirm"  # harvest is happening as planned
LATER = "later"  # harvest moved → ask for the new date
ALERT_BOOK = "alertbook"  # farmer accepted an officer's village alert


def button_id(action: str, field_id: str) -> str:
    return f"{action}:{field_id}"


def parse_button_id(value: str | None) -> tuple[str, str] | None:
    if not value or ":" not in value:
        return None
    action, field_id = value.split(":", 1)
    return (action, field_id) if action in (CONFIRM, LATER, ALERT_BOOK) and field_id else None
