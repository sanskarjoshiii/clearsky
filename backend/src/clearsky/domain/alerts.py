"""Officer village alerts (IMPLEMENTATION.md §2.6).

An alert offers every unbooked farmer in the village a one-tap booking on WhatsApp and flags the
village on the dashboards of nearby balers that have free capacity. Operators get no WhatsApp.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from pydantic import BaseModel

from clearsky import clock
from clearsky.channels import notify
from clearsky.channels.templates import ALERT_BOOK, VILLAGE_ALERT, button_id
from clearsky.config import get_settings
from clearsky.domain.geo import haversine_km
from clearsky.models import Alert, FieldStatus
from clearsky.models.entities import Button
from clearsky.repo import AlertsRepo, BalerDaysRepo, BalersRepo, FieldsRepo, VillagesRepo

OPEN_HOURS = 48
FREE_DAYS_AHEAD = 7


class AlertResult(BaseModel):
    alert: Alert
    farmers_notified: int
    balers_flagged: list[str]
    cooldown: bool = False


class AlertError(ValueError):
    pass


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=clock.IST)


def balers_with_capacity(lat: float, lng: float, today: date) -> list[str]:
    """Active balers whose radius covers the point and with free acres in the next week."""
    out = []
    days_repo = BalerDaysRepo()
    for b in BalersRepo().list_active():
        if haversine_km(lat, lng, b.lat, b.lng) > b.radius_km:
            continue
        ledger = days_repo.range(
            b.baler_id, today + timedelta(days=1), today + timedelta(days=FREE_DAYS_AHEAD)
        )
        free = any(
            b.acres_per_day - (ledger[d].booked_acres if d in ledger else 0) > 0
            for d in (today + timedelta(days=i) for i in range(1, FREE_DAYS_AHEAD + 1))
        )
        if free:
            out.append(b.baler_id)
    return out


def create_alert(village_id: str, officer_id: str, today: date | None = None) -> AlertResult:
    today = today or clock.today()
    village = VillagesRepo().get(village_id)
    if village is None:
        raise AlertError("unknown village")
    now = clock.now()
    repo = AlertsRepo()
    recent = repo.by_village(village_id)
    cooldown = timedelta(minutes=get_settings().alert_cooldown_minutes)
    if recent and now - _aware(recent[-1].created_at) < cooldown:
        last = recent[-1]
        return AlertResult(
            alert=last,
            farmers_notified=last.farmers_notified,
            balers_flagged=last.balers_flagged,
            cooldown=True,
        )

    open_fields = [
        f
        for f in FieldsRepo().by_village(village_id)
        if f.status in (FieldStatus.REGISTERED, FieldStatus.HARVESTED)
    ]
    notified: set[str] = set()
    for f in sorted(open_fields, key=lambda f: -f.risk_score):
        if f.phone in notified:
            continue
        notify.send_proactive(
            f.phone,
            VILLAGE_ALERT,
            [village.name],
            [Button(id=button_id(ALERT_BOOK, f.field_id), title=VILLAGE_ALERT.buttons[0])],
        )
        notified.add(f.phone)

    flagged = balers_with_capacity(village.lat, village.lng, today)
    alert = Alert(
        alert_id=f"AL-{uuid.uuid4().hex[:10]}",
        officer_id=officer_id,
        village_id=village_id,
        farmers_notified=len(notified),
        balers_flagged=flagged,
        status="OPEN",
        created_at=now,
    )
    repo.put(alert)
    return AlertResult(alert=alert, farmers_notified=len(notified), balers_flagged=flagged)


def open_alerts_for_baler(baler_id: str) -> list[Alert]:
    cutoff = clock.now() - timedelta(hours=OPEN_HOURS)
    return [
        a
        for a in AlertsRepo().list_all()
        if a.status == "OPEN" and baler_id in a.balers_flagged and _aware(a.created_at) >= cutoff
    ]
