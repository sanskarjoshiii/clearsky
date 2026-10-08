"""Call the API Lambda with API Gateway v2 events (dev-auth tokens), like the dev server does."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any
from urllib.parse import urlencode


class Ctx:
    function_name = "test"
    memory_limit_in_mb = 512
    invoked_function_arn = "arn:aws:lambda:local:0:function:test"
    aws_request_id = "test"


def event(
    method: str,
    path: str,
    body: Any = None,
    token: str | None = None,
    query: dict[str, str] | None = None,
    claims: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    raw_body: str | None = None,
) -> dict[str, Any]:
    hdrs = {"content-type": "application/json", **(headers or {})}
    if token:
        hdrs["authorization"] = f"Bearer {token}"
    ctx: dict[str, Any] = {
        "http": {
            "method": method,
            "path": path,
            "sourceIp": "127.0.0.1",
            "userAgent": "pytest",
            "protocol": "HTTP/1.1",
        },
        "requestId": uuid.uuid4().hex,
        "routeKey": "$default",
        "stage": "$default",
        "accountId": "0",
        "apiId": "t",
        "domainName": "localhost",
        "time": "",
        "timeEpoch": int(time.time() * 1000),
    }
    if claims is not None:
        ctx["authorizer"] = {"jwt": {"claims": claims, "scopes": None}}
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": path,
        "rawQueryString": urlencode(query or {}),
        "headers": hdrs,
        "queryStringParameters": query,
        "requestContext": ctx,
        "body": raw_body if raw_body is not None else (json.dumps(body) if body is not None else None),
        "isBase64Encoded": False,
    }


def call(
    method: str,
    path: str,
    body: Any = None,
    token: str | None = None,
    query: dict[str, str] | None = None,
    claims: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    from clearsky.handlers import api

    resp = api.handler(event(method, path, body, token, query, claims), Ctx())
    payload = resp.get("body")
    return int(resp["statusCode"]), json.loads(payload) if payload else None


OFFICER = "dev.officer.Sangrur"
OFFICER_ALL = "dev.officer.officer"
BUYER = "dev.buyer.BY01"


def operator(baler_id: str) -> str:
    return f"dev.operator.{baler_id}"
