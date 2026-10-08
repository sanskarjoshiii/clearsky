"""Phase 2: payout formula (demo parameters)."""

from __future__ import annotations

import pytest

from clearsky.config import reset_settings
from clearsky.domain.pricing import estimate_tonnes, quote


def test_estimate_tonnes_uses_setting() -> None:
    assert estimate_tonnes(8) == 20.0


def test_quote_formula() -> None:
    # 8 acres → 20 t; gross 20*1800=36000; baling 8*600=4800; transport 20*10*8=1600; fee 20*50=1000
    q = quote(8, 1800, 10)
    assert (q.gross, q.baling_cost, q.transport_cost, q.platform_fee) == (36000, 4800, 1600, 1000)
    assert q.farmer_payout == 28600
    assert not q.free_clearance


def test_quote_without_buyer_is_free_clearance() -> None:
    q = quote(8, None, None)
    assert q.farmer_payout == 0 and q.free_clearance and q.gross == 0


def test_payout_never_negative(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BALING_COST_PER_ACRE", "100000")
    reset_settings()
    q = quote(8, 1800, 10)
    assert q.farmer_payout == 0 and q.free_clearance


def test_payout_rounded_to_ten_rupees() -> None:
    assert quote(3, 1777, 7.3).farmer_payout % 10 == 0
