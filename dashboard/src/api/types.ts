/**
 * Response shapes of the clearsky REST API (backend/src/clearsky/handlers/api.py and models/).
 * Keep in sync with the backend in the same commit (IMPLEMENTATION.md §1.2).
 */

export type Role = "officer" | "buyer" | "operator";
export type RiskLevel = "GREEN" | "YELLOW" | "RED";
export type FieldStatus = "REGISTERED" | "HARVESTED" | "BOOKED" | "CLEARED" | "FIRE_REPORTED";
export type BookingStatus = "CONFIRMED" | "DONE" | "CANCELLED";

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
}

export interface Layer {
  name: string;
  available: boolean;
  url?: string;
  geojson?: GeoJSON.FeatureCollection;
}
