"""The `Settings` table: small runtime key/value items (e.g. the demo clock)."""

from __future__ import annotations

from datetime import date

from clearsky.repo.base import table


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
