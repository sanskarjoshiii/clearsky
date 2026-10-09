"""The `Settings` table: small runtime key/value items (e.g. the demo clock)."""

from __future__ import annotations

from datetime import date
from typing import Any

from clearsky.models.dynamo import from_dynamo, to_dynamo
from clearsky.repo.base import table

DEMAND_HISTORY_KEEP = 20


class SettingsRepo:
    def __init__(self) -> None:
        self.t = table("Settings")

    def get_clock(self) -> date | None:
        item = self.t.get_item(Key={"key": "clock"}).get("Item")
        if not item or not item.get("today"):
            return None
        return date.fromisoformat(str(item["today"]))

    def set_clock(self, d: date | None) -> None:
        if d is None:
            self.t.delete_item(Key={"key": "clock"})
        else:
            self.t.put_item(Item={"key": "clock", "today": d.isoformat()})

    def demand_history(self, buyer_id: str) -> list[dict[str, Any]]:
        """A buyer's saved demand edits, oldest first (kept here so `Buyers` rows stay small)."""
        item = self.t.get_item(Key={"key": f"demand_history#{buyer_id}"}).get("Item")
        changes: list[dict[str, Any]] = from_dynamo(item.get("changes", [])) if item else []
        return changes

    def add_demand_change(self, buyer_id: str, change: dict[str, Any]) -> None:
        changes = [*self.demand_history(buyer_id), change][-DEMAND_HISTORY_KEEP:]
        self.t.put_item(Item={"key": f"demand_history#{buyer_id}", "changes": to_dynamo(changes)})
