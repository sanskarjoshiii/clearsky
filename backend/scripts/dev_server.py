"""Run the whole backend locally for the dashboard: API + webhook Lambdas behind a tiny HTTP server.

  uv run python scripts/dev_server.py                 # mock DynamoDB (in memory) + seed + simulator + dev login
  uv run python scripts/dev_server.py --tables aws    # use the deployed tables named by TABLE_PREFIX instead

Requests are converted to API Gateway HTTP API (v2) events and passed to the same handlers that run
in Lambda, so local behaviour matches production. DEV_AUTH is forced on here (role picker login),
which is why this server only binds to 127.0.0.1.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import threading
import time
import uuid
from base64 import b64decode
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qsl, urlsplit


class _Ctx:
    function_name = "local"
    memory_limit_in_mb = 1024
    invoked_function_arn = "arn:aws:lambda:local:000000000000:function:local"
    aws_request_id = "local"

    @staticmethod
    def get_remaining_time_in_millis() -> int:
        return 30000


def to_event(method: str, raw_path: str, headers: dict[str, str], body: bytes) -> dict[str, Any]:
    parts = urlsplit(raw_path)
    now = time.time()
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": parts.path,
        "rawQueryString": parts.query,
        "headers": {k.lower(): v for k, v in headers.items()},
        "queryStringParameters": dict(parse_qsl(parts.query)) or None,
        "requestContext": {
            "accountId": "local",
            "apiId": "local",
            "domainName": "localhost",
            "domainPrefix": "local",
            "http": {
                "method": method,
                "path": parts.path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": headers.get("User-Agent", ""),
            },
            "requestId": uuid.uuid4().hex,
            "routeKey": "$default",
            "stage": "$default",
            "time": time.strftime("%d/%b/%Y:%H:%M:%S +0000", time.gmtime(now)),
            "timeEpoch": int(now * 1000),
        },
        "body": body.decode("utf-8", errors="replace") if body else None,
        "isBase64Encoded": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", type=int, default=8787)
    p.add_argument("--tables", choices=["mock", "aws"], default="mock")
    p.add_argument("--no-seed", action="store_true")
    args = p.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    os.environ["DEV_AUTH"] = "true"
    os.environ.setdefault("WA_MODE", "simulator")
    os.environ.setdefault("DEMO_MODE", "true")
    os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
    if os.environ["WA_MODE"] == "simulator":
        os.environ.setdefault("WA_APP_SECRET", "local-dev-secret")
        os.environ.setdefault("WA_VERIFY_TOKEN", "local-dev-verify")

    from clearsky.config import reset_settings

    reset_settings()
    if args.tables == "mock":
        from clearsky.local import start_local_dynamodb

        _server, summary = start_local_dynamodb(seed=not args.no_seed)
        print(f"[dev] mock DynamoDB ready; seed: {summary}")
    from clearsky import clock
    from clearsky.agent import llm
    from clearsky.config import get_settings
    from clearsky.domain import risk

    if args.tables == "mock" and not args.no_seed:
        from clearsky.seed.generate import REFERENCE_DATE

        clock.set_demo_today(REFERENCE_DATE)
        print(f"[dev] demo clock set to {REFERENCE_DATE}; risk: {risk.run_all()}")

    from clearsky.handlers import api, health, webhook

    s = get_settings()
    # A Lambda instance handles one event at a time, and the Powertools resolver keeps the current
    # event on the shared `app` object. Serialise the handlers so parallel browser requests can't
    # read each other's token or query string.
    one_at_a_time = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _dispatch(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            event = to_event(self.command, self.path, dict(self.headers.items()), body)
            path = event["rawPath"]
            with one_at_a_time:
                if path.startswith("/webhook/whatsapp"):
                    resp = webhook.handler(event, _Ctx())
                elif path == "/health":
                    resp = health.handler(event, _Ctx())
                else:
                    resp = api.handler(event, _Ctx())
            payload = resp.get("body") or ""
            data = b64decode(payload) if resp.get("isBase64Encoded") else payload.encode("utf-8")
            self.send_response(int(resp.get("statusCode", 200)))
            headers = resp.get("headers") or {}
            for k, v in headers.items():
                self.send_header(k, str(v))
            for k, vs in (resp.get("multiValueHeaders") or {}).items():
                for v in vs:
                    self.send_header(k, str(v))
            if not any(k.lower() == "content-type" for k in headers):
                self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = do_PUT = do_DELETE = do_OPTIONS = _dispatch

        def log_message(self, fmt: str, *a: Any) -> None:
            if "/api/sim/conversation" not in str(a[0] if a else ""):
                sys.stderr.write(f"[dev] {self.command} {self.path} → {a[1] if len(a) > 1 else ''}\n")

    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(
        f"[dev] clearsky API on http://127.0.0.1:{args.port}  (WA_MODE={s.wa_mode}, LLM={llm.describe()}, "
        f"today={clock.today()})"
    )
    print("[dev] dashboard: cd dashboard && npm run dev  →  http://localhost:5173")
    print(json.dumps({"dev_logins": "/api/dev/accounts"}))
    with contextlib.suppress(KeyboardInterrupt):
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
