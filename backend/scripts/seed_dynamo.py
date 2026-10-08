"""Load data/seed/*.json into the DynamoDB tables named by TABLE_PREFIX (deployed stack or DDB_ENDPOINT_URL).

Usage:  uv run python scripts/seed_dynamo.py --reset [--set-clock]
Writes to whatever tables TABLE_PREFIX points at. `--reset` deletes every item first.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from clearsky import clock
from clearsky.config import get_settings
from clearsky.repo.base import ddb_client
from clearsky.repo.schema import TABLES
from clearsky.seed.generate import SEED_DIR, read
from clearsky.seed.load import load


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reset", action="store_true", help="delete all items before loading")
    p.add_argument("--no-prebook", action="store_true", help="skip pre-booking fields through the matcher")
    p.add_argument("--set-clock", action="store_true", help="set the demo clock to the seed reference date")
    args = p.parse_args()

    s = get_settings()
    existing = set(ddb_client().list_tables().get("TableNames", []))
    missing = [s.table_prefix + t.name for t in TABLES if s.table_prefix + t.name not in existing]
    if missing:
        print(
            f"❌ tables not found (deploy the stack or check TABLE_PREFIX={s.table_prefix!r}): {missing[:3]}…"
        )
        return 1
    if not (SEED_DIR / "villages.json").exists():
        print("❌ no seed files; run scripts/gen_seed.py first")
        return 1

    data = read()
    target = s.ddb_endpoint_url or f"AWS {s.aws_region}"
    print(f"loading seed into {s.table_prefix}* on {target} (reset={args.reset})")
    summary = load(data, reset=args.reset, prebook=not args.no_prebook)
    if args.set_clock:
        clock.set_demo_today(date.fromisoformat(data["meta"]["reference_date"]))
        summary["demo_clock"] = data["meta"]["reference_date"]
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
