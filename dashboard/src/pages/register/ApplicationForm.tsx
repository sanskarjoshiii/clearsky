import { Check, Search } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useSubmitApplication, useVillageSearch } from "../../api/hooks";
import type { Application, ApplicationForm as FormBody, Buyer, VillageOption } from "../../api/types";
import { Button, ErrorNote, Field, Input } from "../../components/ui";

const BUYER_TYPES: { value: Buyer["type"]; label: string }[] = [
  { value: "pellet", label: "Pellet plant" },
  { value: "cbg", label: "CBG plant" },
  { value: "boiler", label: "Industrial boiler" },
  { value: "biomass_power", label: "Biomass power" },
];

const SELECT = "h-9 w-full rounded-[var(--radius-control)] border border-line-strong bg-canvas px-2 text-sm text-ink focus:border-ink focus:outline-none";

/** Village search with the same fuzzy matching the farmer agent uses (any spelling, Hindi or Punjabi script). */
function VillagePicker({ value, onChange }: { value: VillageOption | null; onChange: (v: VillageOption | null) => void }) {
  const [text, setText] = useState(value?.name ?? "");
  const [query, setQuery] = useState("");
  useEffect(() => {
    const t = window.setTimeout(() => setQuery(text.trim()), 250);
    return () => window.clearTimeout(t);
  }, [text]);
  const searching = query.length >= 2 && query !== value?.name;
  const results = useVillageSearch(query, searching);
  return (
    <div>
      <div className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-faint" />
        <Input
          aria-label="Village"
          className="pl-8"
          placeholder="Type your village or town"
          value={text}
          required
          onChange={(e) => {
            setText(e.target.value);
            if (value) onChange(null);
          }}
        />
        {value ? <Check className="absolute right-2.5 top-1/2 size-4 -translate-y-1/2 text-ink" aria-label="Village selected" /> : null}
      </div>
      {searching ? (
        <ul className="mt-1 overflow-hidden rounded-[var(--radius-control)] border border-line" aria-label="Matching villages">
          {results.isLoading ? <li className="px-3 py-2 text-[13px] text-faint">Searching…</li> : null}
          {results.data?.length === 0 ? <li className="px-3 py-2 text-[13px] text-muted">No village found. Try another spelling.</li> : null}
          {(results.data ?? []).map((v) => (
            <li key={v.village_id} className="border-b border-line last:border-0">
              <button
                type="button"
                className="flex min-h-10 w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-hover"
                onClick={() => {
                  onChange(v);
                  setText(v.name);
                }}
              >
                <span className="font-medium text-ink">{v.name}</span>
                <span className="text-xs text-faint">{v.block}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

const num = (v: string): number | undefined => (v.trim() === "" ? undefined : Number(v));

/** The baler / buyer application. `previous` pre-fills the form when a rejected applicant edits and resubmits. */
export function ApplicationForm({ role, previous, onSubmitted }: { role: "operator" | "buyer"; previous?: Application | null; onSubmitted: () => void }) {
  const submit = useSubmitApplication();
  const p = previous?.role === role ? previous : null;
  const [village, setVillage] = useState<VillageOption | null>(p ? { village_id: p.village_id, name: p.village_name ?? p.village_id, block: "" } : null);
  const [f, setF] = useState({
    name: p?.name ?? "",
    phone: p?.phone ?? "+91",
    org_name: p?.org_name ?? "",
    acres_per_day: String(p?.acres_per_day ?? ""),
    radius_km: String(p?.radius_km ?? ""),
    machine_details: p?.machine_details ?? "",
    type: (p?.type ?? "pellet") as Buyer["type"],
    price_per_tonne: String(p?.price_per_tonne ?? ""),
    demand_tonnes: String(p?.demand_tonnes ?? ""),
    max_radius_km: String(p?.max_radius_km ?? ""),
  });
  const [error, setError] = useState<unknown>(null);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const baler = role === "operator";

  const send = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!village) {
      setError(new Error("Pick your village from the list."));
      return;
    }
    const common = { role, name: f.name.trim(), phone: f.phone.replace(/[\s-]/g, ""), org_name: f.org_name.trim(), village_id: village.village_id };
    const body: FormBody = baler
      ? { ...common, acres_per_day: num(f.acres_per_day), radius_km: num(f.radius_km), machine_details: f.machine_details.trim() }
      : { ...common, type: f.type, price_per_tonne: num(f.price_per_tonne), demand_tonnes: num(f.demand_tonnes), max_radius_km: num(f.max_radius_km) };
    submit.mutate(body, { onSuccess: onSubmitted, onError: setError });
  };

  return (
    <form className="space-y-4" onSubmit={send}>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={baler ? "Your name · आपका नाम" : "Your name"}>
          <Input required minLength={2} maxLength={80} autoComplete="name" value={f.name} onChange={set("name")} />
        </Field>
        <Field label={baler ? "Mobile number · मोबाइल" : "Mobile number"} hint="With country code, e.g. +9198…">
          <Input required type="tel" inputMode="tel" pattern="^\+\d[\d\s-]{9,16}$" autoComplete="tel" value={f.phone} onChange={set("phone")} />
        </Field>
      </div>
      <Field label={baler ? "Custom hiring centre (CHC) name · केंद्र का नाम" : "Company / plant name"}>
        <Input required minLength={2} maxLength={120} autoComplete="organization" value={f.org_name} onChange={set("org_name")} />
      </Field>
      <Field label={baler ? "Base village · गाँव" : "Plant location (nearest village or town)"}>
        <VillagePicker value={village} onChange={setVillage} />
      </Field>

      {baler ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Acres per day · एकड़ प्रति दिन" hint="How much one baler clears in a day (1–60)">
              <Input required type="number" min={1} max={60} step="1" inputMode="numeric" value={f.acres_per_day} onChange={set("acres_per_day")} />
            </Field>
            <Field label="Working radius (km) · कितनी दूर तक" hint="How far from your base you travel (5–50)">
              <Input required type="number" min={5} max={50} step="1" inputMode="numeric" value={f.radius_km} onChange={set("radius_km")} />
            </Field>
          </div>
          <Field label="Machines · मशीनें" hint="Optional: baler type, rake, tractor">
            <Input maxLength={500} value={f.machine_details} onChange={set("machine_details")} />
          </Field>
        </>
      ) : (
        <>
          <Field label="Plant type">
            <select className={SELECT} value={f.type} onChange={(e) => setF({ ...f, type: e.target.value as Buyer["type"] })}>
              {BUYER_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </Field>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Price (₹ per tonne)">
              <Input required type="number" min={1} max={100000} step="1" inputMode="numeric" value={f.price_per_tonne} onChange={set("price_per_tonne")} />
            </Field>
            <Field label="Season demand (tonnes)">
              <Input required type="number" min={1} step="1" inputMode="numeric" value={f.demand_tonnes} onChange={set("demand_tonnes")} />
            </Field>
            <Field label="Collection radius (km)">
              <Input required type="number" min={1} max={300} step="1" inputMode="numeric" value={f.max_radius_km} onChange={set("max_radius_km")} />
            </Field>
          </div>
        </>
      )}

      {error ? <ErrorNote error={error} /> : null}
      <Button variant="primary" size="lg" type="submit" className="w-full" loading={submit.isPending}>
        Send for approval{baler ? " · भेजें" : ""}
      </Button>
      <p className="text-xs text-faint">The district officer reviews every application. You can use your dashboard as soon as it is approved.</p>
    </form>
  );
}
