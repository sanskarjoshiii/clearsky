"""Builds the Strands model for the configured LLM provider (see `LLM_PROVIDER` in config.py).

The farmer agent is provider-agnostic: tools, prompt and memory are identical for every provider.
`rules` has no model at all; `agent.run_turn` routes it to the deterministic bot in `agent/rules.py`.
"""

from __future__ import annotations

from strands.models.model import Model

from clearsky.config import get_optional_secret, get_settings

PROVIDERS = ("rules", "openai", "anthropic", "gemini", "bedrock")


class LLMConfigError(RuntimeError):
    pass


def provider() -> str:
    p = get_settings().llm_provider.strip().lower()
    if p not in PROVIDERS:
        raise LLMConfigError(f"LLM_PROVIDER={p!r} is not one of {', '.join(PROVIDERS)}")
    return p


def build_model() -> Model:
    """The Strands model for the current provider. Raises LLMConfigError with a fix-it message."""
    s = get_settings()
    p = provider()
    if p == "rules":
        raise LLMConfigError("LLM_PROVIDER=rules has no model; use agent.rules instead")

    if p == "bedrock":
        if not s.bedrock_model_id:
            raise LLMConfigError("LLM_PROVIDER=bedrock needs BEDROCK_MODEL_ID")
        from strands.models import BedrockModel

        return BedrockModel(
            model_id=s.bedrock_model_id,
            temperature=s.agent_temperature,
            max_tokens=s.agent_max_tokens,
            region_name=s.aws_region,
        )

    if not s.llm_model_id:
        raise LLMConfigError(f"LLM_PROVIDER={p} needs LLM_MODEL_ID (the team chooses the model)")
    key = get_optional_secret("LLM_API_KEY")
    if not key:
        raise LLMConfigError(f"LLM_PROVIDER={p} needs LLM_API_KEY (in .env locally, SSM when deployed)")

    if p == "openai":
        from strands.models.openai import OpenAIModel

        client_args: dict[str, str] = {"api_key": key}
        if s.llm_base_url:
            client_args["base_url"] = s.llm_base_url
        return OpenAIModel(
            client_args=client_args,
            model_id=s.llm_model_id,
            params={"temperature": s.agent_temperature, "max_tokens": s.agent_max_tokens},
        )
    if p == "anthropic":
        from strands.models.anthropic import AnthropicModel

        return AnthropicModel(
            client_args={"api_key": key},
            model_id=s.llm_model_id,
            max_tokens=s.agent_max_tokens,
            params={"temperature": s.agent_temperature},
        )
    from strands.models.gemini import GeminiModel

    return GeminiModel(
        client_args={"api_key": key},
        model_id=s.llm_model_id,
        params={"temperature": s.agent_temperature, "max_output_tokens": s.agent_max_tokens},
    )


def describe() -> str:
    """Human-readable provider/model, for logs and the CLI banner (never includes the key)."""
    s = get_settings()
    p = s.llm_provider
    if p == "rules":
        return "rules (no LLM)"
    if p == "bedrock":
        return f"bedrock:{s.bedrock_model_id or '(unset)'}"
    return f"{p}:{s.llm_model_id or '(unset)'}"
