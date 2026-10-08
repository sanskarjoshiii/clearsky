from __future__ import annotations

from clearsky.models import Buyer, from_item, to_item
from clearsky.repo.base import batch_put, scan_all, table


class BuyersRepo:
    def __init__(self) -> None:
        self.t = table("Buyers")

    def get(self, buyer_id: str) -> Buyer | None:
        item = self.t.get_item(Key={"buyer_id": buyer_id}).get("Item")
        return from_item(Buyer, item) if item else None

    def put(self, b: Buyer) -> None:
        self.t.put_item(Item=to_item(b))

    def put_many(self, buyers: list[Buyer]) -> None:
        batch_put(self.t, [to_item(b) for b in buyers])

    def list_all(self) -> list[Buyer]:
        return [from_item(Buyer, i) for i in scan_all(self.t)]
