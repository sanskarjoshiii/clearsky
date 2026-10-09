"""Self-registration of baler operators and industry buyers, approved by the district officer.

Anyone may sign up (Cognito) and apply. A signed-in user without a group is `pending`. The officer
approves or rejects; approval creates the `Baler`/`Buyer` row (so the matcher can use it), sets the
user's `custom:baler_id` / `custom:buyer_id`, and adds them to the `operator` / `buyer` group.

Cognito is only called when `USER_POOL_ID` is set. Local dev (`DEV_AUTH`) has no pool: the approved
`entity_id` on the application is what the dashboard uses to enter the new account.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Literal

from pydantic import BaseModel, model_validator
from pydantic import Field as PField

from clearsky import clock
from clearsky.auth import Principal
from clearsky.config import get_settings
from clearsky.domain.geo import haversine_km
from clearsky.logging import get_logger
from clearsky.models import Application, ApplicationStatus, Baler, Buyer, BuyerType
from clearsky.repo import ApplicationsRepo, BalersRepo, BuyersRepo, VillagesRepo

log = get_logger(child="registration")

MAX_PIN_KM = 25.0  # a refined map pin must stay near the chosen village
GROUP_FOR = {"operator": "operator", "buyer": "buyer"}
ATTRIBUTE_FOR = {"operator": "custom:baler_id", "buyer": "custom:buyer_id"}


class RegistrationError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class ApplicationForm(BaseModel):
    """What an applicant submits. Email and user id come from the token, never from here."""

    role: Literal["operator", "buyer"]
    name: str = PField(min_length=2, max_length=80)
    phone: str = PField(pattern=r"^\+\d{10,15}$")
    org_name: str = PField(min_length=2, max_length=120)
    village_id: str
    lat: float | None = PField(default=None, ge=-90, le=90)
    lng: float | None = PField(default=None, ge=-180, le=180)
    # baler
    acres_per_day: float | None = PField(default=None, ge=1, le=60)
    radius_km: float | None = PField(default=None, ge=5, le=50)
    machine_details: str = PField(default="", max_length=500)
    # buyer
    type: BuyerType | None = None
    price_per_tonne: float | None = PField(default=None, gt=0, le=100_000)
    demand_tonnes: float | None = PField(default=None, gt=0, le=1_000_000)
    max_radius_km: float | None = PField(default=None, ge=1, le=300)

    @model_validator(mode="after")
    def _role_fields(self) -> ApplicationForm:
        needed = (
            ("acres_per_day", "radius_km")
            if self.role == "operator"
            else ("type", "price_per_tonne", "demand_tonnes", "max_radius_km")
        )
        missing = [f for f in needed if getattr(self, f) is None]
        if missing:
            raise ValueError(f"{', '.join(missing)} required for a {self.role} application")
        if (self.lat is None) != (self.lng is None):
            raise ValueError("lat and lng go together")
        return self


# ------------------------------------------------------------------ applicant


def latest(sub: str) -> Application | None:
    apps = ApplicationsRepo().by_sub(sub)
    return apps[-1] if apps else None


def submit(p: Principal, form: ApplicationForm) -> Application:
    last = latest(p.sub)
    if last is not None and last.status == ApplicationStatus.PENDING:
        raise RegistrationError(409, "application_open", "you already have an application under review")
    if last is not None and last.status != ApplicationStatus.REJECTED:
        raise RegistrationError(409, "already_approved", "this account is already approved")
    village = VillagesRepo().get(form.village_id)
    if village is None:
        raise RegistrationError(400, "bad_request", "village not found")
    lat, lng = village.lat, village.lng
    if form.lat is not None and form.lng is not None:
        if haversine_km(village.lat, village.lng, form.lat, form.lng) > MAX_PIN_KM:
            raise RegistrationError(
                400, "bad_request", f"the map pin must be within {MAX_PIN_KM:g} km of {village.name}"
            )
        lat, lng = form.lat, form.lng
    operator = form.role == "operator"
    app = Application(
        application_id=f"AP-{uuid.uuid4().hex[:12]}",
        sub=p.sub,
        username=p.username or p.sub,
        email=p.email,
        role=form.role,
        name=form.name.strip(),
        phone=form.phone,
        org_name=form.org_name.strip(),
        village_id=form.village_id,
        lat=lat,
        lng=lng,
        acres_per_day=form.acres_per_day if operator else None,
        radius_km=form.radius_km if operator else None,
        machine_details=form.machine_details.strip() if operator else "",
        type=None if operator else form.type,
        price_per_tonne=None if operator else form.price_per_tonne,
        demand_tonnes=None if operator else form.demand_tonnes,
        max_radius_km=None if operator else form.max_radius_km,
        created_at=clock.now(),
    )
    ApplicationsRepo().put(app)
    log.info("application submitted", extra={"application_id": app.application_id, "role": app.role})
    return app


# ------------------------------------------------------------------ officer


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def duplicates(app: Application, balers: list[Baler], buyers: list[Buyer]) -> list[str]:
    """Existing balers/buyers that look like the same organisation (same phone or name): a warning only."""
    out: list[str] = []
    for b in balers:
        if b.baler_id == app.entity_id:
            continue
        if b.operator_phone and b.operator_phone == app.phone:
            out.append(f"Phone matches baler {b.baler_id} ({b.operator_name})")
        elif app.role == "operator" and b.chc_name and _norm(b.chc_name) == _norm(app.org_name):
            out.append(f"Name matches baler {b.baler_id} ({b.chc_name})")
    for y in buyers:
        if y.buyer_id != app.entity_id and app.role == "buyer" and _norm(y.name) == _norm(app.org_name):
            out.append(f"Name matches buyer {y.buyer_id} ({y.name})")
    return out


def _next_id(prefix: str, existing: list[str], after: str | None = None) -> str:
    """B11 after B10, BY04 after BY03. `after` skips an id that was just found taken."""
    numbers = [int(m.group(1)) for i in [*existing, after or ""] if (m := re.fullmatch(rf"{prefix}(\d+)", i))]
    return f"{prefix}{max(numbers, default=0) + 1:02d}"


def _entity(app: Application, entity_id: str) -> Baler | Buyer:
    if app.role == "operator":
        return Baler(
            baler_id=entity_id,
            operator_name=app.name,
            operator_phone=app.phone,
            chc_name=app.org_name,
            base_village_id=app.village_id,
            lat=app.lat,
            lng=app.lng,
            acres_per_day=app.acres_per_day or 0,
            radius_km=app.radius_km or 0,
            active=True,
        )
    assert app.type is not None
    return Buyer(
        buyer_id=entity_id,
        name=app.org_name,
        type=app.type,
        lat=app.lat,
        lng=app.lng,
        price_per_tonne=app.price_per_tonne or 0,
        demand_tonnes=app.demand_tonnes or 0,
        max_radius_km=app.max_radius_km or 0,
    )


def _create_entity(app: Application) -> Baler | Buyer:
    """Claim an id on the application, then create the row under that id (retry if the id is taken)."""
    apps = ApplicationsRepo()
    taken: str | None = None
    for _ in range(5):
        if app.role == "operator":
            entity_id = _next_id("B", [b.baler_id for b in BalersRepo().list_all()], taken)
        else:
            entity_id = _next_id("BY", [b.buyer_id for b in BuyersRepo().list_all()], taken)
        first = taken is None
        if not apps.update_if(
            app.application_id,
            {"entity_id": entity_id},
            ApplicationStatus.PENDING,
            "attribute_not_exists(entity_id)" if first else "",
        ):
            raise RegistrationError(409, "not_pending", "this application is already being reviewed")
        entity = _entity(app, entity_id)
        created = BalersRepo().put_new(entity) if isinstance(entity, Baler) else BuyersRepo().put_new(entity)
        if created:
            return entity
        taken = entity_id  # another approval took this id meanwhile; move to the next one
    raise RegistrationError(409, "conflict", "could not allocate an id; try again")


def _cognito() -> Any:
    import boto3

    return boto3.client("cognito-idp", region_name=get_settings().aws_region)


def _uses_cognito(app: Application) -> bool:
    return bool(get_settings().user_pool_id) and not app.sub.startswith("dev-")


def _grant(app: Application, entity_id: str) -> None:
    """Give the applicant their role in Cognito. Both calls are idempotent, so a retry is safe."""
    if not _uses_cognito(app):
        return
    pool = get_settings().user_pool_id
    username = app.username or app.sub
    client = _cognito()
    client.admin_update_user_attributes(
        UserPoolId=pool,
        Username=username,
        UserAttributes=[{"Name": ATTRIBUTE_FOR[app.role], "Value": entity_id}],
    )
    client.admin_add_user_to_group(UserPoolId=pool, Username=username, GroupName=GROUP_FOR[app.role])


def _revoke(app: Application) -> None:
    if not _uses_cognito(app):
        return
    _cognito().admin_remove_user_from_group(
        UserPoolId=get_settings().user_pool_id,
        Username=app.username or app.sub,
        GroupName=GROUP_FOR[app.role],
    )


def approve(application_id: str, officer_sub: str) -> tuple[Application, Baler | Buyer]:
    """Create the baler/buyer, grant the Cognito role, then mark APPROVED (in that order).

    Every step is conditional on the application still being PENDING, so approving twice or approving
    after a reject returns 409. If Cognito fails midway the application stays PENDING with its
    `entity_id`; pressing Approve again finishes the job with the same id.
    """
    apps = ApplicationsRepo()
    app = apps.get(application_id)
    if app is None:
        raise RegistrationError(404, "not_found", "application not found")
    if app.status != ApplicationStatus.PENDING:
        raise RegistrationError(409, "not_pending", f"application is already {app.status.value.lower()}")

    entity: Baler | Buyer | None
    if app.entity_id:  # an earlier approval stopped halfway: finish it under the same id
        entity = (
            BalersRepo().get(app.entity_id) if app.role == "operator" else BuyersRepo().get(app.entity_id)
        )
        if entity is None:
            entity = _entity(app, app.entity_id)
            if isinstance(entity, Baler):
                BalersRepo().put_new(entity)
            else:
                BuyersRepo().put_new(entity)
    else:
        entity = _create_entity(app)
    entity_id = entity.baler_id if isinstance(entity, Baler) else entity.buyer_id

    try:
        _grant(app, entity_id)
    except Exception as e:
        log.exception("cognito grant failed", extra={"application_id": application_id})
        raise RegistrationError(
            502, "cognito_failed", "could not update the user's sign-in role; press Approve again"
        ) from e

    reviewed = {
        "status": ApplicationStatus.APPROVED.value,
        "reviewed_by": officer_sub,
        "reviewed_at": clock.now().isoformat(),
    }
    if not apps.update_if(application_id, reviewed, ApplicationStatus.PENDING):
        raise RegistrationError(409, "not_pending", "application was reviewed by someone else")
    log.info("application approved", extra={"application_id": application_id, "entity_id": entity_id})
    return apps.get(application_id) or app, entity


def reject(application_id: str, officer_sub: str, reason: str) -> Application:
    apps = ApplicationsRepo()
    app = apps.get(application_id)
    if app is None:
        raise RegistrationError(404, "not_found", "application not found")
    if app.status == ApplicationStatus.PENDING and app.entity_id:
        raise RegistrationError(409, "approval_in_progress", "an approval is half done; press Approve again")
    values = {
        "status": ApplicationStatus.REJECTED.value,
        "reject_reason": reason.strip(),
        "reviewed_by": officer_sub,
        "reviewed_at": clock.now().isoformat(),
    }
    if not apps.update_if(
        application_id, values, ApplicationStatus.PENDING, "attribute_not_exists(entity_id)"
    ):
        raise RegistrationError(409, "not_pending", f"application is already {app.status.value.lower()}")
    return apps.get(application_id) or app


def set_baler_active(baler_id: str, active: bool) -> Baler:
    """Officer switches a baler off (or back on). Off: no new bookings, and a self-registered operator
    loses the `operator` group (their application shows SUSPENDED). Existing bookings stay."""
    balers = BalersRepo()
    baler = balers.get(baler_id)
    if baler is None:
        raise RegistrationError(404, "not_found", "baler not found")
    apps = ApplicationsRepo()
    app = apps.by_entity(baler_id)
    if app is not None:
        try:
            if active:
                _grant(app, baler_id)
            else:
                _revoke(app)
        except Exception as e:
            log.exception("cognito group change failed", extra={"baler_id": baler_id})
            raise RegistrationError(502, "cognito_failed", "could not change the user's sign-in role") from e
        was, now = (
            (ApplicationStatus.SUSPENDED, ApplicationStatus.APPROVED)
            if active
            else (ApplicationStatus.APPROVED, ApplicationStatus.SUSPENDED)
        )
        apps.update_if(app.application_id, {"status": now.value}, was)
    updated = baler.model_copy(update={"active": active})
    balers.put(updated)
    return updated
