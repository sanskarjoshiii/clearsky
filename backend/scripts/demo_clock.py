"""Get or set the demo clock (DEMO_MODE) on the tables named by TABLE_PREFIX.

uv run python scripts/demo_clock.py get
uv run python scripts/demo_clock.py set 2026-10-24
uv run python scripts/demo_clock.py clear
"""

from __future__ import annotations

import argparse
import sys

from clearsky.domain import demo


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("action", choices=["get", "set", "clear"])
    p.add_argument("date", nargs="?")
    args = p.parse_args()
    if args.action == "get":
        print(demo.get_clock())
    elif args.action == "set":
        if not args.date:
            p.error("set needs a date YYYY-MM-DD")
        print(demo.set_clock(args.date))
    else:
        print(demo.set_clock(None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
