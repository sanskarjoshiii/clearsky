"""GET /health — a cheap liveness check for the HTTP API."""

from __future__ import annotations

import json
from typing import Any

from clearsky import clock
from clearsky.config import get_settings


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    s = get_settings()
    body = {"ok": True, "service": "clearsky", "stage": s.stage, "today": clock.today().isoformat()}
    return {"statusCode": 200, "headers": {"content-type": "application/json"}, "body": json.dumps(body)}
