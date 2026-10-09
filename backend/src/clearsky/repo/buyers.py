from __future__ import annotations

from botocore.exceptions import ClientError

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

    def put_new(self, b: Buyer) -> bool:
        """Create a buyer only if the id is free. False = the id was taken meanwhile."""
        try:
            self.t.put_item(Item=to_item(b), ConditionExpression="attribute_not_exists(buyer_id)")
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise
        return True

    def put_many(self, buyers: list[Buyer]) -> None:
        batch_put(self.t, [to_item(b) for b in buyers])

    def list_all(self) -> list[Buyer]:
        return [from_item(Buyer, i) for i in scan_all(self.t)]
