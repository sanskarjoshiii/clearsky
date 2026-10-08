"""All date logic goes through this module (IMPLEMENTATION.md §13).

`today()` returns, in order of precedence:
1. an in-process override (`set_override`, used by tests and `chat_cli --today`),
2. the demo clock stored in the `Settings` table under key `clock` (only when DEMO_MODE is on),
3. the real date in Asia/Kolkata.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone

from clearsky.config import get_settings

# India has no daylight saving, so a fixed offset is exact and avoids needing tzdata on Windows.
IST = timezone(timedelta(hours=5, minutes=30), "IST")

_override: date | None = None
_demo_cache: tuple[float, date | None] | None = None
_DEMO_CACHE_SECONDS = 5.0


def now() -> datetime:
    """Current time in IST. When the demo clock is set, the date part follows it."""
    real = datetime.now(IST)
    d = today()
    if d == real.date():
        return real
    return datetime.combine(d, real.timetz())


def today() -> date:
    if _override is not None:
        return _override
    demo = _demo_today()
    if demo is not None:
        return demo
    return datetime.now(IST).date()


def tomorrow() -> date:
    return today() + timedelta(days=1)


def set_override(d: date | None) -> None:
    global _override
    _override = d


def clear_cache() -> None:
    global _demo_cache
    _demo_cache = None


def set_demo_today(d: date | None) -> None:
    """Persist the demo clock (DEMO_MODE only). `None` returns to the real date."""
    if not get_settings().demo_mode:
        raise RuntimeError("demo clock can only be set when DEMO_MODE is on")
    from clearsky.repo.settings_repo import SettingsRepo

    SettingsRepo().set_clock(d)
    clear_cache()


def _demo_today() -> date | None:
    global _demo_cache
    if not get_settings().demo_mode:
        return None
    t = time.monotonic()
    if _demo_cache is not None and t - _demo_cache[0] < _DEMO_CACHE_SECONDS:
        return _demo_cache[1]
    from clearsky.repo.settings_repo import SettingsRepo

    try:
        value = SettingsRepo().get_clock()
    except Exception:  # table missing or unreachable: fall back to the real date
        value = None
    _demo_cache = (t, value)
    return value


def iso(d: date) -> str:
    return d.isoformat()
