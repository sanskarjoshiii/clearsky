"""NASA FIRMS fire points → GeoJSON layer → per-village fire-history score (IMPLEMENTATION.md §2.8)."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel

from clearsky.domain.geo import bbox_contains, haversine_km
from clearsky.models import Village

FIRMS_AREA_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{area}/{days}/{start}"
SEASON_MONTHS = (10, 11)  # Oct–Nov paddy-residue season


class FirePoint(BaseModel):
    lat: float
    lng: float
    acq_date: date
    acq_time: str = ""  # HHMM, UTC
    confidence: str = ""
    frp: float | None = None
    source: str = ""


def parse_csv(text: str, source: str = "") -> list[FirePoint]:
    """Parse a FIRMS CSV (API or archive download). Rows missing coordinates or dates are skipped."""
    out: list[FirePoint] = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            frp_raw = row.get("frp")
            out.append(
                FirePoint(
                    lat=float(row["latitude"]),
                    lng=float(row["longitude"]),
                    acq_date=date.fromisoformat(row["acq_date"]),
                    acq_time=str(row.get("acq_time", "")).zfill(4),
                    confidence=str(row.get("confidence", "")),
                    frp=float(frp_raw) if frp_raw not in (None, "") else None,
                    source=source or str(row.get("instrument", "")),
                )
            )
        except (KeyError, ValueError):
            continue
    return out


def in_season(
    points: Iterable[FirePoint], bbox: tuple[float, float, float, float], years: Iterable[int]
) -> list[FirePoint]:
    ys = set(years)
    return [
        p
        for p in points
        if p.acq_date.year in ys and p.acq_date.month in SEASON_MONTHS and bbox_contains(bbox, p.lat, p.lng)
    ]


def dedupe(points: Iterable[FirePoint]) -> list[FirePoint]:
    seen: set[tuple[float, float, date, str]] = set()
    out = []
    for p in points:
        k = (round(p.lat, 4), round(p.lng, 4), p.acq_date, p.acq_time)
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def to_geojson(points: Iterable[FirePoint]) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [p.lng, p.lat]},
                "properties": {
                    "date": p.acq_date.isoformat(),
                    "time": p.acq_time,
                    "confidence": p.confidence,
                    "frp": p.frp,
                    "source": p.source,
                },
            }
            for p in points
        ],
    }


def from_geojson(doc: dict[str, Any]) -> list[FirePoint]:
    out = []
    for f in doc.get("features", []):
        lng, lat = f["geometry"]["coordinates"][:2]
        props = f.get("properties", {})
        out.append(
            FirePoint(
                lat=lat,
                lng=lng,
                acq_date=date.fromisoformat(props["date"]),
                acq_time=props.get("time", ""),
                confidence=str(props.get("confidence", "")),
                frp=props.get("frp"),
                source=props.get("source", ""),
            )
        )
    return out


def village_scores(
    points: list[FirePoint], villages: list[Village], radius_km: float
) -> dict[str, tuple[int, float]]:
    """village_id → (points within radius, min-max normalised score 0..1 across the district)."""
    counts = {
        v.village_id: sum(1 for p in points if haversine_km(v.lat, v.lng, p.lat, p.lng) <= radius_km)
        for v in villages
    }
    if not counts:
        return {}
    lo, hi = min(counts.values()), max(counts.values())
    span = hi - lo
    return {vid: (n, round((n - lo) / span, 4) if span else 0.0) for vid, n in counts.items()}


def api_requests(
    key: str, source: str, bbox: tuple[float, float, float, float], years: Iterable[int], day_range: int
) -> list[str]:
    """FIRMS area-API URLs that cover Oct 1 – Nov 30 of each year in `day_range`-day chunks."""
    area = ",".join(str(x) for x in bbox)
    urls = []
    for y in years:
        d = date(y, 10, 1)
        end = date(y, 11, 30)
        while d <= end:
            days = min(day_range, (end - d).days + 1)
            urls.append(
                FIRMS_AREA_URL.format(key=key, source=source, area=area, days=days, start=d.isoformat())
            )
            d += timedelta(days=days)
    return urls
