"""Dashboard REST API (IMPLEMENTATION.md §9). One Lambda, Powertools HTTP API resolver.

Roles: officer (government super admin: radar, alerts, every table, approvals, demo controls), buyer
(industry: own demand and supply), operator (baler: own stops only; baler_id comes from the token, never
the URL), pending (self-registered, not approved yet: registration endpoints only).
Errors are JSON `{"error": {"code", "message"}}`.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from aws_lambda_powertools.event_handler import APIGatewayHttpResolver, CORSConfig, Response, content_types
from aws_lambda_powertools.event_handler.exceptions import ServiceError
from pydantic import BaseModel, ValidationError
from pydantic import Field as PField

from clearsky import auth, clock
from clearsky.channels import notify
from clearsky.channels.templates import FIELD_CLEARED, FIELD_CLEARED_IMPACT
from clearsky.config import get_settings
from clearsky.domain import alerts as alerts_domain
from clearsky.domain import demo, impact, matching, offers, registration, stats
from clearsky.domain.geo import haversine_km
from clearsky.logging import get_logger, mask_phone
from clearsky.models import ApplicationStatus, BookingStatus
from clearsky.models.enums import FIRM_BOOKING_STATUSES
from clearsky.repo import (
    AlertsRepo,
    ApplicationsRepo,
    BalerDaysRepo,
    BalersRepo,
    BookingsRepo,
    BuyersRepo,
    ConversationsRepo,
    FarmersRepo,
    FieldsRepo,
    SettingsRepo,
    VillagesRepo,
)

log = get_logger(child="api")


def _cors() -> CORSConfig:
    origins = [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()] or ["*"]
    return CORSConfig(
        allow_origin=origins[0],
        extra_origins=origins[1:] or None,
        max_age=600,
        allow_headers=["Authorization", "Content-Type"],
    )


app = APIGatewayHttpResolver(cors=_cors())


# ------------------------------------------------------------------ errors & auth


class ApiError(ServiceError):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(status, message)
        self.code = code


@app.exception_handler(ServiceError)
def _service_error(e: ServiceError) -> Response:
    code = getattr(
        e,
        "code",
        {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found"}.get(
            e.status_code, "error"
        ),
    )
    return Response(
        e.status_code, content_types.APPLICATION_JSON, {"error": {"code": code, "message": e.msg}}
    )


@app.exception_handler(registration.RegistrationError)
def _registration_error(e: registration.RegistrationError) -> Response:
    return Response(
        e.status, content_types.APPLICATION_JSON, {"error": {"code": e.code, "message": e.message}}
    )


@app.exception_handler(ValidationError)
def _validation_error(e: ValidationError) -> Response:
    errors = e.errors()
    first: dict[str, Any] = dict(errors[0]) if errors else {}
    where = ".".join(str(p) for p in first.get("loc", []))
    msg = f"{where}: {first.get('msg', 'invalid')}" if where else str(first.get("msg", "invalid"))
    return Response(400, content_types.APPLICATION_JSON, {"error": {"code": "bad_request", "message": msg}})


@app.exception_handler(Exception)
def _unexpected(e: Exception) -> Response:
    request_id = app.current_event.request_context.request_id
    log.exception("unhandled", extra={"request_id": request_id})
    return Response(
        500,
        content_types.APPLICATION_JSON,
        {"error": {"code": "internal", "message": f"internal error ({request_id})"}},
    )


def principal() -> auth.Principal:
    ev = app.current_event
    p = None
    try:
        p = auth.from_claims(ev.request_context.authorizer.jwt_claim)
    except (AttributeError, KeyError, TypeError):
        p = None
    p = p or auth.from_dev_header(ev.get_header_value("authorization"))
    if p is None:
        raise ApiError(401, "unauthorized", "sign in required")
    return p


def require(*roles: str) -> auth.Principal:
    p = principal()
    if p.role not in roles:
        raise ApiError(403, "forbidden", f"requires role: {', '.join(roles)}")
    return p


def body(model: type[BaseModel]) -> Any:
    return model.model_validate(app.current_event.json_body or {})


def q(name: str) -> str | None:
    return app.current_event.get_query_string_value(name=name, default_value=None)


def masked(phone: str) -> str:
    return mask_phone(phone)


# ------------------------------------------------------------------ public


@app.get("/api/stats")
def get_stats() -> dict[str, Any]:
    return stats.compute()


@app.get("/api/impact")
def get_impact() -> dict[str, Any]:
    """Public impact table: pollution avoided per cleared field, grouped by village (issue #5).

    No sign-in. Farmer names are masked and no phone number or id is returned. Every figure is an
    estimate from the sourced factors in EMISSION_FACTORS; with none configured, `impact` is empty.
    """
    group, period = q("group") or "village", q("period") or "season"
    if group not in ("village", "field") or period not in ("season", "week"):
        raise ApiError(400, "bad_request", "group must be village|field and period season|week")
    return impact.public_table(group, period)


@app.get("/api/me")
def get_me() -> dict[str, Any]:
    p = principal()
    out = p.as_dict()
    if p.role == "buyer" and p.buyer_id:
        b = BuyersRepo().get(p.buyer_id)
        out["display_name"] = b.name if b else p.buyer_id
    elif p.role == "operator" and p.baler_id:
        bl = BalersRepo().get(p.baler_id)
        out["display_name"] = bl.operator_name if bl else p.baler_id
    elif p.role == auth.PENDING:
        out["display_name"] = p.email or "Applicant"
    else:
        out["display_name"] = "District Officer" + (f", {p.district}" if p.district else "")
    out["config"] = {
        "wa_mode": get_settings().wa_mode,
        "demo_mode": get_settings().demo_mode,
        "llm_provider": get_settings().llm_provider,
        "today": clock.today().isoformat(),
    }
    return out


class DevLogin(BaseModel):
    role: str
    id: str | None = None


@app.post("/api/dev/login")
def dev_login() -> dict[str, Any]:
    if not get_settings().dev_auth:
        raise ApiError(404, "not_found", "dev login is disabled")
    req = body(DevLogin)
    if req.role not in (*auth.ROLES, auth.PENDING):
        raise ApiError(400, "bad_request", "unknown role")
    if req.role == auth.PENDING and not (req.id and req.id.replace("-", "").isalnum()):
        raise ApiError(400, "bad_request", "a pending dev login needs an id (letters and digits)")
    token = auth.dev_token(req.role, req.id)
    p = auth.from_dev_header(f"Bearer {token}")
    return {"token": token, "principal": p.as_dict() if p else None}


@app.get("/api/dev/accounts")
def dev_accounts() -> dict[str, Any]:
    """Demo identities for the dev login picker (dev auth only)."""
    if not get_settings().dev_auth:
        raise ApiError(404, "not_found", "dev login is disabled")
    return {
        "officer": [{"id": get_settings().district, "label": f"District Officer, {get_settings().district}"}],
        "buyer": [{"id": b.buyer_id, "label": b.name} for b in BuyersRepo().list_all()],
        "operator": [
            {"id": b.baler_id, "label": f"{b.operator_name} · {b.chc_name}"}
            for b in sorted(BalersRepo().list_all(), key=lambda b: b.baler_id)
        ],
        # a fresh self-registered user (no role yet); approved applicants show up in the lists above
        "pending": [{"id": "applicant", "label": "New applicant (pending approval)"}],
    }


# ------------------------------------------------------------------ registration (pending users)


def _application_json(a: Any, villages: dict[str, Any] | None = None) -> dict[str, Any]:
    row: dict[str, Any] = a.model_dump(mode="json", exclude={"sub", "username"})
    if villages is not None:
        row["village_name"] = villages[a.village_id].name if a.village_id in villages else a.village_id
    return row


@app.get("/api/register/villages")
def register_villages() -> dict[str, Any]:
    """Village list for the application form (any signed-in user). `q` = fuzzy search in any script."""
    principal()
    name = q("q")
    if name:
        from clearsky.domain import villages as villages_domain

        return {"villages": [m.model_dump() for m in villages_domain.resolve(name, limit=5)]}
    rows = sorted(VillagesRepo().list_all(), key=lambda v: v.name)
    return {
        "villages": [
            {"village_id": v.village_id, "name": v.name, "block": v.block, "lat": v.lat, "lng": v.lng}
            for v in rows
        ]
    }


@app.post("/api/register")
def register_submit() -> dict[str, Any]:
    p = require(auth.PENDING)
    created = registration.submit(p, body(registration.ApplicationForm))
    return {"application": _application_json(created)}


@app.get("/api/register/me")
def register_me() -> dict[str, Any]:
    """The caller's latest application (None if they signed up but never applied)."""
    p = principal()
    latest = registration.latest(p.sub)
    villages = {v.village_id: v for v in VillagesRepo().list_all()} if latest else {}
    return {"application": _application_json(latest, villages) if latest else None}


# ------------------------------------------------------------------ officer (super admin)


def _villages_for(p: auth.Principal) -> list[Any]:
    repo = VillagesRepo()
    return repo.by_district(p.district) if p.district else repo.list_all()


@app.get("/api/villages")
def list_villages() -> dict[str, Any]:
    p = require("officer")
    villages = sorted(_villages_for(p), key=lambda v: (-v.risk_max_score, v.name))
    return {"villages": [v.model_dump(mode="json") for v in villages]}


def _field_row(f: Any, farmers: dict[str, Any], villages: dict[str, Any]) -> dict[str, Any]:
    farmer = farmers.get(f.phone)
    village = villages.get(f.village_id)
    row = f.model_dump(mode="json", exclude={"phone"})
    row.update(
        {
            "farmer_name": farmer.name if farmer else None,
            "farmer_phone": masked(f.phone),
            "synthetic": bool(farmer and farmer.synthetic),
            "village_name": village.name if village else f.village_id,
        }
    )
    return row


@app.get("/api/fields")
def list_fields() -> dict[str, Any]:
    p = require("officer")
    villages = {v.village_id: v for v in _villages_for(p)}
    farmers = {f.phone: f for f in FarmersRepo().list_all()}
    village_id, status, level = q("village_id"), q("status"), q("level")
    fields = FieldsRepo().by_village(village_id) if village_id else FieldsRepo().list_all()
    rows = []
    for f in fields:
        if f.village_id not in villages:
            continue
        if status and f.status.value != status.upper():
            continue
        if level and f.risk_level.value != level.upper():
            continue
        rows.append(_field_row(f, farmers, villages))
    rows.sort(key=lambda r: (-r["risk_score"], r["field_id"]))
    return {"fields": rows}


@app.get("/api/fields/<field_id>")
def get_field(field_id: str) -> dict[str, Any]:
    p = require("officer")
    f = FieldsRepo().get(field_id)
    villages = {v.village_id: v for v in _villages_for(p)}
    if f is None or f.village_id not in villages:
        raise ApiError(404, "not_found", "field not found")
    farmer = FarmersRepo().get(f.phone)
    farmers = {f.phone: farmer} if farmer else {}
    out = _field_row(f, farmers, villages)
    out["village"] = villages[f.village_id].model_dump(mode="json")
    bookings = [b for b in BookingsRepo().by_field(field_id)]
    out["bookings"] = []
    for b in sorted(bookings, key=lambda b: b.created_at):
        baler = BalersRepo().get(b.baler_id)
        buyer = BuyersRepo().get(b.buyer_id) if b.buyer_id else None
        row = b.model_dump(mode="json", exclude={"phone"})
        row.update(
            {
                "operator_name": baler.operator_name if baler else None,
                "chc_name": baler.chc_name if baler else None,
                "buyer_name": buyer.name if buyer else None,
            }
        )
        out["bookings"].append(row)
    out["alerts"] = [a.model_dump(mode="json") for a in AlertsRepo().by_village(f.village_id)][-5:]
    return out


class AlertRequest(BaseModel):
    village_id: str


@app.post("/api/alerts")
def post_alert() -> dict[str, Any]:
    p = require("officer")
    req = body(AlertRequest)
    if req.village_id not in {v.village_id for v in _villages_for(p)}:
        raise ApiError(404, "not_found", "village not found")
    result = alerts_domain.create_alert(req.village_id, p.sub)
    return result.model_dump(mode="json")


@app.get("/api/alerts")
def list_alerts() -> dict[str, Any]:
    require("officer")
    village_id = q("village_id")
    items = AlertsRepo().by_village(village_id) if village_id else AlertsRepo().list_all()
    return {"alerts": [a.model_dump(mode="json") for a in reversed(items)]}


@app.get("/api/layers/<name>")
def get_layer(name: str) -> dict[str, Any]:
    require("officer")
    files = {"firms": "firms_2022_2025.geojson", "harvest": "harvest_grid.geojson"}
    if name not in files:
        raise ApiError(404, "not_found", "unknown layer")
    s = get_settings()
    if s.data_bucket:
        import boto3

        s3 = boto3.client("s3", region_name=s.aws_region)
        key = f"layers/{files[name]}"
        try:
            s3.head_object(Bucket=s.data_bucket, Key=key)
        except Exception:
            return {"name": name, "available": False}
        url = s3.generate_presigned_url(
            "get_object", Params={"Bucket": s.data_bucket, "Key": key}, ExpiresIn=900
        )
        return {"name": name, "available": True, "url": url}
    import json

    from clearsky.config import REPO_ROOT

    path = REPO_ROOT / "data" / "layers" / files[name]
    if not path.exists():
        return {"name": name, "available": False}
    return {"name": name, "available": True, "geojson": json.loads(path.read_text(encoding="utf-8"))}


@app.get("/api/balers")
def list_balers() -> dict[str, Any]:
    require("officer")
    today = clock.today()
    days = BalerDaysRepo()
    villages = {v.village_id: v for v in VillagesRepo().list_all()}
    out = []
    for b in sorted(BalersRepo().list_all(), key=lambda b: b.baler_id):
        ledger = days.range(b.baler_id, today, today + timedelta(days=6))
        week = [
            {
                "date": (today + timedelta(days=i)).isoformat(),
                "booked_acres": ledger[today + timedelta(days=i)].booked_acres
                if today + timedelta(days=i) in ledger
                else 0.0,
            }
            for i in range(7)
        ]
        row = b.model_dump(mode="json")
        row["base_village_name"] = villages[b.base_village_id].name if b.base_village_id in villages else None
        row["week"] = week
        row["upcoming_stops"] = len(
            BookingsRepo().confirmed_by_baler(b.baler_id, today, today + timedelta(days=30))
        )
        out.append(row)
    return {"balers": out}


class ActiveUpdate(BaseModel):
    active: bool


@app.post("/api/balers/<baler_id>/active")
def baler_set_active(baler_id: str) -> dict[str, Any]:
    """Officer deactivates (or reactivates) a baler: no new bookings; existing ones stay."""
    require("officer")
    updated = registration.set_baler_active(baler_id, body(ActiveUpdate).active)
    moved = offers.expire_for_baler(baler_id) if not updated.active else None
    return {"baler": updated.model_dump(mode="json"), "offers_moved": moved}


@app.get("/api/applications")
def list_applications() -> dict[str, Any]:
    require("officer")
    status = q("status")
    repo = ApplicationsRepo()
    if status:
        try:
            items = repo.by_status(ApplicationStatus(status.upper()))
        except ValueError as e:
            raise ApiError(400, "bad_request", "unknown status") from e
    else:
        items = repo.list_all()
    villages = {v.village_id: v for v in VillagesRepo().list_all()}
    balers, buyers = BalersRepo().list_all(), BuyersRepo().list_all()
    rows = []
    for a in items:
        row = _application_json(a, villages)
        row["duplicates"] = (
            registration.duplicates(a, balers, buyers) if a.status == ApplicationStatus.PENDING else []
        )
        rows.append(row)
    pending = sum(1 for a in repo.list_all() if a.status == ApplicationStatus.PENDING)
    return {"applications": rows, "pending": pending}


@app.post("/api/applications/<application_id>/approve")
def application_approve(application_id: str) -> dict[str, Any]:
    p = require("officer")
    approved, entity = registration.approve(application_id, p.sub)
    return {"application": _application_json(approved), "entity": entity.model_dump(mode="json")}


class RejectRequest(BaseModel):
    reason: str = PField(min_length=3, max_length=500)


@app.post("/api/applications/<application_id>/reject")
def application_reject(application_id: str) -> dict[str, Any]:
    p = require("officer")
    rejected = registration.reject(application_id, p.sub, body(RejectRequest).reason)
    return {"application": _application_json(rejected)}


@app.get("/api/buyers")
def list_buyers() -> dict[str, Any]:
    require("officer")
    return {
        "buyers": [
            b.model_dump(mode="json") | {"remaining_tonnes": b.remaining_tonnes}
            for b in BuyersRepo().list_all()
        ]
    }


@app.get("/api/bookings")
def list_bookings() -> dict[str, Any]:
    require("officer")
    d = q("date")
    items = BookingsRepo().by_date(date.fromisoformat(d)) if d else BookingsRepo().list_all()
    balers = {b.baler_id: b for b in BalersRepo().list_all()}
    buyers = {b.buyer_id: b for b in BuyersRepo().list_all()}
    villages = {v.village_id: v for v in VillagesRepo().list_all()}
    farmers = {f.phone: f for f in FarmersRepo().list_all()}
    rows = []
    for b in sorted(items, key=lambda b: (b.date, b.baler_id, b.stop_order)):
        row = b.model_dump(mode="json", exclude={"phone"})
        row.update(
            {
                "farmer_name": farmers[b.phone].name if b.phone in farmers else None,
                "farmer_phone": masked(b.phone),
                "operator_name": balers[b.baler_id].operator_name if b.baler_id in balers else None,
                "buyer_name": buyers[b.buyer_id].name if b.buyer_id in buyers else None,
                "village_name": villages[b.village_id].name if b.village_id in villages else None,
            }
        )
        rows.append(row)
    return {"bookings": rows}


# ------------------------------------------------------------------ buyer (industry)


def _buyer(p: auth.Principal) -> Any:
    b = BuyersRepo().get(p.buyer_id or "")
    if b is None:
        raise ApiError(404, "not_found", "buyer profile not found for this account")
    return b


@app.get("/api/buyers/me/supply")
def buyer_supply() -> dict[str, Any]:
    p = require("buyer")
    b = _buyer(p)
    items = [
        bk
        for bk in BookingsRepo().list_all()
        if bk.buyer_id == b.buyer_id and bk.status in FIRM_BOOKING_STATUSES  # offers are not supply yet
    ]
    by_date: dict[str, dict[str, float]] = {}
    for bk in items:
        day = by_date.setdefault(bk.date.isoformat(), {"booked": 0.0, "delivered": 0.0})
        day["delivered" if bk.status == BookingStatus.DONE else "booked"] += bk.est_tonnes
    villages = {v.village_id: v for v in VillagesRepo().list_all()}
    deliveries = [
        {
            "booking_id": bk.booking_id,
            "date": bk.date.isoformat(),
            "status": bk.status.value,
            "village_name": villages[bk.village_id].name if bk.village_id in villages else bk.village_id,
            "est_tonnes": bk.est_tonnes,
            "acres": bk.acres,
            "price_per_tonne": bk.buyer_price_per_tonne,
            "distance_km": round(haversine_km(bk.lat, bk.lng, b.lat, b.lng), 1),
            "impact": impact.shown(bk.impact),  # kg per pollutant, DONE rows only (estimate)
        }
        for bk in sorted(items, key=lambda x: (x.date, x.booking_id))
    ]
    return {
        "buyer": b.model_dump(mode="json") | {"remaining_tonnes": b.remaining_tonnes},
        "forecast": [{"date": d, **v} for d, v in sorted(by_date.items())],
        "deliveries": deliveries,
        "totals": {
            "booked": round(sum(v["booked"] for v in by_date.values()), 1),
            "delivered": round(sum(v["delivered"] for v in by_date.values()), 1),
        },
        # pollution avoided by the straw this buyer received
        "impact": impact.display(impact.totals(items)),
    }


class DemandUpdate(BaseModel):
    demand_tonnes: float = PField(gt=0, le=1_000_000)
    price_per_tonne: float = PField(gt=0, le=100_000)
    max_radius_km: float = PField(ge=1, le=300)


@app.put("/api/buyers/me/demand")
def buyer_demand() -> dict[str, Any]:
    p = require("buyer")
    b = _buyer(p)
    req = body(DemandUpdate)
    if req.demand_tonnes < b.reserved_tonnes:
        raise ApiError(400, "bad_request", f"demand can't be below already reserved {b.reserved_tonnes:g} t")
    updated = b.model_copy(update=req.model_dump())
    BuyersRepo().put(updated)  # existing bookings keep their price; new bookings use these values
    SettingsRepo().add_demand_change(b.buyer_id, {"at": clock.now().isoformat(), **req.model_dump()})
    return {"buyer": updated.model_dump(mode="json") | {"remaining_tonnes": updated.remaining_tonnes}}


@app.get("/api/buyers/me/demand/history")
def buyer_demand_history() -> dict[str, Any]:
    b = _buyer(require("buyer"))
    return {"changes": list(reversed(SettingsRepo().demand_history(b.buyer_id)))}


# ------------------------------------------------------------------ operator (baler)


def _baler(p: auth.Principal) -> Any:
    b = BalersRepo().get(p.baler_id or "")
    if b is None:
        raise ApiError(404, "not_found", "baler profile not found for this account")
    return b


@app.get("/api/operator/me")
def operator_me() -> dict[str, Any]:
    b = _baler(require("operator"))
    village = VillagesRepo().get(b.base_village_id)
    today = clock.today()
    upcoming = BookingsRepo().confirmed_by_baler(b.baler_id, today, today + timedelta(days=60))
    next_day = min((bk.date for bk in upcoming), default=None)
    return {
        "baler": b.model_dump(mode="json")
        | {
            "base_village_name": village.name if village else None,
            "next_stop_date": next_day.isoformat() if next_day else None,
            "open_requests": sum(1 for bk in BookingsRepo().offered() if bk.baler_id == b.baler_id),
        }
    }


class OperatorUpdate(BaseModel):
    acres_per_day: float | None = PField(default=None, ge=1, le=60)
    radius_km: float | None = PField(default=None, ge=5, le=50)
    operator_phone: str | None = PField(default=None, pattern=r"^\+\d{10,15}$")
    active: bool | None = None


@app.put("/api/operator/me")
def operator_update() -> dict[str, Any]:
    b = _baler(require("operator"))
    req = body(OperatorUpdate)
    changes = {k: v for k, v in req.model_dump().items() if v is not None}
    updated = b.model_copy(update=changes)
    BalersRepo().put(updated)  # affects new bookings only
    if b.active and not updated.active:
        offers.expire_for_baler(b.baler_id)  # off duty: open requests move to other balers at once
    return {"baler": updated.model_dump(mode="json")}


def _route_line(points: list[tuple[float, float]]) -> list[list[float]]:
    """[lng, lat] polyline: Amazon Location route if configured, else straight lines between stops."""
    s = get_settings()
    if s.route_calculator_name and len(points) >= 2:
        try:
            import boto3

            loc = boto3.client("location", region_name=s.aws_region)
            resp = loc.calculate_route(
                CalculatorName=s.route_calculator_name,
                DeparturePosition=[points[0][1], points[0][0]],
                DestinationPosition=[points[-1][1], points[-1][0]],
                WaypointPositions=[[p[1], p[0]] for p in points[1:-1]][:23],
                IncludeLegGeometry=True,
            )
            line: list[list[float]] = []
            for leg in resp["Legs"]:
                line.extend(leg.get("Geometry", {}).get("LineString", []))
            if line:
                return line
        except Exception:
            log.warning("route calculation failed; using straight lines")
    return [[lng, lat] for lat, lng in points]


@app.get("/api/operator/me/route")
def operator_route() -> dict[str, Any]:
    b = _baler(require("operator"))
    d = date.fromisoformat(q("date") or clock.today().isoformat())
    # the route holds accepted work only; open offers live on the Requests tab
    stops = sorted(BookingsRepo().firm_by_baler(b.baler_id, d), key=lambda x: (x.stop_order, x.booking_id))
    farmers = {f.phone: f for f in FarmersRepo().list_all()}
    villages = {v.village_id: v for v in VillagesRepo().list_all()}
    rows = []
    for s in stops:
        farmer = farmers.get(s.phone)
        rows.append(
            {
                "booking_id": s.booking_id,
                "field_id": s.field_id,
                "stop_order": s.stop_order,
                "status": s.status.value,
                "acres": s.acres,
                "est_tonnes": s.est_tonnes,
                "lat": s.lat,
                "lng": s.lng,
                "farmer_name": farmer.name if farmer else None,
                "farmer_phone": s.phone,  # operator needs the full number for the call button (own stops only)
                "village_name": villages[s.village_id].name if s.village_id in villages else s.village_id,
                "impact": impact.shown(s.impact),
            }
        )
    confirmed = [r for r in rows if r["status"] == "CONFIRMED"]
    points = [(b.lat, b.lng)] + [(r["lat"], r["lng"]) for r in rows]
    ledger = BalerDaysRepo().get(b.baler_id, d)
    return {
        "date": d.isoformat(),
        "baler": b.model_dump(mode="json"),
        "stops": rows,
        "remaining": len(confirmed),
        "booked_acres": ledger.booked_acres if ledger else 0.0,
        "route": _route_line(points) if rows else [],
    }


@app.get("/api/operator/me/schedule")
def operator_schedule() -> dict[str, Any]:
    """Stops and booked acres per day for the next `days` days (default 14)."""
    b = _baler(require("operator"))
    try:
        n = max(1, min(int(q("days") or 14), 31))
    except ValueError as e:
        raise ApiError(400, "bad_request", "days must be a number") from e
    today = clock.today()
    end = today + timedelta(days=n - 1)
    ledger = BalerDaysRepo().range(b.baler_id, today, end)
    by_day: dict[date, list[Any]] = {}
    for bk in BookingsRepo().by_baler(b.baler_id, today, end):
        if bk.status in (BookingStatus.CONFIRMED, BookingStatus.DONE):
            by_day.setdefault(bk.date, []).append(bk)
    villages = {v.village_id: v for v in VillagesRepo().list_all()}
    out = []
    for i in range(n):
        d = today + timedelta(days=i)
        stops = by_day.get(d, [])
        out.append(
            {
                "date": d.isoformat(),
                "stops": len(stops),
                "done": sum(1 for s in stops if s.status == BookingStatus.DONE),
                "booked_acres": ledger[d].booked_acres if d in ledger else 0.0,
                "capacity_acres": b.acres_per_day,
                "villages": sorted(
                    {villages[s.village_id].name if s.village_id in villages else s.village_id for s in stops}
                ),
            }
        )
    return {"days": out}


@app.get("/api/operator/me/history")
def operator_history() -> dict[str, Any]:
    """Fields this baler has cleared (DONE bookings), newest first, with season totals."""
    b = _baler(require("operator"))
    frm, to = q("from"), q("to")
    try:
        start = date.fromisoformat(frm) if frm else get_settings().season_start
        end = date.fromisoformat(to) if to else clock.today()
    except ValueError as e:
        raise ApiError(400, "bad_request", "from/to must be YYYY-MM-DD") from e
    done = [bk for bk in BookingsRepo().by_baler(b.baler_id, start, end) if bk.status == BookingStatus.DONE]
    farmers = {f.phone: f for f in FarmersRepo().list_all()}
    villages = {v.village_id: v for v in VillagesRepo().list_all()}
    rows = [
        {
            "booking_id": bk.booking_id,
            "date": bk.date.isoformat(),
            "done_at": bk.done_at.isoformat() if bk.done_at else None,
            "farmer_name": farmers[bk.phone].name if bk.phone in farmers else None,
            "village_name": villages[bk.village_id].name if bk.village_id in villages else bk.village_id,
            "acres": bk.acres,
            "est_tonnes": bk.est_tonnes,
            "impact": impact.shown(bk.impact),
        }
        for bk in sorted(done, key=lambda x: (x.date, x.booking_id), reverse=True)
    ]
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "rows": rows,
        "totals": {
            "fields": len(rows),
            "acres": round(sum(bk.acres for bk in done), 1),
            "tonnes": round(sum(bk.est_tonnes for bk in done), 1),
            "impact": impact.display(impact.totals(done)),
        },
    }


@app.get("/api/operator/me/requests")
def operator_requests() -> dict[str, Any]:
    """Open offers for this baler: fields the matcher wants them to take, waiting for accept or decline."""
    b = _baler(require("operator"))
    return {
        "requests": offers.request_rows(b),
        "now": clock.now().isoformat(),
        "reasons": [{"value": k, "label": v} for k, v in offers.DECLINE_REASONS.items()],
    }


@app.get("/api/operator/me/alerts")
def operator_alerts() -> dict[str, Any]:
    b = _baler(require("operator"))
    villages = {v.village_id: v for v in VillagesRepo().list_all()}
    out = []
    for a in reversed(alerts_domain.open_alerts_for_baler(b.baler_id)):
        v = villages.get(a.village_id)
        out.append(
            a.model_dump(mode="json")
            | {
                "village_name": v.name if v else a.village_id,
                "distance_km": round(haversine_km(b.lat, b.lng, v.lat, v.lng), 1) if v else None,
                "unbooked_acres": v.risk_unbooked_acres if v else None,
            }
        )
    return {"alerts": out}


_OFFER_ERRORS = {
    "not_found": (404, "booking not found"),
    "forbidden": (403, "not your booking"),
    "not_offered": (409, "this request is no longer open"),
    "expired": (409, "this request has expired"),
}


def _offer_error(result: matching.OfferResult) -> ApiError:
    status, message = _OFFER_ERRORS.get(result.error or "", (409, "conflict"))
    return ApiError(status, result.error or "conflict", message)


def _booking_json(bk: Any) -> dict[str, Any]:
    out: dict[str, Any] = bk.model_dump(mode="json", exclude={"phone"})
    return out


@app.post("/api/bookings/<booking_id>/accept")
def booking_accept(booking_id: str) -> dict[str, Any]:
    """The baler accepts an offer: the pickup is confirmed and the farmer is told on WhatsApp."""
    p = require("operator")
    result = offers.accept(booking_id, _baler(p).baler_id)
    if not result.ok or result.booking is None:
        raise _offer_error(result)
    return {"ok": True, "booking": _booking_json(result.booking)}


class DeclineRequest(BaseModel):
    reason: str
    note: str | None = PField(default=None, max_length=300)


@app.post("/api/bookings/<booking_id>/decline")
def booking_decline(booking_id: str) -> dict[str, Any]:
    """The baler declines with a reason: capacity is released and the next-best baler gets the offer."""
    p = require("operator")
    req = body(DeclineRequest)
    if req.reason not in offers.DECLINE_REASONS:
        raise ApiError(400, "bad_request", "unknown reason")
    result, _next = offers.decline(
        booking_id, _baler(p).baler_id, req.reason, (req.note or "").strip() or None
    )
    if not result.ok or result.booking is None:
        raise _offer_error(result)
    return {"ok": True, "booking": _booking_json(result.booking)}


@app.post("/api/bookings/<booking_id>/reassign")
def booking_reassign(booking_id: str) -> dict[str, Any]:
    """The officer moves an unanswered offer to the next baler without waiting for the SLA."""
    require("officer")
    result, following = offers.reassign(booking_id)
    if not result.ok or result.booking is None:
        raise _offer_error(result)
    return {
        "ok": True,
        "booking": _booking_json(result.booking),
        "next": following.model_dump(mode="json") if following else None,
    }


@app.post("/api/bookings/<booking_id>/done")
def booking_done(booking_id: str) -> dict[str, Any]:
    p = require("operator", "officer")
    result = matching.mark_done(booking_id, p.baler_id if p.role == "operator" else None)
    if not result.ok:
        status = {"not_found": 404, "forbidden": 403}.get(result.error or "", 409)
        raise ApiError(
            status,
            result.error or "conflict",
            {
                "not_found": "booking not found",
                "forbidden": "not your booking",
                "not_confirmed": "booking is not open",
            }.get(result.error or "", "conflict"),
        )
    bk = result.booking
    assert bk is not None
    farmer = FarmersRepo().get(bk.phone)
    name = farmer.name if farmer else ""
    avoided = impact.shown(bk.impact)
    if "pm25" in avoided:  # tell the farmer what their field kept out of the air (an estimate)
        notify.send_proactive(bk.phone, FIELD_CLEARED_IMPACT, [name, f"{avoided['pm25']:,.0f}"])
    else:
        notify.send_proactive(bk.phone, FIELD_CLEARED, [name])
    return {
        "ok": True,
        "booking": bk.model_dump(mode="json", exclude={"phone"}),
        "impact": impact.display(avoided),
    }


# ------------------------------------------------------------------ demo (officer, DEMO_MODE)


def _demo_guard() -> auth.Principal:
    p = require("officer")
    if not get_settings().demo_mode:
        raise ApiError(404, "not_found", "demo mode is off")
    return p


class ClockUpdate(BaseModel):
    today: str | None = None


@app.get("/api/demo/clock")
def demo_clock_get() -> dict[str, Any]:
    _demo_guard()
    return demo.get_clock()


@app.put("/api/demo/clock")
def demo_clock_put() -> dict[str, Any]:
    _demo_guard()
    req = body(ClockUpdate)
    try:
        return demo.set_clock(req.today)
    except ValueError as e:
        raise ApiError(400, "bad_request", str(e)) from e


class SimulateRequest(BaseModel):
    action: str
    village_id: str | None = None
    n: int = PField(default=5, ge=1, le=50)


@app.post("/api/demo/simulate")
def demo_simulate() -> dict[str, Any]:
    _demo_guard()
    req = body(SimulateRequest)
    try:
        return {"action": req.action, "result": demo.simulate(req.action, req.village_id, req.n)}
    except demo.DemoError as e:
        raise ApiError(400, "bad_request", str(e)) from e


# ------------------------------------------------------------------ farmer simulator (WA_MODE=simulator)


def _sim_guard() -> auth.Principal:
    p = require("officer")
    if get_settings().wa_mode != "simulator":
        raise ApiError(404, "not_found", "simulator is off (WA_MODE=cloud)")
    return p


class SimMessage(BaseModel):
    phone: str = PField(pattern=r"^\+\d{10,15}$")
    text: str | None = PField(default=None, max_length=1000)
    button_id: str | None = None
    button_title: str | None = None
    lat: float | None = None
    lng: float | None = None


def _turns(phone: str) -> list[dict[str, Any]]:
    return [t.model_dump(mode="json", exclude={"ttl", "phone"}) for t in ConversationsRepo().last(phone, 100)]


@app.post("/api/sim/message")
def sim_message() -> dict[str, Any]:
    _sim_guard()
    import uuid

    from clearsky.channels.whatsapp import Inbound
    from clearsky.handlers.processor import process_inbound

    req = body(SimMessage)
    msg_id = f"sim-{uuid.uuid4().hex[:12]}"
    if req.button_id:
        inbound = Inbound(
            msg_id=msg_id,
            phone=req.phone,
            type="button",
            button_id=req.button_id,
            text=req.button_title or req.button_id,
        )
    elif req.lat is not None and req.lng is not None:
        inbound = Inbound(msg_id=msg_id, phone=req.phone, type="location", lat=req.lat, lng=req.lng)
    elif req.text and req.text.strip():
        inbound = Inbound(msg_id=msg_id, phone=req.phone, type="text", text=req.text.strip())
    else:
        raise ApiError(400, "bad_request", "send text, a button or a location")
    sent = process_inbound(inbound)
    return {"sent": sent, "turns": _turns(req.phone)}


@app.get("/api/sim/conversation")
def sim_conversation() -> dict[str, Any]:
    _sim_guard()
    phone = q("phone") or ""
    if not phone.startswith("+"):
        raise ApiError(400, "bad_request", "phone must be E.164")
    return {"phone": phone, "turns": _turns(phone)}


@app.get("/api/sim/inbox")
def sim_inbox() -> dict[str, Any]:
    """Farmers who recently got a proactive message (alert, reminder, cleared), newest first.

    Simulator mode only: it lets the officer "become" an alerted farmer in the farmer panel. All
    numbers here are simulator/demo numbers (WA_MODE=simulator never reaches real phones).
    """
    _sim_guard()
    from clearsky.repo.base import scan_all, table

    latest: dict[str, dict[str, Any]] = {}
    for item in scan_all(table("Conversations")):
        if item.get("role") != "assistant" or item.get("kind") not in ("buttons", "template"):
            continue
        phone = str(item["phone"])
        if phone not in latest or str(item["ts"]) > latest[phone]["ts"]:
            latest[phone] = {"ts": str(item["ts"]), "text": str(item.get("text", ""))}
    farmers = {f.phone: f for f in FarmersRepo().list_all()}
    villages = {v.village_id: v for v in VillagesRepo().list_all()}
    rows = []
    for phone, last in sorted(latest.items(), key=lambda kv: kv[1]["ts"], reverse=True)[:25]:
        farmer = farmers.get(phone)
        village = villages.get(farmer.village_id) if farmer else None
        rows.append(
            {
                "phone": phone,
                "name": farmer.name if farmer else None,
                "village_name": village.name if village else None,
                "last_ts": last["ts"],
                "last_text": last["text"][:120],
            }
        )
    return {"inbox": rows}


class SimReset(BaseModel):
    phone: str = PField(pattern=r"^\+\d{10,15}$")


@app.post("/api/sim/reset")
def sim_reset() -> dict[str, Any]:
    _sim_guard()
    req = body(SimReset)
    return {"deleted": ConversationsRepo().delete_phone(req.phone)}


# ------------------------------------------------------------------ entry point


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return app.resolve(event, context)
