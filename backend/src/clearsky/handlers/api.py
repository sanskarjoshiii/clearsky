"""Dashboard REST API (IMPLEMENTATION.md §9). One Lambda, Powertools HTTP API resolver.

Roles: officer (government super admin: radar, alerts, every table, demo controls), buyer (industry:
own demand and supply), operator (baler: own stops only; baler_id comes from the token, never the URL).
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
from clearsky.channels.templates import FIELD_CLEARED
from clearsky.config import get_settings
from clearsky.domain import alerts as alerts_domain
from clearsky.domain import demo, matching, stats
from clearsky.domain.geo import haversine_km
from clearsky.logging import get_logger, mask_phone
from clearsky.models import BookingStatus
from clearsky.repo import (
    AlertsRepo,
    BalerDaysRepo,
    BalersRepo,
    BookingsRepo,
    BuyersRepo,
    ConversationsRepo,
    FarmersRepo,
    FieldsRepo,
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


@app.exception_handler(ValidationError)
def _validation_error(e: ValidationError) -> Response:
    errors = e.errors()
    first: dict[str, Any] = dict(errors[0]) if errors else {}
    msg = f"{'.'.join(str(p) for p in first.get('loc', []))}: {first.get('msg', 'invalid')}"
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
    if req.role not in auth.ROLES:
        raise ApiError(400, "bad_request", "unknown role")
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
    }


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
        if bk.buyer_id == b.buyer_id and bk.status != BookingStatus.CANCELLED
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
    return {"buyer": updated.model_dump(mode="json") | {"remaining_tonnes": updated.remaining_tonnes}}


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
        }
    }


class OperatorUpdate(BaseModel):
    acres_per_day: float | None = PField(default=None, ge=1, le=60)
    active: bool | None = None


@app.put("/api/operator/me")
def operator_update() -> dict[str, Any]:
    b = _baler(require("operator"))
    req = body(OperatorUpdate)
    changes = {k: v for k, v in req.model_dump().items() if v is not None}
    updated = b.model_copy(update=changes)
    BalersRepo().put(updated)  # affects new bookings only
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
    stops = sorted(BookingsRepo().by_baler(b.baler_id, d), key=lambda x: (x.stop_order, x.booking_id))
    stops = [s for s in stops if s.status != BookingStatus.CANCELLED]
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
    notify.send_proactive(bk.phone, FIELD_CLEARED, [farmer.name if farmer else ""])
    return {"ok": True, "booking": bk.model_dump(mode="json", exclude={"phone"})}


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
