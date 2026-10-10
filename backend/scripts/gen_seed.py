"""Generate deterministic demo seed JSON into data/seed/.  Usage: uv run python scripts/gen_seed.py --seed 42"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from clearsky.seed.generate import DEFAULT_SEED, SEED_DIR, generate, write


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--fields", type=int, default=60, help="number of synthetic fields (50-80)")
    p.add_argument("--out", type=Path, default=SEED_DIR)
    args = p.parse_args()
    # Keep FIRMS fire history (written by fetch_firms.py --apply-seed); otherwise `make seed` would erase it.
    fire = None
    existing = args.out / "villages.json"
    if existing.exists():
        fire = {
            v["village_id"]: {k: v[k] for k in ("fire_points", "fire_history_score") if k in v}
            for v in json.loads(existing.read_text(encoding="utf-8"))
        }
    data = generate(args.seed, args.fields, fire=fire)
    for path in write(data, args.out):
        print(f"wrote {path}")
    m = data["meta"]
    print(
        f"{len(data['villages'])} villages, {len(data['balers'])} balers, {len(data['buyers'])} buyers, "
        f"{len(data['fields'])} fields ({len(m['prebook_field_ids'])} to pre-book, "
        f"{len(m['red_candidate_field_ids'])} RED candidates)"
    )


if __name__ == "__main__":
    main()
