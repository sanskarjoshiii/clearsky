"""Phase 0: config, clock, logging, health handler."""

from __future__ import annotations

import json
from datetime import date

import pytest

from clearsky import clock
from clearsky.config import MissingSecretError, get_secret, get_settings, reset_settings, settings
from clearsky.handlers import health
from clearsky.logging import mask_phone, mask_phones_in_text


def test_settings_defaults_and_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    assert get_settings().table_prefix == "test-"
    assert settings.aws_region == "ap-south-1"
    assert get_settings().ssm_prefix == "/clearsky/test"
    monkeypatch.setenv("TONNES_PER_ACRE", "3.0")
    reset_settings()
    assert settings.tonnes_per_acre == 3.0


def test_bedrock_model_id_has_no_default() -> None:
    assert get_settings().bedrock_model_id is None


def test_secret_from_env_and_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRMS_MAP_KEY", "abc")
    assert get_secret("FIRMS_MAP_KEY") == "abc"
    with pytest.raises(KeyError):
        get_secret("NOPE")


def test_rotated_secret_is_picked_up_after_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    import clearsky.config as cfg

    now = [1000.0]
    monkeypatch.setattr(cfg.time, "monotonic", lambda: now[0])
    monkeypatch.setenv("WA_ACCESS_TOKEN", "old")
    assert get_secret("WA_ACCESS_TOKEN") == "old"
    monkeypatch.setenv("WA_ACCESS_TOKEN", "new")
    assert get_secret("WA_ACCESS_TOKEN") == "old"  # still cached
    now[0] += cfg.SECRET_TTL_S
    assert get_secret("WA_ACCESS_TOKEN") == "new"


def test_missing_secret_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import clearsky.config as cfg

    monkeypatch.setattr(cfg, "_dotenv_value", lambda name: None)
    monkeypatch.setattr(cfg, "_ssm_value", lambda path: None)
    with pytest.raises(MissingSecretError):
        get_secret("WA_APP_SECRET")


def test_mask_phone() -> None:
    assert mask_phone("+919800000001") == "+91******0001"
    assert mask_phone("") == ""
    assert mask_phone("123") == "***"
    assert "0001" in mask_phones_in_text("call +919800000001 now")
    assert "980000" not in mask_phones_in_text("call +919800000001 now")


def test_clock_override() -> None:
    clock.set_override(date(2026, 10, 24))
    assert clock.today() == date(2026, 10, 24)
    assert clock.tomorrow() == date(2026, 10, 25)
    assert clock.now().date() == date(2026, 10, 24)
    assert clock.now().tzinfo is not None


def test_demo_clock_from_settings_table(ddb: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "true")
    reset_settings()
    clock.set_override(None)
    clock.set_demo_today(date(2026, 10, 26))
    assert clock.today() == date(2026, 10, 26)
    clock.set_demo_today(None)
    assert clock.today() != date(2026, 10, 26) or date.today() == date(2026, 10, 26)


def test_demo_clock_refused_outside_demo_mode() -> None:
    with pytest.raises(RuntimeError):
        clock.set_demo_today(date(2026, 10, 26))


def test_health_handler() -> None:
    resp = health.handler({}, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["ok"] is True and body["today"] == "2026-10-20"
