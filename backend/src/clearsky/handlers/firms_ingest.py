"""Recompute village fire-history scores from the FIRMS layer in S3.

The layer itself is produced by `scripts/fetch_firms.py` (API or CSV fallback) and uploaded to
`DataBucket/layers/firms_2022_2025.geojson`. This Lambda can be invoked manually after an upload.
"""

from __future__ import annotations

import json
from typing import Any

import boto3

from clearsky.config import get_settings
from clearsky.domain.firms import from_geojson, village_scores
from clearsky.logging import get_logger
from clearsky.repo import VillagesRepo

LAYER_KEY = "layers/firms_2022_2025.geojson"
log = get_logger()


def apply_scores(doc: dict[str, Any]) -> dict[str, Any]:
    s = get_settings()
    points = from_geojson(doc)
    repo = VillagesRepo()
    villages = repo.by_district(s.district)
    scores = village_scores(points, villages, s.village_radius_km)
    for vid, (count, score) in scores.items():
        repo.update_fields(vid, {"fire_points": count, "fire_history_score": score})
    return {"points": len(points), "villages_scored": len(scores)}


@log.inject_lambda_context
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    s = get_settings()
    if not s.data_bucket:
        raise RuntimeError("DATA_BUCKET is not configured")
    key = event.get("key", LAYER_KEY) if isinstance(event, dict) else LAYER_KEY
    obj = boto3.client("s3", region_name=s.aws_region).get_object(Bucket=s.data_bucket, Key=key)
    result = apply_scores(json.loads(obj["Body"].read()))
    log.info("firms scores applied", extra=result)
    return result
