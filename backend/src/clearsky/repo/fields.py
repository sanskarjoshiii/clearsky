from __future__ import annotations

from datetime import date
from typing import Any

from boto3.dynamodb.conditions import Key

from clearsky.models import Field, FieldStatus, from_item, to_item
from clearsky.models.dynamo import to_dynamo
from clearsky.repo.base import batch_put, query_all, scan_all, table


class FieldsRepo:
    def __init__(self) -> None:
        self.t = table("Fields")

    def get(self, field_id: str) -> Field | None:
        item = self.t.get_item(Key={"field_id": field_id}).get("Item")
        return from_item(Field, item) if item else None

    def put(self, f: Field) -> None:
        self.t.put_item(Item=to_item(f))

    def put_many(self, fields: list[Field]) -> None:
        batch_put(self.t, [to_item(f) for f in fields])

    def list_all(self) -> list[Field]:
        return [from_item(Field, i) for i in scan_all(self.t)]

    def by_farmer(self, phone: str) -> list[Field]:
        items = query_all(self.t, IndexName="farmer-index", KeyConditionExpression=Key("phone").eq(phone))
        return sorted((from_item(Field, i) for i in items), key=lambda f: f.created_at)

    def by_village(self, village_id: str, start: date | None = None, end: date | None = None) -> list[Field]:
        cond: Any = Key("village_id").eq(village_id)
        if start and end:
            cond = cond & Key("harvest_date").between(start.isoformat(), end.isoformat())
        items = query_all(self.t, IndexName="village-index", KeyConditionExpression=cond)
        return [from_item(Field, i) for i in items]

    def by_status(self, status: FieldStatus) -> list[Field]:
        items = query_all(
            self.t, IndexName="status-index", KeyConditionExpression=Key("status").eq(status.value)
        )
        return [from_item(Field, i) for i in items]

    def update(self, field_id: str, values: dict[str, Any], remove: list[str] | None = None) -> Field:
        names = {f"#{k}": k for k in values} | {f"#{k}": k for k in remove or []}
        parts = []
        if values:
            parts.append("SET " + ", ".join(f"#{k} = :{k}" for k in values))
        if remove:
            parts.append("REMOVE " + ", ".join(f"#{k}" for k in remove))
        kwargs: dict[str, Any] = {
            "Key": {"field_id": field_id},
            "UpdateExpression": " ".join(parts),
            "ExpressionAttributeNames": names,
            "ConditionExpression": "attribute_exists(field_id)",
            "ReturnValues": "ALL_NEW",
        }
        if values:
            kwargs["ExpressionAttributeValues"] = {f":{k}": to_dynamo(_plain(v)) for k, v in values.items()}
        resp = self.t.update_item(**kwargs)
        return from_item(Field, resp["Attributes"])


def _plain(v: Any) -> Any:
    if isinstance(v, date):
        return v.isoformat()
    if hasattr(v, "value"):  # enums
        return v.value
    return v
