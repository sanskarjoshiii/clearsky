from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest
from moto import mock_aws

from clearsky import clock
from clearsky.config import reset_settings
from clearsky.domain import villages
from clearsky.repo.base import ddb_client, reset_clients
from clearsky.repo.schema import create_all_tables

TODAY = date(2026, 10, 20)


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Hermetic settings: fake AWS creds, test table prefix, real clock off, no endpoint override."""
    for k, v in {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": "ap-south-1",
        "AWS_REGION": "ap-south-1",
        "TABLE_PREFIX": "test-",
        "DEMO_MODE": "false",
        "STAGE": "test",
    }.items():
        monkeypatch.setenv(k, v)
    for k, v in {
        "LLM_PROVIDER": "rules",
        "WA_MODE": "simulator",
        "STT_PROVIDER": "none",
        "TTS_PROVIDER": "none",
        "DEV_AUTH": "false",
    }.items():
        monkeypatch.setenv(k, v)
    for k in (
        "AWS_PROFILE",
        "DDB_ENDPOINT_URL",
        "BEDROCK_MODEL_ID",
        "FIRMS_MAP_KEY",
        "DATA_BUCKET",
        "MEDIA_BUCKET",
        "LLM_MODEL_ID",
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "STT_API_KEY",
        "STT_MODEL_ID",
        "INBOUND_QUEUE_URL",
        "WA_ACCESS_TOKEN",
        "WA_APP_SECRET",
        "WA_VERIFY_TOKEN",
        "WA_PHONE_NUMBER_ID",
        # a developer's own settings must not leak into tests
        "AUTO_ACCEPT_DEMO",
        "OFFER_SLA_MINUTES",
        "OFFER_MAX_ATTEMPTS",
        "USER_POOL_ID",
    ):
        monkeypatch.delenv(k, raising=False)
    # Never read a developer's real .env during tests.
    import clearsky.config as cfg

    monkeypatch.setitem(cfg.Settings.model_config, "env_file", None)
    monkeypatch.setattr(cfg, "_dotenv_value", lambda name: None)
    reset_settings()
    reset_clients()
    villages.clear_cache()
    clock.clear_cache()
    clock.set_override(TODAY)
    yield
    clock.set_override(None)
    reset_settings()
    reset_clients()
    villages.clear_cache()


@pytest.fixture
def ddb() -> Iterator[None]:
    """Mock AWS with every clearsky table created."""
    with mock_aws():
        reset_clients()
        create_all_tables(ddb_client(), "test-")
        yield
        reset_clients()
