from __future__ import annotations

from datetime import date

from boto3.dynamodb.conditions import Key

from clearsky.models import Booking, BookingStatus, from_item, to_item
from clearsky.repo.base import batch_put, query_all, scan_all, table


class BookingsRepo:
    def __init__(self) -> None:
        self.t = table("Bookings")

    def get(self, booking_id: str) -> Booking | None:
        item = self.t.get_item(Key={"booking_id": booking_id}).get("Item")
        return from_item(Booking, item) if item else None

    def put(self, b: Booking) -> None:
        self.t.put_item(Item=to_item(b))

    def put_many(self, bookings: list[Booking]) -> None:
        batch_put(self.t, [to_item(b) for b in bookings])

    def list_all(self) -> list[Booking]:
        return [from_item(Booking, i) for i in scan_all(self.t)]

    def by_baler(self, baler_id: str, start: date, end: date | None = None) -> list[Booking]:
        end = end or start
        cond = Key("baler_id").eq(baler_id) & Key("date").between(start.isoformat(), end.isoformat())
        items = query_all(self.t, IndexName="baler-date-index", KeyConditionExpression=cond)
        return [from_item(Booking, i) for i in items]

    def confirmed_by_baler(self, baler_id: str, start: date, end: date | None = None) -> list[Booking]:
        return [b for b in self.by_baler(baler_id, start, end) if b.status == BookingStatus.CONFIRMED]

    def by_field(self, field_id: str) -> list[Booking]:
        items = query_all(
            self.t, IndexName="field-index", KeyConditionExpression=Key("field_id").eq(field_id)
        )
        return [from_item(Booking, i) for i in items]

    def by_date(self, d: date) -> list[Booking]:
        items = query_all(
            self.t, IndexName="date-index", KeyConditionExpression=Key("date").eq(d.isoformat())
        )
        return [from_item(Booking, i) for i in items]

    def set_stop_order(self, booking_id: str, order: int) -> None:
        self.t.update_item(
            Key={"booking_id": booking_id},
            UpdateExpression="SET stop_order = :o",
            ExpressionAttributeValues={":o": order},
        )
