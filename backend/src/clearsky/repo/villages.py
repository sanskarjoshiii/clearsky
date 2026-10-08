from __future__ import annotations

from typing import Any

from boto3.dynamodb.conditions import Key

from clearsky.models import Village, from_item, to_item
from clearsky.repo.base import batch_put, query_all, scan_all, table


class VillagesRepo:
    def __init__(self) -> None:
        self.t = table("Villages")

    def get(self, village_id: str) -> Village | None:
        item = self.t.get_item(Key={"village_id": village_id}).get("Item")
        return from_item(Village, item) if item else None

    def put(self, v: Village) -> None:
        self.t.put_item(Item=to_item(v))

    def put_many(self, villages: list[Village]) -> None:
        batch_put(self.t, [to_item(v) for v in villages])

    def list_all(self) -> list[Village]:
        return [from_item(Village, i) for i in scan_all(self.t)]

    def by_district(self, district: str) -> list[Village]:
        items = query_all(
            self.t, IndexName="district-index", KeyConditionExpression=Key("district").eq(district)
        )
        return [from_item(Village, i) for i in items]

    def update_fields(self, village_id: str, values: dict[str, Any]) -> None:
        from clearsky.models.dynamo import to_dynamo

        names = {f"#{k}": k for k in values}
        expr = "SET " + ", ".join(f"#{k} = :{k}" for k in values)
        self.t.update_item(
            Key={"village_id": village_id},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues={f":{k}": to_dynamo(v) for k, v in values.items()},
        )
