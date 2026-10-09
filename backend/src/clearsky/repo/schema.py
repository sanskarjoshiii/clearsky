"""Table definitions (IMPLEMENTATION.md §3.1).

This is the single Python description of the tables. `infra/template.yaml` must match it;
`tests/test_template_schema.py` enforces that. Tests and `chat_cli --local` create tables from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Index:
    name: str
    hash_key: str
    range_key: str | None = None


@dataclass(frozen=True)
class TableDef:
    name: str
    hash_key: str
    range_key: str | None = None
    gsis: tuple[Index, ...] = ()
    ttl_attribute: str | None = None
    # attribute name → DynamoDB type for every key attribute (S or N)
    attr_types: dict[str, str] = field(default_factory=dict)

    def key_attributes(self) -> set[str]:
        names = {self.hash_key} | ({self.range_key} if self.range_key else set())
        for g in self.gsis:
            names.add(g.hash_key)
            if g.range_key:
                names.add(g.range_key)
        return names


TABLES: tuple[TableDef, ...] = (
    TableDef("Villages", "village_id", gsis=(Index("district-index", "district"),)),
    TableDef("Farmers", "phone", gsis=(Index("village-index", "village_id"),)),
    TableDef(
        "Fields",
        "field_id",
        gsis=(
            Index("village-index", "village_id", "harvest_date"),
            Index("farmer-index", "phone"),
            Index("status-index", "status", "risk_score"),
        ),
        attr_types={"risk_score": "N"},
    ),
    TableDef("Balers", "baler_id"),
    TableDef("BalerDays", "baler_id", "date"),
    TableDef("Buyers", "buyer_id"),
    TableDef(
        "Bookings",
        "booking_id",
        gsis=(
            Index("baler-date-index", "baler_id", "date"),
            Index("field-index", "field_id"),
            Index("buyer-index", "buyer_id", "date"),
            Index("date-index", "date"),
        ),
    ),
    TableDef("Conversations", "phone", "ts", ttl_attribute="ttl"),
    TableDef("ProcessedMessages", "wa_message_id", ttl_attribute="ttl"),
    TableDef("Alerts", "alert_id", gsis=(Index("village-index", "village_id"),)),
    TableDef(
        "Applications",
        "application_id",
        gsis=(Index("sub-index", "sub"), Index("status-index", "status", "created_at")),
    ),
    TableDef("Settings", "key"),
)

TABLES_BY_NAME = {t.name: t for t in TABLES}


def create_table_kwargs(t: TableDef, prefix: str) -> dict[str, Any]:
    """boto3 `create_table` arguments (on-demand billing)."""
    key_schema = [{"AttributeName": t.hash_key, "KeyType": "HASH"}]
    if t.range_key:
        key_schema.append({"AttributeName": t.range_key, "KeyType": "RANGE"})
    kwargs: dict[str, Any] = {
        "TableName": prefix + t.name,
        "KeySchema": key_schema,
        "AttributeDefinitions": [
            {"AttributeName": a, "AttributeType": t.attr_types.get(a, "S")}
            for a in sorted(t.key_attributes())
        ],
        "BillingMode": "PAY_PER_REQUEST",
    }
    if t.gsis:
        kwargs["GlobalSecondaryIndexes"] = [
            {
                "IndexName": g.name,
                "KeySchema": [{"AttributeName": g.hash_key, "KeyType": "HASH"}]
                + ([{"AttributeName": g.range_key, "KeyType": "RANGE"}] if g.range_key else []),
                "Projection": {"ProjectionType": "ALL"},
            }
            for g in t.gsis
        ]
    return kwargs


def create_all_tables(client: Any, prefix: str) -> list[str]:
    """Create every table that doesn't exist yet. Returns the names created."""
    existing = set(client.list_tables().get("TableNames", []))
    created = []
    for t in TABLES:
        kwargs = create_table_kwargs(t, prefix)
        if kwargs["TableName"] in existing:
            continue
        client.create_table(**kwargs)
        if t.ttl_attribute:
            client.update_time_to_live(
                TableName=kwargs["TableName"],
                TimeToLiveSpecification={"Enabled": True, "AttributeName": t.ttl_attribute},
            )
        created.append(kwargs["TableName"])
    return created
