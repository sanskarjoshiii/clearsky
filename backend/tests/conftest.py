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
    for k in ("AWS_PROFILE", "DDB_ENDPOINT_URL", "BEDROCK_MODEL_ID", "FIRMS_MAP_KEY", "DATA_BUCKET"):
        monkeypatch.delenv(k, raising=False)
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
    """Mock AWS with every ClearSky table created."""
    with mock_aws():
        reset_clients()
        create_all_tables(ddb_client(), "test-")
        yield
        reset_clients()
