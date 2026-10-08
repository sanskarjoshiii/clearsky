"""Impact counters for the dashboard and the public /impact page (README §13)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from clearsky import clock
from clearsky.config import get_settings
from clearsky.models import BookingStatus, FieldStatus, RiskLevel
from clearsky.repo import AlertsRepo, BookingsRepo, FarmersRepo, FieldsRepo


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=clock.IST)


def compute() -> dict[str, Any]:
    fields = FieldsRepo().list_all()
    bookings = BookingsRepo().list_all()
    alerts = AlertsRepo().list_all()
    live = [b for b in bookings if b.status != BookingStatus.CANCELLED]
    done = [b for b in live if b.status == BookingStatus.DONE]

    first_alert: dict[str, datetime] = {}
    for a in alerts:
        first_alert.setdefault(a.village_id, _aware(a.created_at))
    saved = sum(
        1 for b in live if b.village_id in first_alert and _aware(b.created_at) > first_alert[b.village_id]
    )

    factor = get_settings().emission_factor_pm25_kg_per_tonne
    tonnes_delivered = round(sum(b.est_tonnes for b in done), 1)
    return {
        "farmers": len(FarmersRepo().list_all()),
        "fields": len(fields),
        "acres_registered": round(sum(f.acres for f in fields), 1),
        "acres_booked": round(
            sum(f.acres for f in fields if f.status in (FieldStatus.BOOKED, FieldStatus.CLEARED)), 1
        ),
        "acres_cleared": round(sum(f.acres for f in fields if f.status == FieldStatus.CLEARED), 1),
        "tonnes_booked": round(sum(b.est_tonnes for b in live), 1),
        "tonnes_delivered": tonnes_delivered,
        "payouts_estimated_inr": round(sum(b.farmer_payout for b in live)),
        "bookings": len(live),
        "bookings_done": len(done),
        "red_fields": sum(1 for f in fields if f.risk_level == RiskLevel.RED),
        "yellow_fields": sum(1 for f in fields if f.risk_level == RiskLevel.YELLOW),
        "fields_saved_after_alert": saved,
        "alerts_sent": len(alerts),
        "fires_reported": sum(1 for f in fields if f.status == FieldStatus.FIRE_REPORTED),
        # Only when the team supplies a cited factor; otherwise the UI omits emissions.
        "pm25_avoided_kg": round(tonnes_delivered * factor, 1) if factor is not None else None,
        "today": clock.today().isoformat(),
        "demo_prices": True,
    }
