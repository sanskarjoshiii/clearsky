"""Hourly risk scoring (EventBridge Scheduler), also invokable on demand. IMPLEMENTATION.md §2.7."""

from __future__ import annotations

from typing import Any

from clearsky.domain.risk import run_all
from clearsky.logging import get_logger

log = get_logger(child="risk_job")


def handler(event: dict[str, Any], context: Any) -> dict[str, int]:
    counts = run_all()
    log.info("risk scored", extra=counts)
    return counts
