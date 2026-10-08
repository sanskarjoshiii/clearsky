"""Daily 18:00 IST farmer reminders (IMPLEMENTATION.md §2.3). Operators get no messages.

1. Harvest is tomorrow and not yet confirmed → "Kal katai?" with HAAN / NAHI buttons.
2. A confirmed booking is tomorrow → "Kal baler aayega".
Runs at most once per demo/real date (marker in the Settings table) unless forced.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from clearsky import clock
from clearsky.agent.rules import HINGLISH, fmt_date
from clearsky.channels import notify
from clearsky.channels.templates import BALER_TOMORROW, CONFIRM, LATER, PICKUP_REMINDER, button_id
from clearsky.logging import get_logger
from clearsky.models import BookingStatus, FieldStatus
from clearsky.models.entities import Button
from clearsky.repo import BookingsRepo, FarmersRepo, FieldsRepo
from clearsky.repo.base import table

log = get_logger(child="reminders")


def _already_ran(d: date) -> bool:
    return "Item" in table("Settings").get_item(Key={"key": f"reminders:{d.isoformat()}"})


def _mark_ran(d: date, summary: dict[str, int]) -> None:
    table("Settings").put_item(Item={"key": f"reminders:{d.isoformat()}", **summary})


def run(today: date | None = None, force: bool = False) -> dict[str, int]:
    today = today or clock.today()
    tomorrow = today + timedelta(days=1)
    if not force and _already_ran(today):
        return {"harvest_checks": 0, "pickup_notices": 0, "skipped": 1}
    farmers = {f.phone: f for f in FarmersRepo().list_all()}
    fields = FieldsRepo()
    harvest_checks = 0
    candidates = fields.by_status(FieldStatus.REGISTERED) + fields.by_status(FieldStatus.BOOKED)
    for f in candidates:
        if f.harvest_date != tomorrow or f.harvest_confirmed:
            continue
        name = farmers[f.phone].name if f.phone in farmers else ""
        notify.send_proactive(
            f.phone,
            PICKUP_REMINDER,
            [name, fmt_date(tomorrow, HINGLISH)],
            [
                Button(id=button_id(CONFIRM, f.field_id), title="HAAN"),
                Button(id=button_id(LATER, f.field_id), title="NAHI"),
            ],
        )
        harvest_checks += 1

    pickup_notices = 0
    for bk in BookingsRepo().by_date(tomorrow):
        if bk.status != BookingStatus.CONFIRMED:
            continue
        name = farmers[bk.phone].name if bk.phone in farmers else ""
        notify.send_proactive(bk.phone, BALER_TOMORROW, [name, fmt_date(tomorrow, HINGLISH)])
        pickup_notices += 1

    summary = {"harvest_checks": harvest_checks, "pickup_notices": pickup_notices, "skipped": 0}
    _mark_ran(today, summary)
    log.info("reminders sent", extra=summary)
    return summary


def handler(event: dict[str, Any], context: Any) -> dict[str, int]:
    force = bool((event or {}).get("force"))
    return run(force=force)
