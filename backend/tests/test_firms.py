"""Phase 1: FIRMS parsing, filtering, GeoJSON and village fire-history scores. Fixture points are synthetic."""

from __future__ import annotations

import json
from datetime import date

import boto3
import pytest

from clearsky.config import reset_settings
from clearsky.domain.firms import (
    api_requests,
    dedupe,
    from_geojson,
    in_season,
    parse_csv,
    to_geojson,
    village_scores,
)
from clearsky.domain.geo import offset_point
from clearsky.handlers import firms_ingest
from clearsky.models import Village
from clearsky.repo import VillagesRepo
from tests import factories as fx

BBOX = (75.55, 29.75, 76.40, 30.50)


def _csv(rows: list[tuple[float, float, str, str]]) -> str:
    head = "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,frp,daynight"
    lines = [f"{lat},{lng},330.1,0.4,0.4,{d},{t},N,VIIRS,n,2,4.5,D" for lat, lng, d, t in rows]
    return "\n".join([head, *lines]) + "\n"


def _villages() -> list[Village]:
    a = Village(village_id="A", name="A", district="Sangrur", lat=30.20, lng=76.00)
    b = Village(village_id="B", name="B", district="Sangrur", lat=30.10, lng=75.80)
    c = Village(village_id="C", name="C", district="Sangrur", lat=29.90, lng=76.20)
    return [a, b, c]


def test_parse_filter_dedupe() -> None:
    near_a = offset_point(30.20, 76.00, 1, 1)
    text = (
        _csv(
            [
                (*near_a, "2024-10-25", "830"),
                (*near_a, "2024-10-25", "830"),  # duplicate
                (30.20, 76.00, "2024-09-25", "830"),  # outside season
                (31.50, 76.00, "2024-10-25", "830"),  # outside bbox
                (30.20, 76.00, "2021-10-25", "830"),  # outside years
            ]
        )
        + "bad,row,,,,,,\n"
    )
    points = parse_csv(text)
    assert len(points) == 5
    assert points[0].acq_time == "0830" and points[0].frp == 4.5
    kept = dedupe(in_season(points, BBOX, [2022, 2023, 2024, 2025]))
    assert len(kept) == 1


def test_geojson_round_trip() -> None:
    pts = parse_csv(_csv([(30.2, 76.0, "2024-10-25", "0830")]))
    doc = to_geojson(pts)
    assert doc["features"][0]["geometry"]["coordinates"] == [76.0, 30.2]
    back = from_geojson(json.loads(json.dumps(doc)))
    assert back[0].acq_date == date(2024, 10, 25)


def test_village_scores_min_max() -> None:
    a_pt = offset_point(30.20, 76.00, 1, 0)
    b_pt = offset_point(30.10, 75.80, 0, 2)
    pts = parse_csv(
        _csv([(*a_pt, "2024-10-25", "0830")] * 1 + [(*b_pt, f"2024-10-{d}", "0830") for d in range(10, 14)])
    )
    scores = village_scores(pts, _villages(), radius_km=3)
    assert scores["B"] == (4, 1.0)
    assert scores["A"] == (1, 0.25)
    assert scores["C"] == (0, 0.0)
    assert village_scores([], _villages(), 3)["A"] == (0, 0.0)


def test_api_requests_cover_season_in_chunks() -> None:
    urls = api_requests("KEY", "VIIRS_SNPP_SP", BBOX, [2024], day_range=5)
    assert len(urls) == 13  # 61 days / 5
    assert urls[0].endswith("/5/2024-10-01") and urls[-1].endswith("/1/2024-11-30")
    assert "75.55,29.75,76.4,30.5" in urls[0]


def test_firms_ingest_handler_updates_villages(ddb: None, monkeypatch: pytest.MonkeyPatch) -> None:
    fx.village("A", "A", lat=30.20, lng=76.00)
    fx.village("B", "B", lat=30.10, lng=75.80)
    pts = parse_csv(_csv([(*offset_point(30.20, 76.00, 1, 0), "2024-10-25", "0830")]))
    s3 = boto3.client("s3", region_name="ap-south-1")
    s3.create_bucket(Bucket="data-bucket", CreateBucketConfiguration={"LocationConstraint": "ap-south-1"})
    s3.put_object(Bucket="data-bucket", Key=firms_ingest.LAYER_KEY, Body=json.dumps(to_geojson(pts)))
    monkeypatch.setenv("DATA_BUCKET", "data-bucket")
    reset_settings()

    class Ctx:
        function_name, memory_limit_in_mb, invoked_function_arn, aws_request_id = "f", 128, "arn", "id"

    result = firms_ingest.handler({}, Ctx())
    assert result == {"points": 1, "villages_scored": 2}
    assert VillagesRepo().get("A").fire_history_score == 1.0  # type: ignore[union-attr]
    assert VillagesRepo().get("B").fire_points == 0  # type: ignore[union-attr]
