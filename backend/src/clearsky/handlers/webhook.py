"""GET/POST /webhook/whatsapp (API Gateway HTTP API, payload v2). IMPLEMENTATION.md §8, §12.

GET: Meta verification challenge. POST: verify X-Hub-Signature-256 → dedupe each message id
(ProcessedMessages) → enqueue to SQS → 200 fast. Without INBOUND_QUEUE_URL (local dev) messages are
processed inline. A valid signature always gets 200 so Meta stops retrying.
"""

from __future__ import annotations

import base64
import json
from typing import Any

import boto3

from clearsky.channels.whatsapp import Inbound, parse_inbound, verify_challenge, verify_signature
from clearsky.config import MissingSecretError, get_secret, get_settings
from clearsky.logging import get_logger, mask_phone
from clearsky.repo.processed import ProcessedMessagesRepo

log = get_logger(child="webhook")


def _resp(status: int, body: str = "", content_type: str = "text/plain") -> dict[str, Any]:
    return {"statusCode": status, "headers": {"content-type": content_type}, "body": body}


def _raw_body(event: dict[str, Any]) -> bytes:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        return base64.b64decode(body)
    return body.encode()


def _enqueue(msg: Inbound) -> None:
    s = get_settings()
    if s.inbound_queue_url:
        boto3.client("sqs", region_name=s.aws_region).send_message(
            QueueUrl=s.inbound_queue_url, MessageBody=msg.model_dump_json()
        )
        return
    from clearsky.handlers.processor import process_inbound  # local: no queue, process now

    process_inbound(msg)
    ProcessedMessagesRepo().mark(msg.msg_id, "done")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    method = (event.get("requestContext", {}).get("http", {}).get("method") or "GET").upper()
    if method == "GET":
        try:
            token = get_secret("WA_VERIFY_TOKEN")
        except MissingSecretError:
            return _resp(500, "verify token not configured")
        challenge = verify_challenge(event.get("queryStringParameters"), token)
        return _resp(200, challenge) if challenge is not None else _resp(403, "forbidden")

    raw = _raw_body(event)
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    try:
        secret = get_secret("WA_APP_SECRET")
    except MissingSecretError:
        log.error("WA_APP_SECRET not configured")
        return _resp(500, "app secret not configured")
    if not verify_signature(raw, headers.get("x-hub-signature-256"), secret):
        return _resp(401, "bad signature")

    try:
        payload = json.loads(raw or b"{}")
    except ValueError:
        return _resp(200, "ignored")
    messages, statuses = parse_inbound(payload)
    processed = ProcessedMessagesRepo()
    queued = 0
    for msg in messages:
        if not processed.claim(msg.msg_id):
            continue  # Meta retry of a message we already have
        try:
            _enqueue(msg)
            queued += 1
        except Exception:
            log.exception("enqueue failed", extra={"phone": mask_phone(msg.phone)})
    log.info("webhook", extra={"messages": len(messages), "queued": queued, "statuses": statuses})
    return _resp(200, json.dumps({"queued": queued}), "application/json")
