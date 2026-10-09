import { ChevronLeft, ChevronRight, FlaskConical, Play, RotateCcw } from "lucide-react";
import { useState } from "react";
import { useDemoAction, useDemoClock, useSetClock, useVillages } from "../../../api/hooks";
import { PageBody, useSimPanel, TopBar } from "../../../components/Shell";
import { Button, Card, ConfirmDialog, ErrorNote, Field, Input, PageTitle, Skeleton, useToast } from "../../../components/ui";
import { addDays, fmtDayLong } from "../../../lib/format";

const RUNBOOK = [
  "Reset demo data (clock goes to 20 Oct).",
  "Open the farmer simulator and send the Hinglish sample: the agent books 25 Oct.",
  "Sign in as that baler's operator in another window: the new stop is on the route; tap Done.",
  "Move the clock to 26 Oct, then run a harvest wave: fresh fields turn amber/red.",
  "On the radar, Alert the red village: the simulator shows the WhatsApp offer.",
  "Tap \"HAAN, book karo\" in the simulator: the pin turns green within 10 s.",
  "Open Impact for the closing counters.",
];

export function Demo() {
  const clock = useDemoClock(true);
  const setClock = useSetClock();
  const action = useDemoAction();
  const villages = useVillages();
  const toast = useToast();
  const { setOpen } = useSimPanel();
  const [village, setVillage] = useState("");
  const [n, setN] = useState(5);
  const [confirmReset, setConfirmReset] = useState(false);
  const today = clock.data?.today;

  const run = (body: { action: string; village_id?: string; n?: number }, done: string) =>
    action.mutate(body, {
      onSuccess: (r) => toast(`${done}${r.result && "fields" in r.result ? ` (${(r.result.fields as string[]).length} fields)` : ""}`),
      onError: (e) => toast(e.message, "error"),
    });

  return (
    <>
      <TopBar crumbs={[{ label: "Demo", icon: FlaskConical }, { label: "Controls" }]} />
      <PageBody>
        <PageTitle sub="Replay a whole season in minutes (DEMO_MODE only). Everything here works on demo data; nothing is sent to real phones in simulator mode.">
          Demo controls
        </PageTitle>
        {clock.error ? <ErrorNote error={clock.error} /> : null}
        <div className="grid gap-6 md:grid-cols-2">
          <Card title="Demo clock">
            {today ? (
              <>
                <div className="text-[13px] text-muted">{clock.data?.simulated ? "Simulated today" : "Real today (IST)"}</div>
                <div className="mt-1 text-[30px] font-semibold tracking-[var(--tracking-display)]">{fmtDayLong(today)}</div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button onClick={() => setClock.mutate(addDays(today, -1))} loading={setClock.isPending}>
                    <ChevronLeft className="size-4" /> Day
                  </Button>
                  <Button onClick={() => setClock.mutate(addDays(today, 1))} loading={setClock.isPending}>
                    Day <ChevronRight className="size-4" />
                  </Button>
                  <Input type="date" value={today} onChange={(e) => e.target.value && setClock.mutate(e.target.value)} className="w-auto" aria-label="Set demo date" />
                  <Button variant="ghost" onClick={() => setClock.mutate(null)}>
                    Use real date
                  </Button>
                </div>
              </>
            ) : (
              <Skeleton className="h-24" />
            )}
          </Card>

          <Card title="Season events">
            <div className="grid gap-3 sm:grid-cols-[1fr_90px]">
              <Field label="Harvest wave in" hint="Default: the village with the highest fire history">
                <select
                  value={village}
                  onChange={(e) => setVillage(e.target.value)}
                  className="h-9 w-full rounded-[var(--radius-control)] border border-line-strong bg-canvas px-2 text-sm"
                >
                  <option value="">Auto</option>
                  {(villages.data ?? []).map((v) => (
                    <option key={v.village_id} value={v.village_id}>
                      {v.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Fields">
                <Input type="number" min={1} max={50} value={n} onChange={(e) => setN(Number(e.target.value) || 1)} />
              </Field>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="primary" loading={action.isPending} onClick={() => run({ action: "harvest_wave", village_id: village || undefined, n }, "Harvest wave done")}>
                <Play className="size-4" /> Harvest wave
              </Button>
              <Button onClick={() => run({ action: "run_risk" }, "Risk recomputed")}>Run risk now</Button>
              <Button onClick={() => run({ action: "run_reminders" }, "Reminders sent")}>Send tomorrow's reminders</Button>
              <Button variant="ghost" onClick={() => setConfirmReset(true)}>
                <RotateCcw className="size-4" /> Reset
              </Button>
            </div>
          </Card>
        </div>

        <Card title="Demo runbook" actions={<Button size="sm" variant="agent" onClick={() => setOpen(true)}>Open farmer simulator</Button>}>
          <ol className="space-y-2.5">
            {RUNBOOK.map((step, i) => (
              <li key={step} className="flex gap-3 text-sm text-ink-2">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-sunken text-xs font-medium tabular text-ink">{i + 1}</span>
                {step}
              </li>
            ))}
          </ol>
        </Card>
      </PageBody>
      <ConfirmDialog
        open={confirmReset}
        title="Reset demo data?"
        confirmLabel="Reset"
        busy={action.isPending}
        onClose={() => setConfirmReset(false)}
        onConfirm={() =>
          action.mutate(
            { action: "reset" },
            {
              onSuccess: () => {
                setConfirmReset(false);
                toast("Demo data reloaded; clock set to 20 Oct");
              },
              onError: (e) => toast(e.message, "error"),
            },
          )
        }
      >
        Deletes every booking, conversation and alert in this environment's tables and reloads the seed. Use it only on the demo stack.
      </ConfirmDialog>
    </>
  );
}
