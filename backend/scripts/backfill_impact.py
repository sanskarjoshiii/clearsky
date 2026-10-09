"""Write the pollution-avoided snapshot onto DONE bookings that don't have one (issue #5).

  uv run python scripts/backfill_impact.py --dry-run     # show what would change
  uv run python scripts/backfill_impact.py               # fill DONE bookings without a snapshot
  uv run python scripts/backfill_impact.py --recompute   # ALSO overwrite snapshots made with other factors
  uv run python scripts/backfill_impact.py --local       # try it on an in-process mock DynamoDB with the seed

A booking is snapshotted automatically when the baler marks it Done. This script is for bookings that
were done before emission factors were configured, and for a deliberate recompute after the team
changes a factor (history never changes silently). It needs EMISSION_FACTORS to be set, each with a
source; see clearsky/domain/impact.py. Without --local it uses the tables named by TABLE_PREFIX.
"""

from __future__ import annotations

import argparse
import sys

from clearsky.domain import impact
from clearsky.models import BookingStatus
from clearsky.models.dynamo import to_dynamo
from clearsky.repo import BookingsRepo


def backfill(*, recompute: bool = False, dry_run: bool = False) -> dict[str, int]:
    """Returns counts: done bookings seen, snapshots written, already current, left alone (other factors)."""
    version = impact.version()
    if version is None:
        raise SystemExit("EMISSION_FACTORS is not set (or has no factor with a source): nothing to compute.")
    repo = BookingsRepo()
    counts = {"done": 0, "written": 0, "current": 0, "kept": 0}
    for bk in repo.list_all():
        if bk.status != BookingStatus.DONE:
            continue
        counts["done"] += 1
        if bk.impact_factors_version == version:
            counts["current"] += 1
            continue
        if bk.impact is not None and not recompute:
            counts["kept"] += 1  # snapshotted with earlier factors: only --recompute may change history
            continue
        snap = impact.snapshot(bk.est_tonnes)
        counts["written"] += 1
        if dry_run:
            continue
        repo.t.update_item(
            Key={"booking_id": bk.booking_id},
            UpdateExpression="SET impact = :i, impact_tonnes = :t, impact_factors_version = :v",
            ConditionExpression="#s = :done",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues=to_dynamo(
                {
                    ":i": snap["impact"],
                    ":t": snap["impact_tonnes"],
                    ":v": snap["impact_factors_version"],
                    ":done": BookingStatus.DONE.value,
                }
            ),
        )
    return counts


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--recompute", action="store_true", help="overwrite snapshots made with different factors")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--local", action="store_true")
    args = p.parse_args()
    if args.local:
        from clearsky.local import start_local_dynamodb

        _server, summary = start_local_dynamodb()
        print(f"local mock DynamoDB seeded: {summary}")
    counts = backfill(recompute=args.recompute, dry_run=args.dry_run)
    verb = "would write" if args.dry_run else "wrote"
    print(
        f"{counts['done']} done bookings: {verb} {counts['written']}, "
        f"{counts['current']} already current, {counts['kept']} kept (other factors; use --recompute)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
