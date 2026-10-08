"""Build and run DynamoDB TransactWriteItems with Python-native values."""

from __future__ import annotations

from typing import Any

from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from clearsky.models.dynamo import to_dynamo
from clearsky.repo.base import ddb_client, table_name

_ser = TypeSerializer()


def _av(value: Any) -> dict[str, Any]:
    return dict(_ser.serialize(to_dynamo(value)))


def _avmap(values: dict[str, Any]) -> dict[str, Any]:
    return {k: _av(v) for k, v in values.items()}


class TransactionCancelled(Exception):
    """One or more conditions failed. `reasons[i]` is the cancellation code for operation i."""

    def __init__(self, reasons: list[str]):
        super().__init__(f"transaction cancelled: {reasons}")
        self.reasons = reasons

    def failed_index(self) -> int | None:
        for i, r in enumerate(self.reasons):
            if r not in ("None", "", None):
                return i
        return None


class TxBuilder:
    def __init__(self) -> None:
        self.ops: list[dict[str, Any]] = []

    def put(
        self,
        table: str,
        item: dict[str, Any],
        condition: str | None = None,
        names: dict[str, str] | None = None,
        values: dict[str, Any] | None = None,
    ) -> TxBuilder:
        op: dict[str, Any] = {"TableName": table_name(table), "Item": _avmap(to_dynamo(item))}
        self._add_condition(op, condition, names, values)
        self.ops.append({"Put": op})
        return self

    def update(
        self,
        table: str,
        key: dict[str, Any],
        update_expression: str,
        values: dict[str, Any] | None = None,
        names: dict[str, str] | None = None,
        condition: str | None = None,
    ) -> TxBuilder:
        op: dict[str, Any] = {
            "TableName": table_name(table),
            "Key": _avmap(key),
            "UpdateExpression": update_expression,
        }
        self._add_condition(op, condition, names, values)
        self.ops.append({"Update": op})
        return self

    @staticmethod
    def _add_condition(
        op: dict[str, Any],
        condition: str | None,
        names: dict[str, str] | None,
        values: dict[str, Any] | None,
    ) -> None:
        if condition:
            op["ConditionExpression"] = condition
        if names:
            op["ExpressionAttributeNames"] = names
        if values:
            op["ExpressionAttributeValues"] = _avmap(values)

    def execute(self) -> None:
        if not self.ops:
            return
        try:
            ddb_client().transact_write_items(TransactItems=self.ops)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") != "TransactionCanceledException":
                raise
            reasons = [r.get("Code", "None") for r in e.response.get("CancellationReasons", [])]
            if not reasons:
                reasons = _parse_reasons(str(e))
            raise TransactionCancelled(reasons) from e


def _parse_reasons(message: str) -> list[str]:
    """Fallback: 'Transaction cancelled, ... reasons [None, ConditionalCheckFailed]'."""
    if "[" not in message:
        return ["Unknown"]
    inner = message[message.rindex("[") + 1 : message.rindex("]")]
    return [p.strip() for p in inner.split(",")]
