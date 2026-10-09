"""Issue #1: self-registration for balers and buyers with officer (super-admin) approval."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import boto3
import pytest

from clearsky.config import reset_settings
from clearsky.domain import matching, registration
from clearsky.models import ApplicationStatus
from clearsky.repo import ApplicationsRepo, BalersRepo, BuyersRepo, VillagesRepo
from clearsky.seed.generate import generate
from clearsky.seed.load import load
from tests import factories as f
from tests.apiclient import BUYER, OFFICER, call, operator

APPLICANT = "dev.pending.asha"

BALER_FORM = {
    "role": "operator",
    "name": "Asha Kaur",
    "phone": "+919812300001",
    "org_name": "Asha Custom Hiring Centre",
    "village_id": "V001",
    "acres_per_day": 18,
    "radius_km": 20,
    "machine_details": "Round baler + rake",
}
BUYER_FORM = {
    "role": "buyer",
    "name": "Ravi Mehta",
    "phone": "+919812300002",
    "org_name": "Mehta Biofuels",
    "village_id": "V001",
    "type": "pellet",
    "price_per_tonne": 1700,
    "demand_tonnes": 500,
    "max_radius_km": 40,
}


@pytest.fixture
def api(ddb: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEV_AUTH", "true")
    reset_settings()
    load(generate(42), prebook=False)


def submit(form: dict[str, Any], token: str = APPLICANT) -> tuple[int, Any]:
    return call("POST", "/api/register", form, token=token)


def test_pending_user_reaches_only_registration_endpoints(api: None) -> None:
    me = call("GET", "/api/me", token=APPLICANT)[1]
    assert me["role"] == "pending" and me["display_name"] == "asha@dev.local"
    for path in (
        "/api/villages",
        "/api/fields",
        "/api/buyers/me/supply",
        "/api/operator/me",
        "/api/applications",
    ):
        assert call("GET", path, token=APPLICANT)[0] == 403, path
    assert call("GET", "/api/register/me", token=APPLICANT)[1] == {"application": None}
    villages = call("GET", "/api/register/villages", token=APPLICANT)[1]["villages"]
    assert len(villages) == 31 and {"village_id", "name", "lat", "lng", "block"} <= villages[0].keys()
    found = call("GET", "/api/register/villages", token=APPLICANT, query={"q": "bhavanigarh"})[1]["villages"]
    assert found and found[0]["name"] == "Bhawanigarh"
    assert call("GET", "/api/register/villages")[0] == 401
    # people who already have a role can't apply
    assert submit(BALER_FORM, token=operator("B01"))[0] == 403
    assert submit(BALER_FORM, token=OFFICER)[0] == 403


def test_application_validation(api: None) -> None:
    for bad in (
        BALER_FORM | {"phone": "98123"},
        BALER_FORM | {"acres_per_day": 0},
        BALER_FORM | {"radius_km": 500},
        {k: v for k, v in BALER_FORM.items() if k != "acres_per_day"},  # baler needs capacity
        BUYER_FORM | {"type": "steel"},
        {k: v for k, v in BUYER_FORM.items() if k != "price_per_tonne"},  # buyer needs a price
        BALER_FORM | {"role": "officer"},  # nobody can apply to be the officer
        BALER_FORM | {"village_id": "V999"},
        BALER_FORM | {"lat": 30.25},  # lat without lng
        BALER_FORM | {"lat": 28.6, "lng": 77.2},  # pin far from the village
    ):
        status, body = submit(bad)
        assert status == 400 and body["error"]["code"] == "bad_request", bad
    assert ApplicationsRepo().list_all() == []


def test_submit_then_duplicate_is_refused(api: None) -> None:
    status, body = submit(
        BALER_FORM | {"email": "evil@example.test", "status": "APPROVED", "entity_id": "B01"}
    )
    app = body["application"]
    assert status == 200 and app["status"] == "PENDING" and app["role"] == "operator"
    assert app["email"] == "asha@dev.local" and app.get("entity_id") is None  # from the token, not the form
    assert "sub" not in app and "username" not in app
    village = VillagesRepo().get("V001")
    assert village is not None and (app["lat"], app["lng"]) == (village.lat, village.lng)
    assert submit(BALER_FORM)[1]["error"]["code"] == "application_open"
    mine = call("GET", "/api/register/me", token=APPLICANT)[1]["application"]
    assert mine["application_id"] == app["application_id"] and mine["village_name"] == village.name
    # another user's application is theirs alone
    assert call("GET", "/api/register/me", token="dev.pending.other")[1] == {"application": None}


def test_officer_lists_and_approves_a_baler(api: None) -> None:
    app_id = submit(BALER_FORM)[1]["application"]["application_id"]
    submit(BUYER_FORM, token="dev.pending.ravi")
    listing = call("GET", "/api/applications", token=OFFICER)[1]
    assert listing["pending"] == 2 and len(listing["applications"]) == 2
    assert (
        call("GET", "/api/applications", token=OFFICER, query={"status": "approved"})[1]["applications"] == []
    )
    assert call("GET", "/api/applications", token=OFFICER, query={"status": "nope"})[0] == 400
    assert call("GET", "/api/applications", token=BUYER)[0] == 403
    assert call("POST", f"/api/applications/{app_id}/approve", token=APPLICANT)[0] == 403

    status, body = call("POST", f"/api/applications/{app_id}/approve", token=OFFICER)
    assert status == 200 and body["application"]["status"] == "APPROVED"
    assert body["entity"]["baler_id"] == "B11" and body["application"]["entity_id"] == "B11"
    baler = BalersRepo().get("B11")
    assert baler is not None and baler.active and baler.operator_name == "Asha Kaur"
    assert baler.operator_phone == "+919812300001" and baler.chc_name == "Asha Custom Hiring Centre"
    assert (baler.acres_per_day, baler.radius_km, baler.base_village_id) == (18, 20, "V001")
    # idempotent: a second approve, or a reject after approval, changes nothing
    assert (
        call("POST", f"/api/applications/{app_id}/approve", token=OFFICER)[1]["error"]["code"]
        == "not_pending"
    )
    assert (
        call("POST", f"/api/applications/{app_id}/reject", {"reason": "changed my mind"}, token=OFFICER)[0]
        == 409
    )
    assert len(BalersRepo().list_all()) == 11
    assert call("GET", "/api/applications", token=OFFICER)[1]["pending"] == 1
    # the applicant sees it, the new account works, and the dev login lists it
    assert call("GET", "/api/register/me", token=APPLICANT)[1]["application"]["entity_id"] == "B11"
    assert call("GET", "/api/operator/me", token=operator("B11"))[1]["baler"]["operator_name"] == "Asha Kaur"
    assert any(a["id"] == "B11" for a in call("GET", "/api/dev/accounts")[1]["operator"])
    assert submit(BALER_FORM)[1]["error"]["code"] == "already_approved"
    assert call("POST", "/api/applications/AP-nope/approve", token=OFFICER)[0] == 404


def test_approved_buyer_gets_a_buyer_row(api: None) -> None:
    app_id = submit(BUYER_FORM, token="dev.pending.ravi")[1]["application"]["application_id"]
    body = call("POST", f"/api/applications/{app_id}/approve", token=OFFICER)[1]
    assert body["entity"]["buyer_id"] == "BY04"
    buyer = BuyersRepo().get("BY04")
    assert buyer is not None and buyer.name == "Mehta Biofuels" and buyer.type.value == "pellet"
    assert (buyer.price_per_tonne, buyer.demand_tonnes, buyer.max_radius_km) == (1700, 500, 40)
    assert call("GET", "/api/buyers/me/supply", token="dev.buyer.BY04")[1]["buyer"]["buyer_id"] == "BY04"


def test_reject_needs_a_reason_and_allows_resubmission(api: None) -> None:
    app_id = submit(BALER_FORM)[1]["application"]["application_id"]
    assert call("POST", f"/api/applications/{app_id}/reject", {}, token=OFFICER)[0] == 400
    assert call("POST", f"/api/applications/{app_id}/reject", {"reason": " "}, token=OFFICER)[0] == 400
    status, body = call(
        "POST", f"/api/applications/{app_id}/reject", {"reason": "Phone number not reachable"}, token=OFFICER
    )
    assert status == 200 and body["application"]["status"] == "REJECTED"
    mine = call("GET", "/api/register/me", token=APPLICANT)[1]["application"]
    assert mine["status"] == "REJECTED" and mine["reject_reason"] == "Phone number not reachable"
    assert call("POST", f"/api/applications/{app_id}/approve", token=OFFICER)[0] == 409
    assert BalersRepo().get("B11") is None
    # edit and resubmit: a new application, the old one stays as history
    again = submit(BALER_FORM | {"phone": "+919812300009"})[1]["application"]
    assert again["status"] == "PENDING" and again["application_id"] != app_id
    assert [a.status for a in ApplicationsRepo().by_sub("dev-pending-asha")] == [
        ApplicationStatus.REJECTED,
        ApplicationStatus.PENDING,
    ]


def test_duplicate_org_or_phone_is_flagged_for_the_officer(api: None) -> None:
    existing = BalersRepo().get("B01")
    assert existing is not None
    BalersRepo().put(existing.model_copy(update={"operator_phone": "+919812300001"}))
    submit(BALER_FORM)
    submit(BUYER_FORM | {"org_name": "demo pellet plant"}, token="dev.pending.ravi")
    rows = {a["role"]: a for a in call("GET", "/api/applications", token=OFFICER)[1]["applications"]}
    assert rows["operator"]["duplicates"] == [f"Phone matches baler B01 ({existing.operator_name})"]
    assert rows["buyer"]["duplicates"] == ["Name matches buyer BY01 (Demo Pellet Plant)"]


def test_approved_baler_becomes_bookable(ddb: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """A farmer near the new baler's base gets matched to it."""
    monkeypatch.setenv("DEV_AUTH", "true")
    reset_settings()
    f.village("V001", "Testpur")
    f.farmer()
    f.field("F1")
    assert matching.book_pickup("F1").kind == "no_slot"  # no baler anywhere yet
    app_id = submit(BALER_FORM)[1]["application"]["application_id"]
    assert (
        call("POST", f"/api/applications/{app_id}/approve", token=OFFICER)[1]["entity"]["baler_id"] == "B01"
    )
    booked = matching.book_pickup("F1")
    assert booked.kind == "booked" and booked.baler_id == "B01" and booked.operator_name == "Asha Kaur"


def test_officer_deactivates_and_reactivates_a_baler(api: None) -> None:
    app_id = submit(BALER_FORM)[1]["application"]["application_id"]
    call("POST", f"/api/applications/{app_id}/approve", token=OFFICER)
    status, body = call("POST", "/api/balers/B11/active", {"active": False}, token=OFFICER)
    assert status == 200 and body["baler"]["active"] is False
    assert call("GET", "/api/register/me", token=APPLICANT)[1]["application"]["status"] == "SUSPENDED"
    assert "B11" not in {b.baler_id for b in BalersRepo().list_active()}
    call("POST", "/api/balers/B11/active", {"active": True}, token=OFFICER)
    assert call("GET", "/api/register/me", token=APPLICANT)[1]["application"]["status"] == "APPROVED"
    # a seed baler (no application) can be switched off too
    assert (
        call("POST", "/api/balers/B01/active", {"active": False}, token=OFFICER)[1]["baler"]["active"]
        is False
    )
    assert call("POST", "/api/balers/B99/active", {"active": False}, token=OFFICER)[0] == 404
    assert call("POST", "/api/balers/B01/active", {"active": True}, token=operator("B01"))[0] == 403


# ------------------------------------------------------------------ Cognito (moto)


@pytest.fixture
def pool(api: None, monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, Any]]:
    """A Cognito pool with the stack's groups and attributes, and one self-registered user."""
    client = boto3.client("cognito-idp", region_name="ap-south-1")
    pool_id = client.create_user_pool(
        PoolName="test-users",
        UsernameAttributes=["email"],
        Schema=[
            {"Name": n, "AttributeDataType": "String", "Mutable": True}
            for n in ("baler_id", "buyer_id", "district")
        ],
    )["UserPool"]["Id"]
    for group in ("officer", "buyer", "operator"):
        client.create_group(UserPoolId=pool_id, GroupName=group)
    user = client.admin_create_user(UserPoolId=pool_id, Username="asha@example.test")["User"]
    sub = next(a["Value"] for a in user["Attributes"] if a["Name"] == "sub")
    monkeypatch.setenv("USER_POOL_ID", pool_id)
    reset_settings()
    claims = {"sub": sub, "cognito:username": user["Username"], "email": "asha@example.test"}
    yield {"client": client, "pool_id": pool_id, "username": user["Username"], "claims": claims}


def _groups(pool: dict[str, Any]) -> list[str]:
    resp = pool["client"].admin_list_groups_for_user(UserPoolId=pool["pool_id"], Username=pool["username"])
    return [g["GroupName"] for g in resp["Groups"]]


def _attribute(pool: dict[str, Any], name: str) -> str | None:
    user = pool["client"].admin_get_user(UserPoolId=pool["pool_id"], Username=pool["username"])
    return next((a["Value"] for a in user["UserAttributes"] if a["Name"] == name), None)


def test_signed_up_user_without_a_group_is_pending(pool: dict[str, Any]) -> None:
    status, me = call("GET", "/api/me", claims=pool["claims"])
    assert status == 200 and me["role"] == "pending" and me["baler_id"] is None and not me["dev"]
    # a forged custom attribute on a group-less token grants nothing
    forged = pool["claims"] | {"custom:baler_id": "B01"}
    assert call("GET", "/api/me", claims=forged)[1]["baler_id"] is None
    assert call("GET", "/api/operator/me", claims=forged)[0] == 403


def test_approval_sets_the_cognito_group_and_attribute(pool: dict[str, Any]) -> None:
    app_id = call("POST", "/api/register", BALER_FORM, claims=pool["claims"])[1]["application"][
        "application_id"
    ]
    assert _groups(pool) == []
    call("POST", f"/api/applications/{app_id}/approve", token=OFFICER)
    assert _groups(pool) == ["operator"] and _attribute(pool, "custom:baler_id") == "B11"
    # the refreshed token now carries the group and the id: the user is an operator
    approved = pool["claims"] | {"cognito:groups": ["operator"], "custom:baler_id": "B11"}
    assert call("GET", "/api/operator/me", claims=approved)[1]["baler"]["baler_id"] == "B11"
    # deactivating removes the group again
    call("POST", "/api/balers/B11/active", {"active": False}, token=OFFICER)
    assert _groups(pool) == []


def test_cognito_failure_leaves_the_application_pending_and_retry_reuses_the_id(
    pool: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    app_id = call("POST", "/api/register", BALER_FORM, claims=pool["claims"])[1]["application"][
        "application_id"
    ]

    def boom() -> Any:
        raise RuntimeError("cognito is down")

    with monkeypatch.context() as broken:
        broken.setattr(registration, "_cognito", boom)
        status, body = call("POST", f"/api/applications/{app_id}/approve", token=OFFICER)
        assert status == 502 and body["error"]["code"] == "cognito_failed"
    stuck = ApplicationsRepo().get(app_id)
    assert stuck is not None and stuck.status == ApplicationStatus.PENDING and stuck.entity_id == "B11"
    # half-approved: rejecting is refused, approving again finishes with the same id
    assert call("POST", f"/api/applications/{app_id}/reject", {"reason": "nope"}, token=OFFICER)[0] == 409
    body = call("POST", f"/api/applications/{app_id}/approve", token=OFFICER)[1]
    assert body["application"]["status"] == "APPROVED" and body["entity"]["baler_id"] == "B11"
    assert len(BalersRepo().list_all()) == 11 and _groups(pool) == ["operator"]
