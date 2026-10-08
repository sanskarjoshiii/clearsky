"""Try to book every unbooked field and print a summary table (booked / no slot / reason).

  --dry-run   plan only: show the best baler-day and buyer per field without writing anything
  --local     run against an in-process mock DynamoDB loaded with the seed (no AWS needed)
Without --local it uses the tables named by TABLE_PREFIX (deployed stack or DDB_ENDPOINT_URL).
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import date

from clearsky import clock
from clearsky.domain import matching
from clearsky.domain.pricing import estimate_tonnes
from clearsky.models.enums import BOOKABLE_STATUSES
from clearsky.repo import BuyersRepo, FieldsRepo


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--local", action="store_true")
    p.add_argument("--today", type=date.fromisoformat, default=None, help="simulated today (YYYY-MM-DD)")
    args = p.parse_args()

    server = None
    if args.local:
        from clearsky.local import start_local_dynamodb

        server, summary = start_local_dynamodb()
        print(f"local mock DynamoDB seeded: {summary}")
        args.today = args.today or date(2026, 10, 20)
    today = args.today or clock.today()
    print(f"today = {today}  ({'dry run' if args.dry_run else 'booking'})\n")

    fields = sorted(
        (f for f in FieldsRepo().list_all() if f.status in BOOKABLE_STATUSES), key=lambda f: f.field_id
    )
    buyers = BuyersRepo().list_all()
    outcomes: Counter[str] = Counter()
    print(
        f"{'field':<14}{'acres':>6}  {'harvest':<11}{'deadline':<11}{'result':<20}{'baler':<6}{'date':<11}buyer"
    )
    for f in fields:
        if args.dry_run:
            cands = matching._load_candidates(f, today)
            if cands:
                c = cands[0]
                chosen = matching.choose_buyer(f, estimate_tonnes(f.acres), buyers)
                result, baler, day, buyer = (
                    "would book",
                    c.baler.baler_id,
                    c.day.isoformat(),
                    chosen[0].name if chosen else "-",
                )
            else:
                start, end = matching.booking_window(f, today)
                reason = "deadline_too_close" if start > end else "no_baler_capacity"
                result, baler, day, buyer = f"no slot: {reason}", "", "", ""
        else:
            r = matching.book_pickup(f.field_id, today)
            if isinstance(r, matching.Booked):
                result, baler, day, buyer = "booked", r.baler_id, r.date.isoformat(), r.buyer_name or "-"
            else:
                result, baler, day, buyer = f"no slot: {r.reason}", "", "", ""
        outcomes[result.split(":")[0]] += 1
        print(
            f"{f.field_id:<14}{f.acres:>6.1f}  {f.harvest_date!s:<11}{f.sowing_deadline!s:<11}{result:<20}"
            f"{baler:<6}{day:<11}{buyer}"
        )
    print("\nsummary:", dict(outcomes))
    if server is not None:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
