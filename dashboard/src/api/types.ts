/**
 * Response shapes of the clearsky REST API (backend/src/clearsky/handlers/api.py and models/).
 * Keep in sync with the backend in the same commit (IMPLEMENTATION.md §1.2).
 */

/** The three role apps. A signed-in user with none of these is `pending` (self-registered, not approved yet). */
export type AppRole = "officer" | "buyer" | "operator";
export type Role = AppRole | "pending";
export type ApplicationStatus = "PENDING" | "APPROVED" | "REJECTED" | "SUSPENDED";
export type RiskLevel = "GREEN" | "YELLOW" | "RED";
export type FieldStatus = "REGISTERED" | "HARVESTED" | "BOOKED" | "CLEARED" | "FIRE_REPORTED";
/** OFFERED = sent to a baler, waiting for accept/decline. DECLINED / EXPIRED = that offer ended and the field went to the next baler. */
export type BookingStatus = "OFFERED" | "CONFIRMED" | "DONE" | "CANCELLED" | "DECLINED" | "EXPIRED";

export interface Me {
  sub: string;
  role: Role;
  email: string;
  district: string | null;
  buyer_id: string | null;
  baler_id: string | null;
  dev: boolean;
  display_name: string;
  config: { wa_mode: "simulator" | "cloud"; demo_mode: boolean; llm_provider: string; today: string };
}

export interface Village {
  village_id: string;
  name: string;
  name_hi: string;
  name_pa: string;
  block: string;
  district: string;
  lat: number;
  lng: number;
  approx: boolean;
  fire_history_score: number;
  fire_points: number;
  risk_unbooked_acres: number;
  risk_red_fields: number;
  risk_yellow_fields: number;
  risk_max_score: number;
}

export interface FieldRow {
  field_id: string;
  village_id: string;
  village_name: string;
  farmer_name: string | null;
  farmer_phone: string; // masked
  synthetic: boolean;
  acres: number;
  lat: number;
  lng: number;
  harvest_date: string;
  sowing_deadline: string;
  harvest_confirmed: boolean;
  status: FieldStatus;
  booking_id: string | null;
  /** While status is BOOKED: "offered" until a baler accepts, then "confirmed". */
  booking_state?: "offered" | "confirmed" | null;
  risk_score: number;
  risk_level: RiskLevel;
  risk_reasons: string[];
  source: string;
  created_at: string;
  updated_at: string;
}

export interface BookingRow {
  booking_id: string;
  field_id: string;
  village_id: string;
  village_name?: string | null;
  baler_id: string;
  buyer_id: string | null;
  date: string;
  stop_order: number;
  acres: number;
  est_tonnes: number;
  lat: number;
  lng: number;
  buyer_price_per_tonne: number | null;
  farmer_payout: number;
  status: BookingStatus;
  created_at: string;
  done_at?: string | null;
  attempt?: number;
  offered_at?: string | null;
  expires_at?: string | null;
  responded_at?: string | null;
  decline_reason?: string | null;
  decline_note?: string | null;
  farmer_name?: string | null;
  farmer_phone?: string;
  operator_name?: string | null;
  chc_name?: string | null;
  buyer_name?: string | null;
}

export interface Alert {
  alert_id: string;
  officer_id: string;
  village_id: string;
  farmers_notified: number;
  balers_flagged: string[];
  status: string;
  created_at: string;
  village_name?: string;
  distance_km?: number | null;
  unbooked_acres?: number | null;
}

export interface FieldDetail extends FieldRow {
  village: Village;
  bookings: BookingRow[];
  alerts: Alert[];
}

export interface Baler {
  baler_id: string;
  operator_name: string;
  operator_phone?: string | null;
  chc_name: string;
  base_village_id: string;
  base_village_name?: string | null;
  lat: number;
  lng: number;
  acres_per_day: number;
  radius_km: number;
  active: boolean;
  week?: { date: string; booked_acres: number }[];
  upcoming_stops?: number;
  next_stop_date?: string | null;
  open_requests?: number;
}

/** An open offer on a baler's Requests tab. */
export interface OfferRequest {
  booking_id: string;
  field_id: string;
  date: string;
  harvest_date: string | null;
  acres: number;
  est_tonnes: number;
  lat: number;
  lng: number;
  farmer_name: string | null;
  village_name: string;
  distance_km: number;
  offered_at: string | null;
  expires_at: string | null;
  attempt: number;
}

export interface OfferRequests {
  requests: OfferRequest[];
  now: string;
  reasons: { value: string; label: string }[];
}

export interface Buyer {
  buyer_id: string;
  name: string;
  type: "pellet" | "cbg" | "boiler" | "biomass_power";
  lat: number;
  lng: number;
  price_per_tonne: number;
  demand_tonnes: number;
  reserved_tonnes: number;
  received_tonnes: number;
  max_radius_km: number;
  remaining_tonnes: number;
}

export interface Supply {
  buyer: Buyer;
  forecast: { date: string; booked: number; delivered: number }[];
  deliveries: {
    booking_id: string;
    date: string;
    status: BookingStatus;
    village_name: string;
    est_tonnes: number;
    acres: number;
    price_per_tonne: number | null;
    distance_km: number;
  }[];
  totals: { booked: number; delivered: number };
}

export interface Stop {
  booking_id: string;
  field_id: string;
  stop_order: number;
  status: BookingStatus;
  acres: number;
  est_tonnes: number;
  lat: number;
  lng: number;
  farmer_name: string | null;
  farmer_phone: string;
  village_name: string;
}

export interface Route {
  date: string;
  baler: Baler;
  stops: Stop[];
  remaining: number;
  booked_acres: number;
  route: [number, number][];
}

export interface ScheduleDay {
  date: string;
  stops: number;
  done: number;
  booked_acres: number;
  capacity_acres: number;
  villages: string[];
}

export interface BalerHistory {
  from: string;
  to: string;
  rows: {
    booking_id: string;
    date: string;
    done_at: string | null;
    farmer_name: string | null;
    village_name: string;
    acres: number;
    est_tonnes: number;
  }[];
  totals: { fields: number; acres: number; tonnes: number };
}

export interface DemandChange {
  at: string;
  demand_tonnes: number;
  price_per_tonne: number;
  max_radius_km: number;
}

export interface Stats {
  farmers: number;
  fields: number;
  acres_registered: number;
  acres_booked: number;
  acres_cleared: number;
  tonnes_booked: number;
  tonnes_delivered: number;
  payouts_estimated_inr: number;
  bookings: number;
  bookings_done: number;
  offers_waiting: number;
  acres_offered: number;
  red_fields: number;
  yellow_fields: number;
  fields_saved_after_alert: number;
  alerts_sent: number;
  fires_reported: number;
  pm25_avoided_kg: number | null;
  today: string;
  demo_prices: boolean;
}

export interface Turn {
  ts: string;
  role: "user" | "assistant";
  text: string;
  kind: string;
  buttons: { id: string; title: string }[];
  media_url: string | null;
}

export interface AlertResult {
  alert: Alert;
  farmers_notified: number;
  balers_flagged: string[];
  cooldown: boolean;
}

export interface DemoClock {
  today: string;
  simulated: boolean;
  demo_mode: boolean;
}

export interface DevAccounts {
  officer: { id: string; label: string }[];
  buyer: { id: string; label: string }[];
  operator: { id: string; label: string }[];
  pending: { id: string; label: string }[];
}

/** A baler or buyer application (backend models.Application without the applicant's user ids). */
export interface Application {
  application_id: string;
  email: string;
  role: "operator" | "buyer";
  status: ApplicationStatus;
  name: string;
  phone: string;
  org_name: string;
  village_id: string;
  village_name?: string;
  lat: number;
  lng: number;
  acres_per_day?: number | null;
  radius_km?: number | null;
  machine_details?: string;
  type?: Buyer["type"] | null;
  price_per_tonne?: number | null;
  demand_tonnes?: number | null;
  max_radius_km?: number | null;
  created_at: string;
  reviewed_at?: string | null;
  reject_reason?: string | null;
  entity_id?: string | null;
  duplicates?: string[];
}

/** What the applicant sends to POST /api/register. */
export interface ApplicationForm {
  role: "operator" | "buyer";
  name: string;
  phone: string;
  org_name: string;
  village_id: string;
  acres_per_day?: number;
  radius_km?: number;
  machine_details?: string;
  type?: Buyer["type"];
  price_per_tonne?: number;
  demand_tonnes?: number;
  max_radius_km?: number;
}

export interface VillageOption {
  village_id: string;
  name: string;
  block: string;
  lat?: number;
  lng?: number;
  score?: number;
}

export interface Layer {
  name: string;
  available: boolean;
  url?: string;
  geojson?: GeoJSON.FeatureCollection;
}
