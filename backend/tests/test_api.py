"""Phases 5, 6, 9: dashboard REST API, auth/role scoping, operator done flow, buyer, demo, simulator."""

from __future__ import annotations

from typing import Any

import pytest

from clearsky.config import reset_settings
from clearsky.models import BookingStatus, FieldStatus
from clearsky.repo import BookingsRepo, ConversationsRepo, FieldsRepo, VillagesRepo
from clearsky.seed.generate import generate
from clearsky.seed.load import load
from tests.apiclient import BUYER, OFFICER, OFFICER_ALL, call, operator


@pytest.fixture
def api(ddb: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEV_AUTH", "true")
    monkeypatch.setenv("DEMO_MODE", "true")
    reset_settings()
    load(generate(42), prebook=True)


def confirmed_booking() -> Any:
    return next(b for b in BookingsRepo().list_all() if b.status == BookingStatus.CONFIRMED)


def test_auth_required_and_roles(api: None) -> None:
    assert call("GET", "/api/villages")[0] == 401
    assert call("GET", "/api/villages", token="dev.officer")[0] == 401  # malformed
    status, body = call("GET", "/api/villages", token=BUYER)
    assert status == 403 and body["error"]["code"] == "forbidden"
    assert call("GET", "/api/buyers/me/supply", token=operator("B01"))[0] == 403
    assert call("GET", "/api/stats")[0] == 200  # public


def test_dev_login_is_off_by_default(ddb: None) -> None:
    load(generate(42), prebook=False)
    assert call("POST", "/api/dev/login", {"role": "officer"})[0] == 404
    assert call("GET", "/api/villages", token=OFFICER)[0] == 401  # dev tokens ignored when DEV_AUTH=false


def test_cognito_claims(api: None) -> None:
    claims = {"sub": "abc", "cognito:groups": "[operator]", "custom:baler_id": "B01", "email": "o@x"}
    status, me = call("GET", "/api/me", claims=claims)
    assert status == 200 and me["role"] == "operator" and me["baler_id"] == "B01" and not me["dev"]
    # signed in but in no clearsky group: a self-registered user waiting for approval
    assert call("GET", "/api/me", claims={"sub": "x", "cognito:groups": "[nobody]"})[1]["role"] == "pending"
    assert call("GET", "/api/villages", claims={"sub": "x", "cognito:groups": "[nobody]"})[0] == 403


def test_dev_login_and_accounts(api: None) -> None:
    status, body = call("POST", "/api/dev/login", {"role": "buyer", "id": "BY01"})
    assert status == 200 and body["token"] == BUYER and body["principal"]["buyer_id"] == "BY01"
    accounts = call("GET", "/api/dev/accounts")[1]
    assert len(accounts["operator"]) == 10 and accounts["buyer"][0]["label"].startswith("Demo ")
    assert call("POST", "/api/dev/login", {"role": "root"})[0] == 400


def test_officer_views(api: None) -> None:
    villages = call("GET", "/api/villages", token=OFFICER)[1]["villages"]
    assert len(villages) == 31
    fields = call("GET", "/api/fields", token=OFFICER)[1]["fields"]
    assert len(fields) == 60
    assert all("phone" not in f and "*" in f["farmer_phone"] for f in fields)  # masked
    booked = call("GET", "/api/fields", token=OFFICER, query={"status": "booked"})[1]["fields"]
    assert booked and all(f["status"] == "BOOKED" for f in booked)
    detail = call("GET", f"/api/fields/{booked[0]['field_id']}", token=OFFICER)[1]
    assert (
        detail["bookings"][0]["operator_name"] and detail["village"]["village_id"] == booked[0]["village_id"]
    )
    assert call("GET", "/api/fields/nope", token=OFFICER)[0] == 404
    balers = call("GET", "/api/balers", token=OFFICER)[1]["balers"]
    assert len(balers) == 10 and len(balers[0]["week"]) == 7
    assert len(call("GET", "/api/buyers", token=OFFICER)[1]["buyers"]) == 3
    assert call("GET", "/api/bookings", token=OFFICER)[1]["bookings"]
    assert call("GET", "/api/layers/firms", token=OFFICER)[1]["name"] == "firms"
    assert call("GET", "/api/layers/other", token=OFFICER)[0] == 404
    # an officer scoped to another district sees nothing
    assert call("GET", "/api/villages", token="dev.officer.Barnala")[1]["villages"] == []
    assert len(call("GET", "/api/villages", token=OFFICER_ALL)[1]["villages"]) == 31


def test_alert_endpoint(api: None) -> None:
    for v in VillagesRepo().list_all():
        VillagesRepo().update_fields(v.village_id, {"fire_history_score": 1.0})
    call("POST", "/api/demo/simulate", {"action": "run_risk"}, token=OFFICER)
    top = call("GET", "/api/villages", token=OFFICER)[1]["villages"][0]
    status, body = call("POST", "/api/alerts", {"village_id": top["village_id"]}, token=OFFICER)
    assert status == 200 and body["farmers_notified"] >= 1 and not body["cooldown"]
    assert call("POST", "/api/alerts", {"village_id": top["village_id"]}, token=OFFICER)[1]["cooldown"]
    assert call("GET", "/api/alerts", token=OFFICER)[1]["alerts"]
    assert call("POST", "/api/alerts", {"village_id": "V999"}, token=OFFICER)[0] == 404
    assert call("POST", "/api/alerts", {}, token=OFFICER)[0] == 400
    flagged = body["balers_flagged"][0]
    assert (
        call("GET", "/api/operator/me/alerts", token=operator(flagged))[1]["alerts"][0]["village_id"]
        == top["village_id"]
    )


def test_operator_route_done_and_isolation(api: None) -> None:
    bk = confirmed_booking()
    me = call("GET", "/api/operator/me", token=operator(bk.baler_id))[1]["baler"]
    assert me["baler_id"] == bk.baler_id
    status, route = call(
        "GET", "/api/operator/me/route", token=operator(bk.baler_id), query={"date": bk.date.isoformat()}
    )
    assert status == 200 and any(s["booking_id"] == bk.booking_id for s in route["stops"])
    stop = next(s for s in route["stops"] if s["booking_id"] == bk.booking_id)
    assert stop["farmer_phone"].startswith("+91") and "*" not in stop["farmer_phone"]  # own stop: full number
    assert route["route"][0] == [me["lng"], me["lat"]]  # starts at the baler base
    other = next(b for b in ("B01", "B02", "B03", "B04") if b != bk.baler_id)
    assert call("POST", f"/api/bookings/{bk.booking_id}/done", token=operator(other))[0] == 403
    status, done = call("POST", f"/api/bookings/{bk.booking_id}/done", token=operator(bk.baler_id))
    assert status == 200 and done["booking"]["status"] == "DONE"
    assert FieldsRepo().get(bk.field_id).status == FieldStatus.CLEARED  # type: ignore[union-attr]
    assert ConversationsRepo().last(bk.phone, 1)[0].text.startswith("✅")  # farmer notified
    assert call("POST", f"/api/bookings/{bk.booking_id}/done", token=operator(bk.baler_id))[0] == 409
    assert call("GET", "/api/operator/me", token=operator("B99"))[0] == 404


def test_operator_update(api: None) -> None:
    status, body = call(
        "PUT", "/api/operator/me", {"acres_per_day": 25, "active": False}, token=operator("B01")
    )
    assert status == 200 and body["baler"]["acres_per_day"] == 25 and body["baler"]["active"] is False
    assert call("PUT", "/api/operator/me", {"acres_per_day": 500}, token=operator("B01"))[0] == 400
    profile = call(
        "PUT", "/api/operator/me", {"radius_km": 30, "operator_phone": "+919800000000"}, token=operator("B01")
    )[1]["baler"]
    assert profile["radius_km"] == 30 and profile["operator_phone"] == "+919800000000"
    assert profile["acres_per_day"] == 25  # untouched fields keep their value
    assert call("PUT", "/api/operator/me", {"operator_phone": "98000"}, token=operator("B01"))[0] == 400
    assert call("PUT", "/api/operator/me", {"radius_km": 500}, token=operator("B01"))[0] == 400


def test_operator_schedule_and_history(api: None) -> None:
    bk = confirmed_booking()
    token = operator(bk.baler_id)
    days = call("GET", "/api/operator/me/schedule", token=token, query={"days": "14"})[1]["days"]
    assert len(days) == 14 and days[0]["date"] == "2026-10-20"
    day = next(d for d in days if d["date"] == bk.date.isoformat())
    assert day["stops"] >= 1 and day["booked_acres"] >= bk.acres and day["villages"]
    assert call("GET", "/api/operator/me/schedule", token=token, query={"days": "x"})[0] == 400

    window = {"from": "2026-10-01", "to": bk.date.isoformat()}
    assert call("GET", "/api/operator/me/history", token=token, query=window)[1]["totals"]["fields"] == 0
    call("POST", f"/api/bookings/{bk.booking_id}/done", token=token)
    history = call("GET", "/api/operator/me/history", token=token, query=window)[1]
    assert [r["booking_id"] for r in history["rows"]] == [bk.booking_id]
    # no emission factors are configured in tests, so the impact total is empty (see test_impact.py)
    assert history["totals"] == {"fields": 1, "acres": bk.acres, "tonnes": bk.est_tonnes, "impact": {}}
    assert "farmer_phone" not in history["rows"][0]
    assert call("GET", "/api/operator/me/history", token=token, query={"from": "nope"})[0] == 400
    assert call("GET", "/api/operator/me/schedule", token=BUYER)[0] == 403


def test_buyer_supply_and_demand(api: None) -> None:
    status, supply = call("GET", "/api/buyers/me/supply", token=BUYER)
    assert status == 200 and supply["buyer"]["buyer_id"] == "BY01"
    assert {"forecast", "deliveries", "totals"} <= supply.keys()
    reserved = supply["buyer"]["reserved_tonnes"]
    status, upd = call(
        "PUT",
        "/api/buyers/me/demand",
        {"demand_tonnes": reserved + 100, "price_per_tonne": 1750, "max_radius_km": 70},
        token=BUYER,
    )
    assert status == 200 and upd["buyer"]["price_per_tonne"] == 1750
    changes = call("GET", "/api/buyers/me/demand/history", token=BUYER)[1]["changes"]
    assert len(changes) == 1 and changes[0]["price_per_tonne"] == 1750 and changes[0]["at"]
    assert call("GET", "/api/buyers/me/demand/history", token="dev.buyer.BY02")[1]["changes"] == []
    if reserved > 0:
        bad = call(
            "PUT",
            "/api/buyers/me/demand",
            {"demand_tonnes": reserved / 2, "price_per_tonne": 1750, "max_radius_km": 70},
            token=BUYER,
        )
        assert bad[0] == 400


def test_demo_clock_and_simulate(api: None) -> None:
    from clearsky import clock

    clock.set_override(None)  # let the stored demo clock drive "today" in this test
    assert call("PUT", "/api/demo/clock", {"today": "2026-10-26"}, token=OFFICER)[1]["today"] == "2026-10-26"
    assert call("GET", "/api/demo/clock", token=OFFICER)[1]["simulated"] is True
    assert call("PUT", "/api/demo/clock", {"today": "bad"}, token=OFFICER)[0] == 400
    wave = call("POST", "/api/demo/simulate", {"action": "harvest_wave", "n": 3}, token=OFFICER)[1]["result"]
    assert len(wave["fields"]) >= 1
    assert call("POST", "/api/demo/simulate", {"action": "run_reminders"}, token=OFFICER)[0] == 200
    assert call("POST", "/api/demo/simulate", {"action": "nope"}, token=OFFICER)[0] == 400
    reset = call("POST", "/api/demo/simulate", {"action": "reset"}, token=OFFICER)[1]["result"]
    assert reset["today"] == "2026-10-20" and reset["villages"] == 31


def test_demo_routes_hidden_when_demo_off(api: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "false")
    reset_settings()
    assert call("GET", "/api/demo/clock", token=OFFICER)[0] == 404


def test_simulator_end_to_end(api: None) -> None:
    phone = "+919811100001"
    status, body = call("POST", "/api/sim/message", {"phone": phone, "text": "namaste"}, token=OFFICER)
    assert status == 200 and body["sent"][0].startswith("Sat Sri Akal")
    body = call(
        "POST",
        "/api/sim/message",
        {"phone": phone, "text": "Naam Gurpreet, Bhawanigarh, 8 acre, 24 tareekh"},
        token=OFFICER,
    )[1]
    assert body["sent"][0].startswith("📨 Gurpreet ji")
    convo = call("GET", "/api/sim/conversation", token=OFFICER, query={"phone": phone})[1]["turns"]
    assert [t["role"] for t in convo] == ["user", "assistant", "user", "assistant"]
    assert call("POST", "/api/sim/message", {"phone": "12345", "text": "x"}, token=OFFICER)[0] == 400
    assert call("POST", "/api/sim/message", {"phone": phone}, token=OFFICER)[0] == 400
    assert call("POST", "/api/sim/reset", {"phone": phone}, token=OFFICER)[1]["deleted"] == 4
    assert call("POST", "/api/sim/message", {"phone": phone, "text": "hi"}, token=BUYER)[0] == 403


def test_simulator_hidden_in_cloud_mode(api: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WA_MODE", "cloud")
    reset_settings()
    assert call("POST", "/api/sim/message", {"phone": "+919811100001", "text": "x"}, token=OFFICER)[0] == 404


def test_stats(api: None) -> None:
    stats = call("GET", "/api/stats")[1]
    assert stats["fields"] == 60 and stats["bookings"] >= 1
    # clearsky ships with no emission factors: nothing about pollution is reported until they are set
    assert stats["impact"] == {} and stats["impact_configured"] is False and stats["impact_estimate"] is True
    assert stats["acres_booked"] > 0 and stats["demo_prices"] is True


def test_me_includes_display_name(api: None) -> None:
    assert call("GET", "/api/me", token=BUYER)[1]["display_name"] == "Demo Pellet Plant"
    assert call("GET", "/api/me", token=OFFICER)[1]["config"]["wa_mode"] == "simulator"


def test_simulator_inbox_lists_alerted_farmers(api: None) -> None:
    assert call("GET", "/api/sim/inbox", token=OFFICER)[1]["inbox"] == []
    unbooked = [f for f in FieldsRepo().list_all() if f.status.value in ("REGISTERED", "HARVESTED")]
    village_id = unbooked[0].village_id
    open_fields = [f for f in unbooked if f.village_id == village_id]
    call("POST", "/api/alerts", {"village_id": village_id}, token=OFFICER)
    inbox = call("GET", "/api/sim/inbox", token=OFFICER)[1]["inbox"]
    assert {r["phone"] for r in inbox} == {f.phone for f in open_fields}
    assert inbox[0]["name"] and inbox[0]["last_text"].startswith("Namaste")
