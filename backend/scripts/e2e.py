"""End-to-end check of the deployed WhatsApp path (Phase 4 DoD).

Posts a correctly signed fake Meta webhook payload to the deployed API, then polls the deployed
tables until the farmer's field is BOOKED. Uses a synthetic test phone number by default, so in
WA_MODE=cloud the reply is recorded but not sent to anyone.

  uv run python scripts/e2e.py --api-url https://xxxx.execute-api.ap-south-1.amazonaws.com
Needs WA_APP_SECRET (env/.env or SSM) and AWS credentials for the stack (TABLE_PREFIX=clearsky-dev-).
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
import time
import uuid

import httpx

from clearsky.config import get_secret, get_settings
from clearsky.models import Farmer
from clearsky.repo import ConversationsRepo, FarmersRepo, FieldsRepo


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api-url", required=True)
    p.add_argument("--phone", default="+919999988888", help="synthetic test sender (never messaged)")
    p.add_argument("--text", default="Mera 8 acre dhaan 24 tareekh ko katega, Bhawanigarh. Naam Test Farmer.")
    p.add_argument("--timeout", type=int, default=90)
    args = p.parse_args()

    # Mark the test sender synthetic first so cloud mode never sends to this number.
    from clearsky import clock

    FarmersRepo().put(
        Farmer(phone=args.phone, name="E2E Test", village_id="V002", synthetic=True, created_at=clock.now())
    )
    msg_id = f"wamid.e2e-{uuid.uuid4().hex[:10]}"
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "e2e",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": args.phone.lstrip("+"),
                                    "id": msg_id,
                                    "timestamp": str(int(time.time())),
                                    "type": "text",
                                    "text": {"body": args.text},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }
    raw = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(get_secret("WA_APP_SECRET").encode(), raw, hashlib.sha256).hexdigest()
    resp = httpx.post(
        args.api_url.rstrip("/") + "/webhook/whatsapp",
        content=raw,
        headers={"content-type": "application/json", "x-hub-signature-256": sig},
        timeout=15,
    )
    print(f"webhook → {resp.status_code} {resp.text}")
    if resp.status_code != 200:
        return 1
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        fields = [f for f in FieldsRepo().by_farmer(args.phone) if f.status.value == "BOOKED"]
        if fields:
            reply = ConversationsRepo().last(args.phone, 1)
            print(f"✅ booked {fields[-1].field_id} (tables {get_settings().table_prefix}*)")
            print(f"   reply: {reply[0].text if reply else '(none)'}")
            return 0
        time.sleep(3)
    print("❌ no booking within the timeout; check the processor logs and the DLQ")
    return 1


if __name__ == "__main__":
    sys.exit(main())
