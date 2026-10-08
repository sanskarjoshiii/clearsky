from __future__ import annotations

from boto3.dynamodb.conditions import Key

from clearsky.models import Farmer, from_item, to_item
from clearsky.repo.base import batch_put, query_all, scan_all, table


class FarmersRepo:
    def __init__(self) -> None:
        self.t = table("Farmers")

    def get(self, phone: str) -> Farmer | None:
        item = self.t.get_item(Key={"phone": phone}).get("Item")
        return from_item(Farmer, item) if item else None

    def put(self, f: Farmer) -> None:
        self.t.put_item(Item=to_item(f))

    def put_many(self, farmers: list[Farmer]) -> None:
        batch_put(self.t, [to_item(f) for f in farmers])

    def by_village(self, village_id: str) -> list[Farmer]:
        items = query_all(
            self.t, IndexName="village-index", KeyConditionExpression=Key("village_id").eq(village_id)
        )
        return [from_item(Farmer, i) for i in items]

    def list_all(self) -> list[Farmer]:
        return [from_item(Farmer, i) for i in scan_all(self.t)]
