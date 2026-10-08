"""Burn-risk scoring (IMPLEMENTATION.md §6): which fields are likely to be burnt soon.

score = 100 × (0.45·urgency + 0.25·no_capacity + 0.30·fire_history) × (1 if harvested else 0.35)
RED ≥ RISK_RED_AT (60), YELLOW ≥ RISK_YELLOW_AT (40), else GREEN. Booked/cleared are 0; a fire is 100.

Why RED is 60, not the 70 first proposed: a field must have ≥ 3 days to sowing to still be bookable
(SOWING_BUFFER_DAYS=2), and at 3 days even a maximum fire history gives 68. With 70, a bookable field
could never be RED, so "alert → farmer taps HAAN → booked → GREEN" (Phase 6 DoD) was impossible.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel

from clearsky import clock
from clearsky.config import get_settings
from clearsky.models import Field, FieldStatus, RiskLevel, Village
from clearsky.repo import FieldsRepo, VillagesRepo

HIGH_HISTORY = 0.6


class RiskResult(BaseModel):
    score: int
    level: RiskLevel
    reasons: list[str]


def level_for(score: int) -> RiskLevel:
    s = get_settings()
    if score >= s.risk_red_at:
        return RiskLevel.RED
    if score >= s.risk_yellow_at:
        return RiskLevel.YELLOW
    return RiskLevel.GREEN


def score_field(field: Field, fire_history: float, today: date, slot_available: bool) -> RiskResult:
    if field.status == FieldStatus.BOOKED:
        return RiskResult(score=0, level=RiskLevel.GREEN, reasons=["booked"])
    if field.status == FieldStatus.CLEARED:
        return RiskResult(score=0, level=RiskLevel.GREEN, reasons=["cleared"])
    if field.status == FieldStatus.FIRE_REPORTED:
        return RiskResult(score=100, level=RiskLevel.RED, reasons=["fire reported"])

    window = get_settings().sowing_window_days
    harvested = field.harvest_confirmed or today >= field.harvest_date
    days_left = (field.sowing_deadline - today).days
    urgency = min(max(1 - days_left / window, 0.0), 1.0)
    history = min(max(fire_history, 0.0), 1.0)
    base = 0.45 * urgency + 0.25 * (0 if slot_available else 1) + 0.30 * history
    score = round(100 * base * (1.0 if harvested else 0.35))

    reasons: list[str] = []
    if harvested:
        ago = (today - field.harvest_date).days
        reasons.append("harvested today" if ago <= 0 else f"harvested {ago} day{'s' if ago != 1 else ''} ago")
    else:
        reasons.append(f"harvest in {(field.harvest_date - today).days} days")
    reasons.append(f"{days_left} days to sowing" if days_left >= 0 else "sowing deadline passed")
    if history >= HIGH_HISTORY:
        reasons.append("high fire history")
    if not slot_available:
        reasons.append("no baler free")
    reasons.append("not booked")
    return RiskResult(score=score, level=level_for(score), reasons=reasons)


def _apply(field: Field, result: RiskResult) -> None:
    FieldsRepo().update(
        field.field_id,
        {
            "risk_score": result.score,
            "risk_level": result.level,
            "risk_reasons": result.reasons,
        },
    )


def refresh_field(field_id: str, today: date | None = None) -> RiskResult | None:
    """Recompute one field's risk now (after booking, cancel, harvest confirmation)."""
    from clearsky.domain.matching import has_capacity_before_deadline

    today = today or clock.today()
    field = FieldsRepo().get(field_id)
    if field is None:
        return None
    village = VillagesRepo().get(field.village_id)
    open_ = field.status in (FieldStatus.REGISTERED, FieldStatus.HARVESTED)
    slot = has_capacity_before_deadline(field, today) if open_ else True
    result = score_field(field, village.fire_history_score if village else 0.0, today, slot)
    _apply(field, result)
    refresh_village(field.village_id)
    return result


def aggregate(villages: list[Village], fields: list[Field]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {
        v.village_id: {
            "risk_unbooked_acres": 0.0,
            "risk_red_fields": 0,
            "risk_yellow_fields": 0,
            "risk_max_score": 0,
        }
        for v in villages
    }
    for f in fields:
        agg = out.get(f.village_id)
        if agg is None:
            continue
        if f.status in (FieldStatus.REGISTERED, FieldStatus.HARVESTED):
            agg["risk_unbooked_acres"] += f.acres
        if f.risk_level == RiskLevel.RED:
            agg["risk_red_fields"] += 1
        elif f.risk_level == RiskLevel.YELLOW:
            agg["risk_yellow_fields"] += 1
        agg["risk_max_score"] = max(agg["risk_max_score"], f.risk_score)
    return out


def refresh_village(village_id: str) -> None:
    village = VillagesRepo().get(village_id)
    if village is None:
        return
    agg = aggregate([village], FieldsRepo().by_village(village_id))[village_id]
    VillagesRepo().update_fields(village_id, agg)


def run_all(today: date | None = None) -> dict[str, int]:
    """The hourly job: score every field, then every village aggregate."""
    from clearsky.domain.matching import has_capacity_before_deadline

    today = today or clock.today()
    villages = VillagesRepo().list_all()
    history = {v.village_id: v.fire_history_score for v in villages}
    fields = FieldsRepo().list_all()
    updated: list[Field] = []
    counts = {"fields": 0, "red": 0, "yellow": 0, "green": 0}
    for f in fields:
        open_ = f.status in (FieldStatus.REGISTERED, FieldStatus.HARVESTED)
        slot = has_capacity_before_deadline(f, today) if open_ else True
        r = score_field(f, history.get(f.village_id, 0.0), today, slot)
        if (r.score, r.level, r.reasons) != (f.risk_score, f.risk_level, f.risk_reasons):
            _apply(f, r)
        updated.append(
            f.model_copy(update={"risk_score": r.score, "risk_level": r.level, "risk_reasons": r.reasons})
        )
        counts["fields"] += 1
        counts[r.level.value.lower()] += 1
    for vid, agg in aggregate(villages, updated).items():
        VillagesRepo().update_fields(vid, agg)
    counts["villages"] = len(villages)
    return counts
