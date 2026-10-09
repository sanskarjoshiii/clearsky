"""Pollution avoided by straw that was baled instead of burnt (issue #5).

    avoided_<pollutant> [kg] = straw not burnt [t] × BURN_FRACTION × EF_<pollutant> [kg per tonne burnt in the open]

**No emission factor is built in.** The team chooses published, peer-reviewed factors for open
burning of rice straw and sets them in `EMISSION_FACTORS` with their citation:

    EMISSION_FACTORS='{"pm25": {"kg_per_tonne": <value>, "source": "<author, year, journal>", "url": "<doi link>"}}'

A factor without a source is ignored, and a pollutant without a factor is not shown anywhere. With
no factors at all every impact figure is simply absent. Every number is an estimate, never a
measurement, and is labelled so wherever it appears.

When a booking becomes DONE its impact is **snapshotted** onto the booking (`impact`,
`impact_tonnes`, `impact_factors_version`), so history does not silently change if the factors are
edited later. `scripts/backfill_impact.py` fills old bookings and does deliberate recomputes.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from pydantic import BaseModel

from clearsky import clock
from clearsky.config import get_settings
from clearsky.models import Booking, BookingStatus
from clearsky.repo import BookingsRepo, FarmersRepo, VillagesRepo


class Pollutant(BaseModel):
    key: str
    label: str
    unit: str  # display unit: "kg", or "t" for CO₂ (the stored value is always kg)


# The pollutants clearsky can report, in display order. Which of them appear depends on the factors set.
POLLUTANTS: dict[str, Pollutant] = {
    p.key: p
    for p in (
        Pollutant(key="pm25", label="PM2.5", unit="kg"),
        Pollutant(key="pm10", label="PM10", unit="kg"),
        Pollutant(key="co", label="CO", unit="kg"),
        Pollutant(key="co2", label="CO₂", unit="t"),
        Pollutant(key="bc", label="Black carbon", unit="kg"),
    )
}


class Factor(BaseModel):
    kg_per_tonne: float
    source: str
    url: str | None = None


def factors() -> dict[str, Factor]:
    """The configured, sourced emission factors (kg per tonne of straw burnt), in display order."""
    raw = get_settings().emission_factors or {}
    out: dict[str, Factor] = {}
    for key in POLLUTANTS:
        entry = raw.get(key)
        if not isinstance(entry, dict):
            continue
        try:
            value = float(entry.get("kg_per_tonne") or 0)
        except (TypeError, ValueError):
            continue
        source = str(entry.get("source") or "").strip()
        if value <= 0 or not source:  # no citation, no number
            continue
        out[key] = Factor(
            kg_per_tonne=value, source=source, url=str(entry["url"]) if entry.get("url") else None
        )
    return out


def burn_fraction() -> float:
    return min(max(get_settings().burn_fraction, 0.0), 1.0)


def version() -> str | None:
    """Short fingerprint of the factors in force: stored with each snapshot."""
    current = factors()
    if not current:
        return None
    payload = json.dumps(
        {"f": {k: v.model_dump() for k, v in current.items()}, "b": burn_fraction()}, sort_keys=True
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]


def compute(tonnes: float) -> dict[str, float]:
    """Kilograms of each configured pollutant not emitted because `tonnes` of straw were not burnt."""
    scale = tonnes * burn_fraction()
    return {key: round(scale * f.kg_per_tonne, 3) for key, f in factors().items()}


def snapshot(tonnes: float) -> dict[str, Any]:
    """Fields to store on a booking when it is done. Empty when no factors are configured."""
    impact = compute(tonnes)
    if not impact:
        return {}
    return {"impact": impact, "impact_tonnes": tonnes, "impact_factors_version": version()}


def shown(impact: dict[str, float] | None) -> dict[str, float]:
    """A stored snapshot limited to the pollutants that currently have an agreed factor."""
    current = factors()
    return {k: v for k, v in (impact or {}).items() if k in current}


def in_unit(key: str, kg: float) -> float:
    return round(kg / 1000, 2) if POLLUTANTS[key].unit == "t" else round(kg, 1)


def describe() -> dict[str, Any]:
    """Methodology for the API: every factor with its label, unit and citation."""
    current = factors()
    return {
        "configured": bool(current),
        "estimate": True,
        "burn_fraction": burn_fraction(),
        "version": version(),
        "formula": "straw not burnt (t) × emission factor (kg per tonne of rice straw burnt in the open)",
        "factors": {
            key: {
                "label": POLLUTANTS[key].label,
                "unit": POLLUTANTS[key].unit,
                "kg_per_tonne": f.kg_per_tonne,
                "source": f.source,
                "url": f.url,
            }
            for key, f in current.items()
        },
    }


def totals(bookings: list[Booking]) -> dict[str, float]:
    """Sum of the stored snapshots of DONE bookings. Cancelled, declined or open bookings never count."""
    out: dict[str, float] = defaultdict(float)
    for bk in bookings:
        if bk.status != BookingStatus.DONE:
            continue
        for key, kg in shown(bk.impact).items():
            out[key] += kg
    return {k: round(out[k], 3) for k in factors() if k in out}


def display(kg_by_pollutant: dict[str, float]) -> dict[str, dict[str, Any]]:
    """Totals with everything the UI needs to print them: value in the display unit, label, source."""
    current = factors()
    return {
        key: {
            "kg": round(kg, 1),
            "value": in_unit(key, kg),
            "unit": POLLUTANTS[key].unit,
            "label": POLLUTANTS[key].label,
            "source": current[key].source,
            "url": current[key].url,
        }
        for key, kg in kg_by_pollutant.items()
        if key in current
    }


# ------------------------------------------------------------------ public table


def mask_name(name: str | None) -> str | None:
    """ "Gurpreet Singh" → "Gurpreet S." for the public page (no phone numbers, no full names)."""
    parts = (name or "").split()
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][0].upper()}."


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=clock.IST)


def cleared_on(bk: Booking) -> date:
    return _aware(bk.done_at).astimezone(clock.IST).date() if bk.done_at else bk.date


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _running(points: dict[date, float], start: date) -> list[dict[str, Any]]:
    """Cumulative series for a sparkline: starts at zero on `start`, one point per day that added something."""
    total = 0.0
    series = [{"date": start.isoformat(), "cumulative": 0.0}]
    for d in sorted(points):
        total += points[d]
        series.append({"date": d.isoformat(), "cumulative": round(total, 3)})
    return series


def public_table(group: str = "village", period: str = "season") -> dict[str, Any]:
    """Rows for the impact table. Safe for the public page: farmer names are masked ("Gurpreet S."),
    there are no phone numbers and no ids that lead back to a person."""
    current = factors()
    primary = next(iter(current), None)  # the pollutant sparklines and the season chart follow
    start = get_settings().season_start
    done = sorted(
        (b for b in BookingsRepo().list_all() if b.status == BookingStatus.DONE),
        key=lambda b: (cleared_on(b), b.booking_id),
    )
    farmers = {f.phone: f for f in FarmersRepo().list_all()}
    villages = {v.village_id: v for v in VillagesRepo().list_all()}
    weeks = sorted({_week_start(cleared_on(b)) for b in done})

    def by_week(items: list[Booking]) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for bk in items:
            cell = out.setdefault(_week_start(cleared_on(bk)).isoformat(), {})
            for key, kg in shown(bk.impact).items():
                cell[key] = round(cell.get(key, 0.0) + kg, 3)
        return out

    def field_row(bk: Booking) -> dict[str, Any]:
        village = villages.get(bk.village_id)
        village_name = village.name if village else bk.village_id
        farmer = farmers.get(bk.phone)
        impact = shown(bk.impact)
        day = cleared_on(bk)
        row: dict[str, Any] = {
            "label": mask_name(farmer.name if farmer else None) or f"Field in {village_name}",
            "village": village_name,
            "acres": bk.acres,
            "tonnes": bk.impact_tonnes if bk.impact_tonnes is not None else bk.est_tonnes,
            "cleared_date": day.isoformat(),
            "impact": impact,
            "trend": _running({day: impact[primary]}, start) if primary and primary in impact else [],
        }
        if period == "week":
            row["by_week"] = by_week([bk])
        return row

    def summary(label: str, items: list[Booking]) -> dict[str, Any]:
        per_day: dict[date, float] = defaultdict(float)
        for bk in items:
            if primary and primary in shown(bk.impact):
                per_day[cleared_on(bk)] += shown(bk.impact)[primary]
        row: dict[str, Any] = {
            "label": label,
            "fields": len(items),
            "acres": round(sum(b.acres for b in items), 1),
            "tonnes": round(sum(b.est_tonnes for b in items), 1),
            "impact": totals(items),
            "trend": _running(per_day, start) if per_day else [],
        }
        if period == "week":
            row["by_week"] = by_week(items)
        return row

    out: dict[str, Any] = describe() | {
        "group": group,
        "period": period,
        "primary": primary,
        "season": {"from": start.isoformat(), "to": clock.today().isoformat()},
        "weeks": [w.isoformat() for w in weeks],
        "district": summary(f"{get_settings().district} district", done),
    }
    if group == "field":
        out["rows"] = [field_row(b) for b in reversed(done)]
        return out
    grouped: dict[str, list[Booking]] = defaultdict(list)
    for bk in done:
        grouped[bk.village_id].append(bk)
    groups = []
    for village_id, items in grouped.items():
        village = villages.get(village_id)
        row = summary(village.name if village else village_id, items)
        row["village_id"] = village_id
        row["rows"] = [field_row(b) for b in reversed(items)]
        groups.append(row)
    groups.sort(key=lambda g: (-g["tonnes"], g["label"]))
    out["groups"] = groups
    return out
