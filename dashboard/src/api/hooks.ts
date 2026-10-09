import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type {
  Alert,
  AlertResult,
  Application,
  ApplicationForm,
  ApplicationStatus,
  Baler,
  BalerHistory,
  BookingRow,
  Buyer,
  DemandChange,
  DemoClock,
  DevAccounts,
  FieldDetail,
  FieldRow,
  Layer,
  Route,
  ScheduleDay,
  Stats,
  Supply,
  Turn,
  Village,
  VillageOption,
} from "./types";

/** Live screens poll every 10 s (PLAN.md Phase 7) so pins and stops update without a refresh. */
export const LIVE = 10_000;

export const useStats = (live = true) =>
  useQuery({ queryKey: ["stats"], queryFn: () => api<Stats>("/api/stats"), refetchInterval: live ? LIVE : false });

export const useVillages = () =>
  useQuery({
    queryKey: ["villages"],
    queryFn: async () => (await api<{ villages: Village[] }>("/api/villages")).villages,
    refetchInterval: LIVE,
  });

export const useFields = (filters: { village_id?: string; status?: string; level?: string } = {}) =>
  useQuery({
    queryKey: ["fields", filters],
    queryFn: async () => (await api<{ fields: FieldRow[] }>("/api/fields", { query: filters })).fields,
    refetchInterval: LIVE,
  });

export const useField = (id: string | null) =>
  useQuery({
    queryKey: ["field", id],
    queryFn: () => api<FieldDetail>(`/api/fields/${id}`),
    enabled: !!id,
    refetchInterval: LIVE,
  });

export const useBalers = () =>
  useQuery({ queryKey: ["balers"], queryFn: async () => (await api<{ balers: Baler[] }>("/api/balers")).balers });

export const useBuyers = () =>
  useQuery({ queryKey: ["buyers"], queryFn: async () => (await api<{ buyers: Buyer[] }>("/api/buyers")).buyers });

export const useBookings = (date?: string) =>
  useQuery({
    queryKey: ["bookings", date ?? "all"],
    queryFn: async () => (await api<{ bookings: BookingRow[] }>("/api/bookings", { query: { date } })).bookings,
    refetchInterval: LIVE,
  });

export const useAlerts = () =>
  useQuery({ queryKey: ["alerts"], queryFn: async () => (await api<{ alerts: Alert[] }>("/api/alerts")).alerts });

export const useLayer = (name: "firms" | "harvest", enabled: boolean) =>
  useQuery({ queryKey: ["layer", name], queryFn: () => api<Layer>(`/api/layers/${name}`), enabled, staleTime: Infinity });

export function useSendAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (village_id: string) => api<AlertResult>("/api/alerts", { method: "POST", body: { village_id } }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["alerts"] });
      void qc.invalidateQueries({ queryKey: ["sim"] });
    },
  });
}

// ---------------------------------------------------------------- registration + approvals
/** The signed-in user's latest application. Polled while it is under review so approval shows up by itself. */
export const useMyApplication = (enabled: boolean, poll = true) =>
  useQuery({
    queryKey: ["register", "me"],
    queryFn: async () => (await api<{ application: Application | null }>("/api/register/me")).application,
    enabled,
    refetchInterval: poll ? 5000 : false,
  });

export const useVillageSearch = (q: string, enabled: boolean) =>
  useQuery({
    queryKey: ["register", "villages", q],
    queryFn: async () => (await api<{ villages: VillageOption[] }>("/api/register/villages", { query: { q } })).villages,
    enabled,
    staleTime: 60_000,
  });

export function useSubmitApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (form: ApplicationForm) => api<{ application: Application }>("/api/register", { method: "POST", body: form }),
    onSuccess: (data) => qc.setQueryData(["register", "me"], data.application),
  });
}

export const useApplications = (status?: ApplicationStatus) =>
  useQuery({
    queryKey: ["applications", status ?? "all"],
    queryFn: () => api<{ applications: Application[]; pending: number }>("/api/applications", { query: { status } }),
    refetchInterval: LIVE,
  });

export function useReviewApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; action: "approve" } | { id: string; action: "reject"; reason: string }) =>
      api<{ application: Application }>(`/api/applications/${v.id}/${v.action}`, {
        method: "POST",
        body: v.action === "reject" ? { reason: v.reason } : undefined,
      }),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ["applications"] });
      void qc.invalidateQueries({ queryKey: ["balers"] });
      void qc.invalidateQueries({ queryKey: ["buyers"] });
    },
  });
}

export function useSetBalerActive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { baler_id: string; active: boolean }) =>
      api<{ baler: Baler }>(`/api/balers/${v.baler_id}/active`, { method: "POST", body: { active: v.active } }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["balers"] });
      void qc.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

// ---------------------------------------------------------------- buyer
export const useSupply = () =>
  useQuery({ queryKey: ["supply"], queryFn: () => api<Supply>("/api/buyers/me/supply"), refetchInterval: LIVE });

export function useUpdateDemand() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { demand_tonnes: number; price_per_tonne: number; max_radius_km: number }) =>
      api<{ buyer: Buyer }>("/api/buyers/me/demand", { method: "PUT", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["supply"] });
      void qc.invalidateQueries({ queryKey: ["demand-history"] });
    },
  });
}

export const useDemandHistory = () =>
  useQuery({
    queryKey: ["demand-history"],
    queryFn: async () => (await api<{ changes: DemandChange[] }>("/api/buyers/me/demand/history")).changes,
  });

// ---------------------------------------------------------------- operator
export const useOperatorMe = () =>
  useQuery({ queryKey: ["operator", "me"], queryFn: async () => (await api<{ baler: Baler }>("/api/operator/me")).baler });

export const useRoute = (date: string) =>
  useQuery({
    queryKey: ["operator", "route", date],
    queryFn: () => api<Route>("/api/operator/me/route", { query: { date } }),
    refetchInterval: LIVE,
  });

export const useOperatorAlerts = () =>
  useQuery({
    queryKey: ["operator", "alerts"],
    queryFn: async () => (await api<{ alerts: Alert[] }>("/api/operator/me/alerts")).alerts,
    refetchInterval: LIVE,
  });

export const useSchedule = (days = 14) =>
  useQuery({
    queryKey: ["operator", "schedule", days],
    queryFn: async () => (await api<{ days: ScheduleDay[] }>("/api/operator/me/schedule", { query: { days: String(days) } })).days,
    refetchInterval: LIVE,
  });

export const useBalerHistory = () =>
  useQuery({ queryKey: ["operator", "history"], queryFn: () => api<BalerHistory>("/api/operator/me/history") });

export function useUpdateOperator() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { acres_per_day?: number; radius_km?: number; operator_phone?: string; active?: boolean }) =>
      api<{ baler: Baler }>("/api/operator/me", { method: "PUT", body }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["operator"] }),
  });
}

export function useMarkDone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (bookingId: string) => api<{ ok: boolean }>(`/api/bookings/${bookingId}/done`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["operator"] });
      void qc.invalidateQueries({ queryKey: ["bookings"] });
    },
  });
}

// ---------------------------------------------------------------- demo + simulator
export const useDemoClock = (enabled: boolean) =>
  useQuery({ queryKey: ["demo", "clock"], queryFn: () => api<DemoClock>("/api/demo/clock"), enabled, refetchInterval: LIVE });

export function useDemoAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { action: string; village_id?: string; n?: number }) =>
      api<{ action: string; result: Record<string, unknown> }>("/api/demo/simulate", { method: "POST", body }),
    onSuccess: () => void qc.invalidateQueries(),
  });
}

export function useSetClock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (today: string | null) => api<DemoClock>("/api/demo/clock", { method: "PUT", body: { today } }),
    onSuccess: () => void qc.invalidateQueries(),
  });
}

export const useConversation = (phone: string, enabled: boolean) =>
  useQuery({
    queryKey: ["sim", phone],
    queryFn: async () => (await api<{ turns: Turn[] }>("/api/sim/conversation", { query: { phone } })).turns,
    enabled: enabled && /^\+\d{10,15}$/.test(phone),
    refetchInterval: 4000,
  });

export function useSimSend(phone: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { text?: string; button_id?: string; button_title?: string; lat?: number; lng?: number }) =>
      api<{ sent: string[]; turns: Turn[] }>("/api/sim/message", { method: "POST", body: { phone, ...body } }),
    onSuccess: (data) => {
      qc.setQueryData(["sim", phone], data.turns);
      void qc.invalidateQueries({ queryKey: ["fields"] });
      void qc.invalidateQueries({ queryKey: ["villages"] });
      void qc.invalidateQueries({ queryKey: ["stats"] });
      void qc.invalidateQueries({ queryKey: ["bookings"] });
    },
  });
}

export interface InboxRow {
  phone: string;
  name: string | null;
  village_name: string | null;
  last_ts: string;
  last_text: string;
}

export const useSimInbox = (enabled: boolean) =>
  useQuery({
    queryKey: ["sim", "inbox"],
    queryFn: async () => (await api<{ inbox: InboxRow[] }>("/api/sim/inbox")).inbox,
    enabled,
    refetchInterval: 8000,
  });

export function useSimReset(phone: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<{ deleted: number }>("/api/sim/reset", { method: "POST", body: { phone } }),
    onSuccess: () => qc.setQueryData(["sim", phone], []),
  });
}

export const useDevAccounts = (enabled: boolean) =>
  useQuery({ queryKey: ["dev", "accounts"], queryFn: () => api<DevAccounts>("/api/dev/accounts"), enabled, retry: false });
