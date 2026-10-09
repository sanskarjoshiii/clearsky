"""Entities stored in DynamoDB (IMPLEMENTATION.md §3)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PField

from clearsky.models.enums import (
    ApplicationStatus,
    BookingStatus,
    BuyerType,
    FieldStatus,
    Language,
    RiskLevel,
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="ignore", use_enum_values=False)


class Village(_Model):
    village_id: str
    name: str
    name_hi: str = ""
    name_pa: str = ""
    aliases: list[str] = PField(default_factory=list)
    block: str = ""
    district: str
    lat: float
    lng: float
    approx: bool = False  # coordinates not yet geocoded / confirmed
    fire_history_score: float = 0.0
    fire_points: int = 0
    risk_unbooked_acres: float = 0.0
    risk_red_fields: int = 0
    risk_yellow_fields: int = 0
    risk_max_score: int = 0


class Farmer(_Model):
    phone: str  # E.164
    name: str
    village_id: str
    language: Language = Language.HINDI
    synthetic: bool = False  # seeded demo record: never send real WhatsApp messages to it
    created_at: datetime


class Field(_Model):
    field_id: str
    phone: str
    village_id: str
    acres: float
    lat: float
    lng: float
    harvest_date: date
    sowing_deadline: date
    harvest_confirmed: bool = False
    status: FieldStatus = FieldStatus.REGISTERED
    booking_id: str | None = None
    risk_score: int = 0
    risk_level: RiskLevel = RiskLevel.GREEN
    risk_reasons: list[str] = PField(default_factory=list)
    source: str = "whatsapp"
    created_at: datetime
    updated_at: datetime


class Baler(_Model):
    baler_id: str
    operator_name: str
    operator_phone: str | None = None  # display only; never used for WhatsApp
    chc_name: str = ""
    base_village_id: str
    lat: float
    lng: float
    acres_per_day: float
    radius_km: float
    active: bool = True


class BalerDay(_Model):
    baler_id: str
    date: date
    booked_acres: float = 0.0
    capacity_acres: float = 0.0
    stop_count: int = 0


class Buyer(_Model):
    buyer_id: str
    name: str
    type: BuyerType
    lat: float
    lng: float
    price_per_tonne: float  # demo value
    demand_tonnes: float
    reserved_tonnes: float = 0.0
    received_tonnes: float = 0.0
    max_radius_km: float

    @property
    def remaining_tonnes(self) -> float:
        return self.demand_tonnes - self.reserved_tonnes


class Booking(_Model):
    booking_id: str
    field_id: str
    phone: str
    village_id: str
    baler_id: str
    buyer_id: str | None = None
    date: date
    stop_order: int = 0
    acres: float
    est_tonnes: float
    lat: float
    lng: float
    buyer_price_per_tonne: float | None = None
    farmer_payout: float = 0.0
    status: BookingStatus = BookingStatus.CONFIRMED
    created_at: datetime
    done_at: datetime | None = None


class Application(_Model):
    """A self-registered baler operator or industry buyer waiting for the officer's decision."""

    application_id: str
    sub: str  # Cognito user id of the applicant
    username: str = ""  # Cognito username for the admin calls on approval
    email: str = ""  # from the token, never from the form
    role: str  # "operator" | "buyer"
    status: ApplicationStatus = ApplicationStatus.PENDING
    name: str
    phone: str  # E.164
    org_name: str  # custom hiring centre or company
    village_id: str
    lat: float
    lng: float
    # baler only → becomes the Baler row
    acres_per_day: float | None = None
    radius_km: float | None = None
    machine_details: str = ""
    # buyer only → becomes the Buyer row
    type: BuyerType | None = None
    price_per_tonne: float | None = None
    demand_tonnes: float | None = None
    max_radius_km: float | None = None
    # audit
    created_at: datetime
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    reject_reason: str | None = None
    entity_id: str | None = None  # the created B… / BY…


class Alert(_Model):
    alert_id: str
    officer_id: str
    village_id: str
    farmers_notified: int = 0
    balers_flagged: list[str] = PField(default_factory=list)
    status: str = "OPEN"
    created_at: datetime


class Button(_Model):
    id: str  # e.g. "confirm:F-123"; comes back as the reply id / template payload
    title: str  # ≤ 20 characters (WhatsApp limit)


class ConversationTurn(_Model):
    phone: str
    ts: str  # ISO timestamp, sort key
    role: str  # "user" | "assistant"
    text: str
    kind: str = "text"  # text | buttons | audio | template | voice_in | location
    buttons: list[Button] = PField(default_factory=list)
    media_url: str | None = None
    ttl: int | None = None
