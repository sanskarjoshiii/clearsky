from __future__ import annotations

import time

from boto3.dynamodb.conditions import Key

from clearsky.models import ConversationTurn, from_item, to_item
from clearsky.repo.base import query_all, table

TTL_SECONDS = 7 * 24 * 3600


class ConversationsRepo:
    def __init__(self) -> None:
        self.t = table("Conversations")

    def add(self, turn: ConversationTurn) -> None:
        if turn.ttl is None:
            turn = turn.model_copy(update={"ttl": int(time.time()) + TTL_SECONDS})
        self.t.put_item(Item=to_item(turn))

    def last(self, phone: str, n: int) -> list[ConversationTurn]:
        """The last `n` turns in chronological order."""
        resp = self.t.query(
            KeyConditionExpression=Key("phone").eq(phone),
            ScanIndexForward=False,
            Limit=n,
        )
        turns = [from_item(ConversationTurn, i) for i in resp.get("Items", [])]
        return list(reversed(turns))

    def since(self, phone: str, ts_from: str) -> list[ConversationTurn]:
        """Turns with ts ≥ ts_from (ISO strings sort chronologically), oldest first."""
        items = query_all(self.t, KeyConditionExpression=Key("phone").eq(phone) & Key("ts").gte(ts_from))
        return [from_item(ConversationTurn, i) for i in items]

    def last_user_ts(self, phone: str, scan: int = 50) -> str | None:
        for turn in reversed(self.last(phone, scan)):
            if turn.role == "user":
                return turn.ts
        return None

    def delete_phone(self, phone: str) -> int:
        n = 0
        for turn in self.last(phone, 1000):
            self.t.delete_item(Key={"phone": phone, "ts": turn.ts})
            n += 1
        return n
