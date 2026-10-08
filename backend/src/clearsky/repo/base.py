"""boto3 handles and shared helpers for repositories."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from typing import Any

import boto3
from boto3.dynamodb.conditions import ConditionBase

from clearsky.config import get_settings


@lru_cache(maxsize=1)
def ddb_resource() -> Any:
    s = get_settings()
    return boto3.resource("dynamodb", region_name=s.aws_region, endpoint_url=s.ddb_endpoint_url)


@lru_cache(maxsize=1)
def ddb_client() -> Any:
    s = get_settings()
    return boto3.client("dynamodb", region_name=s.aws_region, endpoint_url=s.ddb_endpoint_url)


def reset_clients() -> None:
    ddb_resource.cache_clear()
    ddb_client.cache_clear()


def table_name(name: str) -> str:
    return get_settings().table_prefix + name


def table(name: str) -> Any:
    return ddb_resource().Table(table_name(name))


def query_all(tbl: Any, **kwargs: Any) -> Iterator[dict[str, Any]]:
    """Paginate a Table.query."""
    while True:
        resp = tbl.query(**kwargs)
        yield from resp.get("Items", [])
        lek = resp.get("LastEvaluatedKey")
        if not lek:
            return
        kwargs["ExclusiveStartKey"] = lek


def scan_all(tbl: Any, filter_expression: ConditionBase | None = None) -> Iterator[dict[str, Any]]:
    kwargs: dict[str, Any] = {}
    if filter_expression is not None:
        kwargs["FilterExpression"] = filter_expression
    while True:
        resp = tbl.scan(**kwargs)
        yield from resp.get("Items", [])
        lek = resp.get("LastEvaluatedKey")
        if not lek:
            return
        kwargs["ExclusiveStartKey"] = lek


def batch_put(tbl: Any, items: list[dict[str, Any]]) -> None:
    with tbl.batch_writer() as w:
        for it in items:
            w.put_item(Item=it)


def delete_all(tbl: Any, key_names: list[str]) -> int:
    n = 0
    with tbl.batch_writer() as w:
        for it in scan_all(tbl):
            w.delete_item(Key={k: it[k] for k in key_names})
            n += 1
    return n
