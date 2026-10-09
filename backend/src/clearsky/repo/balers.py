from __future__ import annotations

from datetime import date

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from clearsky.models import Baler, BalerDay, from_item, to_item
from clearsky.repo.base import batch_put, query_all, scan_all, table


class BalersRepo:
    def __init__(self) -> None:
        self.t = table("Balers")

    def get(self, baler_id: str) -> Baler | None:
        item = self.t.get_item(Key={"baler_id": baler_id}).get("Item")
        return from_item(Baler, item) if item else None

    def put(self, b: Baler) -> None:
        self.t.put_item(Item=to_item(b))

    def put_new(self, b: Baler) -> bool:
        """Create a baler only if the id is free. False = the id was taken meanwhile."""
        try:
            self.t.put_item(Item=to_item(b), ConditionExpression="attribute_not_exists(baler_id)")
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise
        return True

    def put_many(self, balers: list[Baler]) -> None:
        batch_put(self.t, [to_item(b) for b in balers])

    def list_all(self) -> list[Baler]:
        return [from_item(Baler, i) for i in scan_all(self.t)]

    def list_active(self) -> list[Baler]:
        return [b for b in self.list_all() if b.active]


class BalerDaysRepo:
    """Capacity ledger: one item per (baler, date)."""

    def __init__(self) -> None:
        self.t = table("BalerDays")

    def get(self, baler_id: str, d: date) -> BalerDay | None:
        item = self.t.get_item(Key={"baler_id": baler_id, "date": d.isoformat()}).get("Item")
        return from_item(BalerDay, item) if item else None

    def range(self, baler_id: str, start: date, end: date) -> dict[date, BalerDay]:
        cond = Key("baler_id").eq(baler_id) & Key("date").between(start.isoformat(), end.isoformat())
        days = (from_item(BalerDay, i) for i in query_all(self.t, KeyConditionExpression=cond))
        return {d.date: d for d in days}

    def put_many(self, days: list[BalerDay]) -> None:
        batch_put(self.t, [to_item(d) for d in days])
