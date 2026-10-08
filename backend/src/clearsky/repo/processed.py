"""ProcessedMessages: idempotency markers for inbound WhatsApp message ids (TTL 2 days)."""

from __future__ import annotations

import time

from botocore.exceptions import ClientError

from clearsky.repo.base import table

TTL_SECONDS = 2 * 24 * 3600


class ProcessedMessagesRepo:
    def __init__(self) -> None:
        self.t = table("ProcessedMessages")

    def claim(self, wa_message_id: str) -> bool:
        """True if this id is new (and now marked `processing`); False if it was seen before."""
        try:
            self.t.put_item(
                Item={
                    "wa_message_id": wa_message_id,
                    "status": "processing",
                    "ttl": int(time.time()) + TTL_SECONDS,
                },
                ConditionExpression="attribute_not_exists(wa_message_id)",
            )
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise

    def mark(self, wa_message_id: str, status: str) -> None:
        self.t.update_item(
            Key={"wa_message_id": wa_message_id},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": status},
        )

    def status(self, wa_message_id: str) -> str | None:
        item = self.t.get_item(Key={"wa_message_id": wa_message_id}).get("Item")
        return str(item["status"]) if item else None
