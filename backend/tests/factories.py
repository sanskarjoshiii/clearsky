"""Small builders for test data. Coordinates are synthetic."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from clearsky.domain.matching import compute_sowing_deadline
from clearsky.models import Baler, Buyer, BuyerType, Farmer, Field, FieldStatus, Village
from clearsky.repo import BalersRepo, BuyersRepo, FarmersRepo, FieldsRepo, VillagesRepo

BASE_LAT, BASE_LNG = 30.25, 76.00
NOW = datetime(2026, 10, 20, 10, 0)


def village(
    village_id: str = "V1", name: str = "Testpur", lat: float = BASE_LAT, lng: float = BASE_LNG, **kw: object
) -> Village:
    v = Village(village_id=village_id, name=name, district="Sangrur", lat=lat, lng=lng, **kw)  # type: ignore[arg-type]
    VillagesRepo().put(v)
    return v


def baler(
    baler_id: str = "B1",
    lat: float = BASE_LAT,
    lng: float = BASE_LNG,
    acres_per_day: float = 15,
    radius_km: float = 20,
    active: bool = True,
    base_village_id: str = "V1",
) -> Baler:
    b = Baler(
        baler_id=baler_id,
        operator_name=f"Operator {baler_id}",
        chc_name=f"CHC {baler_id}",
        base_village_id=base_village_id,
        lat=lat,
        lng=lng,
        acres_per_day=acres_per_day,
        radius_km=radius_km,
        active=active,
    )
    BalersRepo().put(b)
    return b


def buyer(
    buyer_id: str = "BY1",
    lat: float = BASE_LAT + 0.1,
    lng: float = BASE_LNG,
    price: float = 1800,
    demand: float = 1000,
    radius: float = 60,
    reserved: float = 0,
) -> Buyer:
    b = Buyer(
        buyer_id=buyer_id,
        name=f"Demo Buyer {buyer_id}",
        type=BuyerType.PELLET,
        lat=lat,
        lng=lng,
        price_per_tonne=price,
        demand_tonnes=demand,
        reserved_tonnes=reserved,
        max_radius_km=radius,
    )
    BuyersRepo().put(b)
    return b


def farmer(phone: str = "+919900000001", village_id: str = "V1", name: str = "Test Farmer") -> Farmer:
    f = Farmer(phone=phone, name=name, village_id=village_id, synthetic=True, created_at=NOW)
    FarmersRepo().put(f)
    return f


def field(
    field_id: str = "F1",
    phone: str = "+919900000001",
    village_id: str = "V1",
    acres: float = 8,
    harvest: date = date(2026, 10, 22),
    deadline: date | None = None,
    lat: float = BASE_LAT,
    lng: float = BASE_LNG,
    status: FieldStatus = FieldStatus.REGISTERED,
) -> Field:
    f = Field(
        field_id=field_id,
        phone=phone,
        village_id=village_id,
        acres=acres,
        lat=lat,
        lng=lng,
        harvest_date=harvest,
        sowing_deadline=deadline or compute_sowing_deadline(harvest),
        status=status,
        created_at=NOW,
        updated_at=NOW,
    )
    FieldsRepo().put(f)
    return f


def km_east(lng: float, km: float, lat: float = BASE_LAT) -> float:
    import math

    return lng + km / (111.320 * math.cos(math.radians(lat)))


def days(n: int) -> timedelta:
    return timedelta(days=n)
