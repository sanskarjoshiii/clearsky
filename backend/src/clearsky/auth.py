"""Who is calling the dashboard API (IMPLEMENTATION.md §11).

Deployed: API Gateway's Cognito JWT authorizer has already verified the ID token; we read its claims
(`cognito:groups`, `custom:district`, `custom:buyer_id`, `custom:baler_id`).
Local dev only (DEV_AUTH=true): `Authorization: Bearer dev.<role>.<id>` is accepted without a
signature so the dashboard can be exercised with no Cognito. Never enable DEV_AUTH in a shared stack.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from clearsky.config import get_settings

ROLES = ("officer", "buyer", "operator")


@dataclass(frozen=True)
class Principal:
    sub: str
    role: str
    email: str = ""
    district: str | None = None
    buyer_id: str | None = None
    baler_id: str | None = None
    dev: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "sub": self.sub,
            "role": self.role,
            "email": self.email,
            "district": self.district,
            "buyer_id": self.buyer_id,
            "baler_id": self.baler_id,
            "dev": self.dev,
        }


def _groups(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(g) for g in raw]
    if isinstance(raw, str):
        return [g for g in raw.strip("[]").replace(",", " ").split() if g]
    return []


def from_claims(claims: dict[str, Any] | None) -> Principal | None:
    if not claims or not claims.get("sub"):
        return None
    groups = _groups(claims.get("cognito:groups"))
    role = next((r for r in ROLES if r in groups), None)
    if role is None:
        return None
    return Principal(
        sub=str(claims["sub"]),
        role=role,
        email=str(claims.get("email", "")),
        district=claims.get("custom:district"),
        buyer_id=claims.get("custom:buyer_id"),
        baler_id=claims.get("custom:baler_id"),
    )


def dev_token(role: str, ident: str | None) -> str:
    return f"dev.{role}.{ident or role}"


def from_dev_header(authorization: str | None) -> Principal | None:
    if not get_settings().dev_auth or not authorization:
        return None
    token = authorization.removeprefix("Bearer ").strip()
    parts = token.split(".", 2)
    if len(parts) != 3 or parts[0] != "dev" or parts[1] not in ROLES:
        return None
    role, ident = parts[1], parts[2]
    return Principal(
        sub=f"dev-{role}-{ident}",
        role=role,
        email=f"{role}@dev.local",
        district=ident if role == "officer" and ident != "officer" else None,
        buyer_id=ident if role == "buyer" else None,
        baler_id=ident if role == "operator" else None,
        dev=True,
    )
