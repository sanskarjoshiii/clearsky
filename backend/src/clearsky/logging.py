"""Structured logging (Powertools) and PII masking. Never log a full phone number."""

from __future__ import annotations

import re

from aws_lambda_powertools import Logger

from clearsky.config import get_settings

_PHONE_RE = re.compile(r"\+?\d{10,15}")


def get_logger(child: str | None = None) -> Logger:
    s = get_settings()
    if child:
        return Logger(service=s.service_name, level=s.log_level, child=True)
    return Logger(service=s.service_name, level=s.log_level)


def mask_phone(phone: str | None) -> str:
    """`+919812340001` → `+91******0001`. Non-phone input is masked conservatively."""
    if not phone:
        return ""
    digits = phone.lstrip("+")
    if len(digits) < 8:
        return "*" * len(phone)
    prefix = "+" if phone.startswith("+") else ""
    return f"{prefix}{digits[:2]}{'*' * (len(digits) - 6)}{digits[-4:]}"


def mask_phones_in_text(text: str) -> str:
    return _PHONE_RE.sub(lambda m: mask_phone(m.group(0)), text)
