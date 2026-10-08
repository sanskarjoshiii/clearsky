"""Model ⇄ DynamoDB item conversion. DynamoDB needs Decimal instead of float; dates are ISO strings."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel


def to_dynamo(value: Any) -> Any:
    """Recursively convert floats to Decimal and drop None values (DynamoDB rejects floats)."""
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: to_dynamo(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [to_dynamo(v) for v in value]
    return value


def from_dynamo(value: Any) -> Any:
    """Recursively convert Decimal to int (if integral) or float."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: from_dynamo(v) for k, v in value.items()}
    if isinstance(value, list | set):
        return [from_dynamo(v) for v in value]
    return value


def to_item(model: BaseModel) -> dict[str, Any]:
    item: dict[str, Any] = to_dynamo(model.model_dump(mode="json", exclude_none=True))
    return item


def from_item[M: BaseModel](cls: type[M], item: dict[str, Any]) -> M:
    return cls.model_validate(from_dynamo(item))
