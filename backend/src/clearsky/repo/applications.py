from __future__ import annotations

from typing import Any

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from clearsky.models import Application, ApplicationStatus, from_item, to_item
from clearsky.models.dynamo import to_dynamo
from clearsky.repo.base import query_all, scan_all, table


class ApplicationsRepo:
    def __init__(self) -> None:
        self.t = table("Applications")

    def get(self, application_id: str) -> Application | None:
        item = self.t.get_item(Key={"application_id": application_id}).get("Item")
        return from_item(Application, item) if item else None

    def put(self, a: Application) -> None:
        self.t.put_item(Item=to_item(a))

    def by_sub(self, sub: str) -> list[Application]:
        """Every application of one user, oldest first (a rejected one may be followed by a new one)."""
        items = query_all(self.t, IndexName="sub-index", KeyConditionExpression=Key("sub").eq(sub))
        return sorted((from_item(Application, i) for i in items), key=lambda a: a.created_at)

    def by_status(self, status: ApplicationStatus) -> list[Application]:
        """Newest first."""
        items = query_all(
            self.t,
            IndexName="status-index",
            KeyConditionExpression=Key("status").eq(status.value),
            ScanIndexForward=False,
        )
        return [from_item(Application, i) for i in items]

    def list_all(self) -> list[Application]:
        """Newest first."""
        return sorted(
            (from_item(Application, i) for i in scan_all(self.t)), key=lambda a: a.created_at, reverse=True
        )

    def by_entity(self, entity_id: str) -> Application | None:
        return next((a for a in self.list_all() if a.entity_id == entity_id), None)

    def update_if(
        self, application_id: str, values: dict[str, Any], status: ApplicationStatus, extra: str = ""
    ) -> bool:
        """Set `values` only while the application is in `status` (plus an optional extra condition).

        Returns False when the condition fails, which is how concurrent reviews are kept to one winner.
        """
        names = {f"#{k}": k for k in values} | {"#status": "status"}
        try:
            self.t.update_item(
                Key={"application_id": application_id},
                UpdateExpression="SET " + ", ".join(f"#{k} = :{k}" for k in values),
                ConditionExpression="#status = :was" + (f" AND {extra}" if extra else ""),
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=to_dynamo({f":{k}": v for k, v in values.items()})
                | {":was": status.value},
            )
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise
        return True
