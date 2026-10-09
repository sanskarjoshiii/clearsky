"""Every 15 minutes: offers a baler did not answer in time expire and go to the next baler."""

from __future__ import annotations

from typing import Any

from clearsky.domain import offers


def handler(event: dict[str, Any], context: Any) -> dict[str, int]:
    return offers.expire_due()
