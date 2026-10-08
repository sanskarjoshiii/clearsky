from __future__ import annotations

from boto3.dynamodb.conditions import Key

from clearsky.models import Alert, from_item, to_item
from clearsky.repo.base import query_all, scan_all, table


class AlertsRepo:
    def __init__(self) -> None:
        self.t = table("Alerts")

    def put(self, a: Alert) -> None:
        self.t.put_item(Item=to_item(a))

    def by_village(self, village_id: str) -> list[Alert]:
        items = query_all(
            self.t, IndexName="village-index", KeyConditionExpression=Key("village_id").eq(village_id)
        )
        return sorted((from_item(Alert, i) for i in items), key=lambda a: a.created_at)

    def list_all(self) -> list[Alert]:
        return sorted((from_item(Alert, i) for i in scan_all(self.t)), key=lambda a: a.created_at)
