import { LogOut, Minus, Plus } from "lucide-react";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useOperatorMe, useUpdateOperator } from "../../../api/hooks";
import { useAuth } from "../../../auth/AuthProvider";
import { Button, Card, ErrorNote, Field, Input, Skeleton, Toggle, useToast } from "../../../components/ui";
import { fmtNum } from "../../../lib/format";
import { BalerPage } from "../Layout";

const STEP = "flex size-11 shrink-0 items-center justify-center rounded-[var(--radius-control)] border border-line-strong text-ink hover:bg-hover disabled:text-faint";

function Stepper({
  label,
  value,
  unit,
  min,
  max,
  step = 1,
  busy,
  onChange,
}: {
  label: string;
  value: number;
  unit: string;
  min: number;
  max: number;
  step?: number;
  busy: boolean;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line py-3 last:border-0">
      <span className="text-sm text-ink-2">{label}</span>
      <div className="flex items-center gap-2">
        <button className={STEP} aria-label={`Less: ${label}`} disabled={busy || value - step < min} onClick={() => onChange(value - step)}>
          <Minus className="size-4" />
        </button>
        <span className="min-w-[76px] text-center text-[15px] font-medium tabular">
          {fmtNum(value)} {unit}
        </span>
        <button className={STEP} aria-label={`More: ${label}`} disabled={busy || value + step > max} onClick={() => onChange(value + step)}>
          <Plus className="size-4" />
        </button>
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line py-2.5 text-sm last:border-0">
      <span className="text-muted">{label}</span>
      <span className="text-right text-ink">{children}</span>
    </div>
  );
}

/** Machine capacity, working radius, availability and contact number. Changes affect new bookings only. */
export function Profile() {
  const me = useOperatorMe();
  const update = useUpdateOperator();
  const toast = useToast();
  const { signOut } = useAuth();
  const baler = me.data;
  const [phone, setPhone] = useState("");
  useEffect(() => setPhone(baler?.operator_phone ?? ""), [baler?.operator_phone]);

  const save = (body: Parameters<typeof update.mutate>[0], done?: string) =>
    update.mutate(body, { onSuccess: () => done && toast(done), onError: (e) => toast(e.message, "error") });
  const savePhone = (e: FormEvent) => {
    e.preventDefault();
    save({ operator_phone: phone.trim() }, "Phone number saved");
  };

  return (
    <BalerPage>
      <h1 className="text-[22px] font-semibold tracking-[var(--tracking-display)]">Profile · प्रोफ़ाइल</h1>
      {me.error ? <ErrorNote error={me.error} onRetry={() => void me.refetch()} /> : null}
      {me.isLoading ? <Skeleton className="h-64" /> : null}
      {baler ? (
        <>
          <Card title="Baler">
            <Row label="Operator">{baler.operator_name}</Row>
            <Row label="Custom hiring centre">{baler.chc_name || "–"}</Row>
            <Row label="Base village">{baler.base_village_name ?? baler.base_village_id}</Row>
            <Row label="Baler id">
              <span className="tabular">{baler.baler_id}</span>
            </Row>
          </Card>

          <Card title="Work settings · काम">
            <div className="flex min-h-11 items-center justify-between gap-3 border-b border-line pb-3">
              <span className="text-sm text-ink-2">{baler.active ? "Available for new bookings · उपलब्ध" : "Off duty · छुट्टी"}</span>
              <Toggle checked={baler.active} label="Available for new bookings" disabled={update.isPending} onChange={(v) => save({ active: v })} />
            </div>
            <Stepper label="Acres per day · एकड़/दिन" value={baler.acres_per_day} unit="ac" min={1} max={60} busy={update.isPending} onChange={(v) => save({ acres_per_day: v })} />
            <Stepper label="Working radius · दूरी" value={baler.radius_km} unit="km" min={5} max={50} step={5} busy={update.isPending} onChange={(v) => save({ radius_km: v })} />
            <p className="pt-3 text-xs text-faint">New bookings use these values. Stops you already have stay as they are.</p>
          </Card>

          <Card title="Contact number · फ़ोन">
            <form className="space-y-3" onSubmit={savePhone}>
              <Field label="Phone (with country code)" hint="Shown to the admin and to farmers on your route. clearsky never sends you WhatsApp messages.">
                <Input className="h-11!" type="tel" inputMode="tel" placeholder="+91…" pattern="^\+\d{10,15}$" required value={phone} onChange={(e) => setPhone(e.target.value)} />
              </Field>
              <Button variant="primary" size="lg" type="submit" className="w-full" loading={update.isPending} disabled={phone.trim() === (baler.operator_phone ?? "")}>
                Save number
              </Button>
            </form>
          </Card>

          <Button size="lg" className="w-full" onClick={() => void signOut()}>
            <LogOut className="size-4" /> Sign out
          </Button>
        </>
      ) : null}
    </BalerPage>
  );
}
