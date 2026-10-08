"""Offline development: an in-process mock DynamoDB (moto server), with tables created and seeded.

Used by `scripts/chat_cli.py --local` and `scripts/book_all.py --local`. Needs the dev dependency
`moto[server]`. Only DynamoDB is redirected; Bedrock calls still go to real AWS.
"""

from __future__ import annotations

import os
import socket
from typing import Any

from clearsky import clock
from clearsky.config import reset_settings
from clearsky.domain import villages
from clearsky.repo.base import ddb_client, reset_clients
from clearsky.repo.schema import create_all_tables


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def start_local_dynamodb(seed: bool = True) -> tuple[Any, dict[str, Any]]:
    """Start moto, point the app at it, create tables, load the seed. Returns (server, seed summary)."""
    import logging

    from moto.server import ThreadedMotoServer

    logging.getLogger("werkzeug").setLevel(logging.ERROR)  # hide per-request access logs
    port = _free_port()
    server = ThreadedMotoServer(ip_address="127.0.0.1", port=port, verbose=False)
    server.start()
    os.environ["DDB_ENDPOINT_URL"] = f"http://127.0.0.1:{port}"
    os.environ.setdefault("TABLE_PREFIX", "clearsky-local-")
    reset_settings()
    reset_clients()
    villages.clear_cache()
    clock.clear_cache()
    from clearsky.config import get_settings

    create_all_tables(ddb_client(), get_settings().table_prefix)
    summary: dict[str, Any] = {}
    if seed:
        from clearsky.seed.generate import SEED_DIR, generate, read
        from clearsky.seed.load import load

        data = read() if (SEED_DIR / "villages.json").exists() else generate()
        summary = load(data, reset=False, prebook=True)
    return server, summary
