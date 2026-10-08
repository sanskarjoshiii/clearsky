"""Build the FIRMS fire-history layer for the district (Oct–Nov of each configured year).

Source, in order:  --csv-dir (archive CSVs downloaded from https://firms.modaps.eosdis.nasa.gov/download/)
                   → FIRMS area API with FIRMS_MAP_KEY (env or SSM).
Output: data/layers/firms_2022_2025.geojson. Then optionally:
  --apply-seed   write fire_points / fire_history_score into data/seed/villages.json
  --apply-db     write them into the Villages table (TABLE_PREFIX)
  --upload       upload the layer to DATA_BUCKET/layers/ (deployed stack only)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

from clearsky.config import REPO_ROOT, MissingSecretError, get_secret, get_settings
from clearsky.domain.firms import (
    FirePoint,
    api_requests,
    dedupe,
    in_season,
    parse_csv,
    to_geojson,
    village_scores,
)
from clearsky.models import Village
from clearsky.seed.generate import SEED_DIR

LAYER = REPO_ROOT / "data" / "layers" / "firms_2022_2025.geojson"
RAW_DIR = REPO_ROOT / "data" / "raw" / "firms"


def from_csv_dir(path: Path) -> list[FirePoint]:
    points: list[FirePoint] = []
    for f in sorted(path.glob("*.csv")):
        points += parse_csv(f.read_text(encoding="utf-8"), source=f.stem)
        print(f"  read {f.name}")
    return points


def from_api(key: str) -> list[FirePoint]:
    s = get_settings()
    urls = api_requests(key, s.firms_source, s.district_bbox, s.firms_years, s.firms_day_range)
    points: list[FirePoint] = []
    with httpx.Client(timeout=60) as client:
        for i, url in enumerate(urls, 1):
            resp = client.get(url)
            if resp.status_code != 200 or resp.text.lstrip().lower().startswith(("invalid", "error")):
                raise RuntimeError(f"FIRMS API error {resp.status_code}: {resp.text[:200]}")
            points += parse_csv(resp.text, source=s.firms_source)
            print(f"  [{i}/{len(urls)}] {len(points)} points so far")
            time.sleep(0.5)  # be gentle with the shared API
    return points


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--csv-dir", type=Path, default=None, help=f"folder of FIRMS CSVs (default {RAW_DIR} if present)"
    )
    p.add_argument("--apply-seed", action="store_true")
    p.add_argument("--apply-db", action="store_true")
    p.add_argument("--upload", action="store_true")
    args = p.parse_args()
    s = get_settings()

    csv_dir = args.csv_dir or (RAW_DIR if RAW_DIR.exists() and any(RAW_DIR.glob("*.csv")) else None)
    if csv_dir:
        print(f"reading CSVs from {csv_dir}")
        raw = from_csv_dir(csv_dir)
    else:
        try:
            key = get_secret("FIRMS_MAP_KEY")
        except MissingSecretError:
            print(f"❌ no FIRMS data: set FIRMS_MAP_KEY or put archive CSVs in {RAW_DIR}")
            return 1
        print("fetching from the FIRMS area API")
        raw = from_api(key)

    points = dedupe(in_season(raw, s.district_bbox, s.firms_years))
    LAYER.parent.mkdir(parents=True, exist_ok=True)
    LAYER.write_text(json.dumps(to_geojson(points)), encoding="utf-8")
    print(f"✅ {len(points)} in-season points in bbox → {LAYER}")

    villages_path = SEED_DIR / "villages.json"
    villages = [Village.model_validate(v) for v in json.loads(villages_path.read_text(encoding="utf-8"))]
    scores = village_scores(points, villages, s.village_radius_km)
    top = sorted(scores.items(), key=lambda kv: kv[1][0], reverse=True)[:5]
    print("top villages by fire points:", ", ".join(f"{vid}={n}" for vid, (n, _) in top))

    if args.apply_seed:
        rows = json.loads(villages_path.read_text(encoding="utf-8"))
        for r in rows:
            n, score = scores[r["village_id"]]
            r["fire_points"], r["fire_history_score"] = n, score
        villages_path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"✅ scores written to {villages_path}")
    if args.apply_db:
        from clearsky.repo import VillagesRepo

        repo = VillagesRepo()
        for vid, (n, score) in scores.items():
            repo.update_fields(vid, {"fire_points": n, "fire_history_score": score})
        print(f"✅ scores written to {s.table_prefix}Villages")
    if args.upload:
        import boto3

        if not s.data_bucket:
            print("❌ DATA_BUCKET not set (take DataBucketName from the stack outputs)")
            return 1
        boto3.client("s3", region_name=s.aws_region).upload_file(
            str(LAYER), s.data_bucket, f"layers/{LAYER.name}"
        )
        print(f"✅ uploaded to s3://{s.data_bucket}/layers/{LAYER.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
