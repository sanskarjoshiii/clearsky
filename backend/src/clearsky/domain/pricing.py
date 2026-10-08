"""Farmer payout (IMPLEMENTATION.md §5). All rates are DEMO parameters, never real market prices."""

from __future__ import annotations

from pydantic import BaseModel

from clearsky.config import get_settings


class Quote(BaseModel):
    est_tonnes: float
    gross: float
    baling_cost: float
    transport_cost: float
    platform_fee: float
    farmer_payout: float

    @property
    def free_clearance(self) -> bool:
        return self.farmer_payout <= 0


def estimate_tonnes(acres: float) -> float:
    return round(acres * get_settings().tonnes_per_acre, 2)


def quote(acres: float, price_per_tonne: float | None, dist_to_buyer_km: float | None) -> Quote:
    """Payout for one field. No buyer (price None) → no gross, payout 0 ("free clearance")."""
    s = get_settings()
    tonnes = estimate_tonnes(acres)
    gross = tonnes * price_per_tonne if price_per_tonne is not None else 0.0
    baling = acres * s.baling_cost_per_acre
    transport = tonnes * (dist_to_buyer_km or 0.0) * s.transport_cost_per_tonne_km
    fee = s.platform_fee_per_tonne * tonnes if price_per_tonne is not None else 0.0
    payout = max(0.0, gross - baling - transport - fee)
    return Quote(
        est_tonnes=tonnes,
        gross=round(gross, 2),
        baling_cost=round(baling, 2),
        transport_cost=round(transport, 2),
        platform_fee=round(fee, 2),
        farmer_payout=round(payout / 10) * 10.0,  # round to ₹10 for readable messages
    )
