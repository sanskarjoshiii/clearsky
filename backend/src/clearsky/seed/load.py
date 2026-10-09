"""Load seed JSON into DynamoDB and pre-book selected fields through the real matcher."""

from __future__ import annotations

from datetime import date
from typing import Any

from clearsky.domain import matching
from clearsky.models import Baler, Buyer, Farmer, Field, Village
from clearsky.repo import BalersRepo, BuyersRepo, FarmersRepo, FieldsRepo, VillagesRepo
from clearsky.repo.base import delete_all, table
from clearsky.repo.schema import TABLES


def reset_all() -> dict[str, int]:
    """Delete every item from every table (tables themselves are kept)."""
    out = {}
    for t in TABLES:
        keys = [t.hash_key] + ([t.range_key] if t.range_key else [])
        out[t.name] = delete_all(table(t.name), keys)
    return out


def load(data: dict[str, Any], *, reset: bool = False, prebook: bool = True) -> dict[str, Any]:
    if reset:
        reset_all()
    VillagesRepo().put_many([Village.model_validate(v) for v in data["villages"]])
    BalersRepo().put_many([Baler.model_validate(b) for b in data["balers"]])
    BuyersRepo().put_many([Buyer.model_validate(b) for b in data["buyers"]])
    FarmersRepo().put_many([Farmer.model_validate(f) for f in data["farmers"]])
    FieldsRepo().put_many([Field.model_validate(f) for f in data["fields"]])

    summary: dict[str, Any] = {k: len(data[k]) for k in ("villages", "balers", "buyers", "farmers", "fields")}
    if prebook:
        ref = date.fromisoformat(data["meta"]["reference_date"])
        # seeded history: these pickups are already agreed, so they skip the offer stage
        results = [
            matching.book_pickup(fid, today=ref, auto_accept=True)
            for fid in data["meta"]["prebook_field_ids"]
        ]
        summary["prebooked"] = sum(1 for r in results if isinstance(r, matching.Booked))
        summary["prebook_no_slot"] = [r.field_id for r in results if isinstance(r, matching.NoSlot)]
    return summary
