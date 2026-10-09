"""Central configuration. Every setting is read here (IMPLEMENTATION.md §13).

Plain settings come from environment variables (or a local `.env`). Secrets come from SSM Parameter
Store under `/clearsky/{stage}/...`, are loaded lazily, and cached. An env var with the same name
overrides SSM, which keeps local development and tests offline.
"""

from __future__ import annotations

import os
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_ignore_empty=True,  # `BEDROCK_MODEL_ID=` in .env means "unset", not ""
    )

    # Deployment
    stage: str = "dev"
    aws_region: str = "ap-south-1"
    table_prefix: str = "clearsky-dev-"
    media_bucket: str | None = None
    data_bucket: str | None = None
    inbound_queue_url: str | None = None
    ddb_endpoint_url: str | None = None  # local DynamoDB / moto server; None means real AWS

    # Agent. LLM_PROVIDER picks the brain of the farmer agent:
    #   rules     deterministic slot-filling bot, no LLM, works offline (default; safe fallback)
    #   openai    OpenAI or any OpenAI-compatible API (set LLM_BASE_URL, e.g. Groq/OpenRouter)
    #   anthropic Anthropic API      gemini  Google Gemini API      bedrock  Amazon Bedrock
    # Model IDs are never defaulted: the team sets LLM_MODEL_ID (or BEDROCK_MODEL_ID for bedrock).
    llm_provider: str = "rules"
    llm_model_id: str | None = None
    llm_base_url: str | None = None
    bedrock_model_id: str | None = None
    agent_temperature: float = 0.2
    agent_max_tokens: int = 600
    history_turns: int = 10
    rate_limit_per_hour: int = 20  # agent turns per farmer phone

    # WhatsApp. WA_MODE=simulator records outbound messages (dashboard simulator) instead of calling
    # Meta; WA_MODE=cloud sends through the WhatsApp Cloud API with the WA_* secrets.
    wa_mode: str = "simulator"
    wa_api_version: str = "v23.0"
    wa_template_language: str = "hi"

    # Voice. STT_PROVIDER: transcribe (Amazon Transcribe) | openai (OpenAI-compatible
    # /audio/transcriptions, needs STT_MODEL_ID) | none. TTS_PROVIDER: polly | none.
    stt_provider: str = "none"
    stt_model_id: str | None = None
    stt_base_url: str | None = None
    tts_provider: str = "polly"
    max_voice_seconds: int = 60
    transcribe_language: str = "hi-IN"
    polly_voice: str = "Kajal"
    polly_engine: str = "neural"

    # Dashboard / API
    dev_auth: bool = False  # NEVER true in a shared deployment: accepts unsigned role tokens
    # Local dev sign-in only (DEV_AUTH): every dev account uses this password. Not a real secret; the
    # deployed dashboard uses Cognito passwords.
    dev_password: str = "clearsky-dev"
    user_pool_id: str | None = (
        None  # Cognito pool for approving self-registered users; None = no Cognito calls
    )
    cors_origins: str = "*"
    route_calculator_name: str | None = None  # Amazon Location route calculator; None = straight lines
    alert_cooldown_minutes: int = 30

    # Season and agronomy
    district: str = "Sangrur"
    # Approximate Sangrur district bbox: west, south, east, north. Confirm before production use.
    district_bbox: tuple[float, float, float, float] = (75.55, 29.75, 76.40, 30.50)
    tonnes_per_acre: float = 2.5
    sowing_window_days: int = 20
    sowing_buffer_days: int = 2
    season_start: date = date(2026, 9, 15)
    season_sowing_cutoff: date = date(2026, 11, 15)
    harvest_lookback_days: int = 15  # oldest harvest date a farmer may register, relative to today

    # Matching weights (IMPLEMENTATION.md §4)
    w_dist: float = 1.0
    w_delay: float = 2.0
    w_cluster: float = 5.0
    matcher_max_attempts: int = 3

    # Offers: a booking is first offered to the best baler, who accepts or declines on the dashboard.
    offer_sla_minutes: int = 120  # no answer in this time → the offer expires and goes to the next baler
    offer_max_attempts: int = 3  # after this many balers, escalate to the officer
    auto_accept_demo: bool = False  # true = book instantly as CONFIRMED (the pre-offer behaviour)

    # Pricing: DEMO PARAMETERS ONLY, never shown as real market prices (IMPLEMENTATION.md §5)
    baling_cost_per_acre: float = 600.0
    transport_cost_per_tonne_km: float = 8.0
    platform_fee_per_tonne: float = 50.0

    # Risk levels (IMPLEMENTATION.md §6; see domain/risk.py for why RED is 60)
    risk_red_at: int = 60
    risk_yellow_at: int = 40

    # Impact (issue #5): sourced emission factors, in kg per tonne of rice straw burnt in the open.
    #   EMISSION_FACTORS='{"pm25": {"kg_per_tonne": <value>, "source": "<citation>", "url": "<link>"}}'
    # Pollutants: pm25, pm10, co, co2, bc. NEVER defaulted: the team picks published values and records
    # the citation (domain/impact.py). A factor without a source is ignored; empty = no impact shown.
    emission_factors: dict[str, Any] = {}  # entries are validated one by one in domain/impact.py
    burn_fraction: float = 1.0  # share of unbooked straw assumed burnt; below 1 needs its own citation

    # FIRMS
    village_radius_km: float = 3.0
    firms_source: str = "VIIRS_SNPP_SP"
    firms_years: tuple[int, ...] = (2022, 2023, 2024, 2025)
    firms_day_range: int = 5

    # Demo
    demo_mode: bool = True

    # Logging
    log_level: str = "INFO"
    service_name: str = "clearsky"

    @property
    def ssm_prefix(self) -> str:
        return f"/clearsky/{self.stage}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings() -> None:
    """Drop cached settings and secrets (tests and scripts that change env vars)."""
    get_settings.cache_clear()
    _secret_cache.clear()


class _SettingsProxy:
    """`clearsky.config.settings` resolves to the cached Settings at attribute access time."""

    def __getattr__(self, name: str) -> object:
        return getattr(get_settings(), name)


settings: Settings = _SettingsProxy()  # type: ignore[assignment]


# ---------------------------------------------------------------- secrets

SECRET_NAMES = {
    "WA_PHONE_NUMBER_ID": "wa/phone_number_id",
    "WA_ACCESS_TOKEN": "wa/access_token",
    "WA_APP_SECRET": "wa/app_secret",
    "WA_VERIFY_TOKEN": "wa/verify_token",
    "FIRMS_MAP_KEY": "firms/map_key",
    "LLM_API_KEY": "llm/api_key",
    "STT_API_KEY": "stt/api_key",
}


def get_optional_secret(name: str) -> str | None:
    try:
        return get_secret(name)
    except MissingSecretError:
        return None


_secret_cache: dict[str, str] = {}


class MissingSecretError(RuntimeError):
    pass


def get_secret(name: str) -> str:
    """Return a secret by env-var name, e.g. `get_secret("FIRMS_MAP_KEY")`.

    Order: process env / .env → SSM SecureString `/clearsky/{stage}/<path>`. Cached per process.
    """
    if name in _secret_cache:
        return _secret_cache[name]
    if name not in SECRET_NAMES:
        raise KeyError(f"unknown secret {name}")

    value = os.environ.get(name) or _dotenv_value(name)
    if not value:
        value = _ssm_value(f"{get_settings().ssm_prefix}/{SECRET_NAMES[name]}")
    if not value:
        raise MissingSecretError(
            f"{name} is not set (env var or SSM {get_settings().ssm_prefix}/{SECRET_NAMES[name]})"
        )
    _secret_cache[name] = value
    return value


def _dotenv_value(name: str) -> str | None:
    from dotenv import dotenv_values

    for path in (REPO_ROOT / ".env", Path(".env")):
        if path.exists():
            v = dotenv_values(path).get(name)
            if v:
                return v
    return None


def _ssm_value(path: str) -> str | None:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    try:
        client = boto3.client("ssm", region_name=get_settings().aws_region)
        resp = client.get_parameter(Name=path, WithDecryption=True)
        return str(resp["Parameter"]["Value"])
    except (ClientError, BotoCoreError):
        return None
