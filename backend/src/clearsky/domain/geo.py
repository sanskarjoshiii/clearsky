"""Small geo helpers. Distances are great-circle (haversine), in km."""

from __future__ import annotations

import math
import random

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def offset_point(lat: float, lng: float, north_km: float, east_km: float) -> tuple[float, float]:
    """Move a point by a small distance (flat-earth approximation, fine below ~50 km)."""
    dlat = north_km / 110.574
    dlng = east_km / (111.320 * math.cos(math.radians(lat)))
    return round(lat + dlat, 6), round(lng + dlng, 6)


def jitter_point(
    lat: float, lng: float, max_km: float, rng: random.Random | None = None
) -> tuple[float, float]:
    """A random point within `max_km` of (lat, lng). Used for field pins (farmers don't share GPS)."""
    r = rng or random.Random()
    dist = max_km * math.sqrt(r.random())
    theta = r.random() * 2 * math.pi
    return offset_point(lat, lng, dist * math.cos(theta), dist * math.sin(theta))


def bbox_contains(bbox: tuple[float, float, float, float], lat: float, lng: float) -> bool:
    """bbox = (west, south, east, north)."""
    west, south, east, north = bbox
    return west <= lng <= east and south <= lat <= north
