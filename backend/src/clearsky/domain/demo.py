"""Demo mode (IMPLEMENTATION.md §18): replay a whole season in minutes. DEMO_MODE only."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from clearsky import clock
from clearsky.config import get_settings
from clearsky.domain import risk
from clearsky.models import FieldStatus
from clearsky.repo import FieldsRepo, VillagesRepo


class DemoError(ValueError):
    pass


def require_demo() -> None:
    if not get_settings().demo_mode:
        raise DemoError("demo mode is off")


def get_clock() -> dict[str, Any]:
    from clearsky.repo import SettingsRepo

    stored = SettingsRepo().get_clock() if get_settings().demo_mode else None
    return {
        "today": clock.today().isoformat(),
        "simulated": stored is not None,
        "demo_mode": get_settings().demo_mode,
    }


def set_clock(value: str | None) -> dict[str, Any]:
    require_demo()
    clock.set_demo_today(date.fromisoformat(value) if value else None)
    return get_clock()


def harvest_wave(village_id: str | None = None, n: int = 5) -> dict[str, Any]:
    """Mark up to n unbooked fields in a village as harvested 3 days ago with sowing in 4 days.

    They turn RED where the village has a high FIRMS fire history (or no baler is free).
    """
    require_demo()
    today = clock.today()
    fields_repo = FieldsRepo()
    villages = VillagesRepo().list_all()
    if village_id is None:
        open_by_village: dict[str, int] = {}
        for f in fields_repo.list_all():
            if f.status in (FieldStatus.REGISTERED, FieldStatus.HARVESTED):
                open_by_village[f.village_id] = open_by_village.get(f.village_id, 0) + 1
        # The village most likely to burn: highest fire history among villages with open fields.
        ranked = sorted(
            (v for v in villages if open_by_village.get(v.village_id)),
            key=lambda v: (-v.fire_history_score, -open_by_village.get(v.village_id, 0), v.village_id),
        )
        if not ranked:
            raise DemoError("no village has unbooked fields")
        village_id = ranked[0].village_id
    targets = [
        f
        for f in fields_repo.by_village(village_id)
        if f.status in (FieldStatus.REGISTERED, FieldStatus.HARVESTED)
    ][:n]
    for f in targets:
        fields_repo.update(
            f.field_id,
            {
                "harvest_date": today - timedelta(days=3),
                "harvest_confirmed": True,
                "status": FieldStatus.HARVESTED,
                # 4 days to sowing: urgent, but still bookable (window = deadline − 2-day buffer)
                "sowing_deadline": today + timedelta(days=4),
                "updated_at": clock.now().isoformat(),
            },
        )
    for f in targets:
        risk.refresh_field(f.field_id, today)
    return {"village_id": village_id, "fields": [f.field_id for f in targets]}


def reset() -> dict[str, Any]:
    """Reload the seed, set the clock to the seed's reference date, score risk."""
    require_demo()
    from clearsky.seed.generate import SEED_DIR, generate, read
    from clearsky.seed.load import load

    data = read() if (SEED_DIR / "villages.json").exists() else generate()
    summary = load(data, reset=True, prebook=True)
    clock.set_demo_today(date.fromisoformat(data["meta"]["reference_date"]))
    summary["risk"] = risk.run_all()
    summary["today"] = clock.today().isoformat()
    return summary


def simulate(action: str, village_id: str | None = None, n: int = 5) -> dict[str, Any]:
    require_demo()
    if action == "harvest_wave":
        return harvest_wave(village_id, n)
    if action == "run_risk":
        return risk.run_all()
    if action == "run_reminders":
        from clearsky.handlers.reminders import run

        return run(force=True)
    if action == "reset":
        return reset()
    raise DemoError(f"unknown action {action!r}")
