import { ArrowUp, MapPin, RotateCcw, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useConversation, useSimReset, useSimSend } from "../api/hooks";
import type { Turn } from "../api/types";
import { fmtTime } from "../lib/format";
import { cx, IconButton, useToast } from "./ui";

// A placeholder number inside the seed's synthetic range: the simulator never sends real messages.
const DEFAULT_PHONE = "+919999900999";

const SAMPLES: { label: string; text: string }[] = [
  { label: "Hinglish", text: "Mera 8 acre dhaan 24 tareekh ko katega, Bhawanigarh. Naam Gurpreet." },
  { label: "हिन्दी", text: "मेरा नाम हरप्रीत है, सुनाम, 6 एकड़, 25 तारीख" },
  { label: "ਪੰਜਾਬੀ", text: "ਮੇਰਾ ਨਾਂ ਹਰਜੀਤ, ਪਿੰਡ ਧੂਰੀ, 5 ਏਕੜ, 23 ਤਾਰੀਖ" },
  { label: "English", text: "My name is Aman, village Dirba, 10 acres, harvest on 26 Oct" },
  { label: "Status", text: "kab aayega baler?" },
  { label: "Cancel", text: "booking cancel karo" },
];

function Bubble({ turn, onButton, busy }: { turn: Turn; onButton: (id: string, title: string) => void; busy: boolean }) {
  if (turn.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-[var(--radius-card)] border border-line bg-canvas px-3.5 py-2.5 text-[14px] leading-relaxed text-ink">
          {turn.kind === "button" ? <span className="mr-1 text-faint">▸</span> : null}
          {turn.text}
          <div className="mt-1 text-right text-[11px] text-faint">{fmtTime(turn.ts)}</div>
        </div>
      </div>
    );
  }
  return (
    <div className="max-w-[92%]">
      <div className="mb-1 flex items-center gap-1.5 text-[11px] font-medium text-agent">
        <Sparkles className="size-3" /> ClearSky agent
        {turn.kind === "template" || turn.kind === "buttons" ? <span className="text-faint">· proactive</span> : null}
        <span className="text-faint">· {fmtTime(turn.ts)}</span>
      </div>
      <div className="whitespace-pre-wrap text-[14px] leading-relaxed text-ink">{turn.text}</div>
      {turn.media_url ? <audio className="mt-2 h-8 w-full" controls src={turn.media_url} /> : null}
      {turn.buttons.length ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {turn.buttons.map((b) => (
            <button
              key={b.id}
              disabled={busy}
              onClick={() => onButton(b.id, b.title)}
              className="h-8 rounded-full border border-agent-line bg-agent-soft px-3 text-[13px] font-medium text-agent-strong hover:border-agent disabled:opacity-50"
            >
              {b.title}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

/** WhatsApp farmer simulator (WA_MODE=simulator): the same processor path a real message takes. */
export function Simulator({ onClose }: { onClose: () => void }) {
  const [phone, setPhone] = useState<string>(() => {
    try {
      return localStorage.getItem("clearsky.simPhone") || DEFAULT_PHONE;
    } catch {
      return DEFAULT_PHONE;
    }
  });
  const [draft, setDraft] = useState("");
  const valid = /^\+\d{10,15}$/.test(phone);
  const convo = useConversation(phone, valid);
  const send = useSimSend(phone);
  const reset = useSimReset(phone);
  const toast = useToast();
  const scroller = useRef<HTMLDivElement>(null);
  const turns = convo.data ?? [];

  useEffect(() => {
    try {
      if (valid) localStorage.setItem("clearsky.simPhone", phone);
    } catch {
      /* ignore */
    }
  }, [phone, valid]);
  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [turns.length, send.isPending]);

  const submit = (text: string) => {
    const t = text.trim();
    if (!t || !valid || send.isPending) return;
    setDraft("");
    send.mutate({ text: t }, { onError: (e) => toast(e.message, "error") });
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex h-[52px] shrink-0 items-center gap-2 border-b border-line px-4">
        <span className="text-[15px] font-medium tracking-[var(--tracking-title)]">Farmer on WhatsApp</span>
        <span className="rounded-full bg-agent-soft px-2 py-0.5 text-[11px] font-medium text-agent-strong">simulator</span>
        <div className="ml-auto flex items-center">
          <IconButton
            label="Clear this conversation"
            onClick={() => reset.mutate(undefined, { onError: (e) => toast(e.message, "error") })}
            disabled={!valid || reset.isPending}
          >
            <RotateCcw className="size-4" />
          </IconButton>
          <IconButton label="Close simulator" onClick={onClose}>
            <X className="size-4" />
          </IconButton>
        </div>
      </header>

      <div className="flex items-center gap-2 border-b border-line px-4 py-2 text-[13px]">
        <span className="text-muted">From</span>
        <input
          value={phone}
          onChange={(e) => setPhone(e.target.value.replace(/[^\d+]/g, ""))}
          className={cx("h-7 flex-1 rounded-[6px] border bg-canvas px-2 tabular text-[13px] focus:outline-none", valid ? "border-line" : "border-risk-line")}
          aria-label="Farmer phone number"
        />
      </div>

      <div ref={scroller} className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {turns.length === 0 && !convo.isLoading ? (
          <div className="rounded-[var(--radius-card)] border border-dashed border-agent-line bg-agent-soft/40 p-4 text-[13px] text-ink-2">
            Type as a farmer would on WhatsApp, or tap a sample. Messages go through the real webhook processor and
            farmer agent; nothing is sent to a phone in simulator mode.
          </div>
        ) : null}
        {turns.map((t) => (
          <Bubble
            key={t.ts}
            turn={t}
            busy={send.isPending}
            onButton={(id, title) => send.mutate({ button_id: id, button_title: title }, { onError: (e) => toast(e.message, "error") })}
          />
        ))}
        {send.isPending ? <div className="text-[13px] text-agent">ClearSky agent is typing…</div> : null}
      </div>

      <div className="shrink-0 px-3 pb-3">
        <div className="mb-2 flex gap-1.5 overflow-x-auto pb-1">
          {SAMPLES.map((s) => (
            <button
              key={s.label}
              onClick={() => submit(s.text)}
              disabled={send.isPending || !valid}
              className="h-7 shrink-0 rounded-full border border-line px-2.5 text-[12px] text-ink-2 hover:bg-hover disabled:opacity-50"
              title={s.text}
            >
              {s.label}
            </button>
          ))}
        </div>
        <form
          className="rounded-[12px] border border-agent-line bg-canvas p-2 focus-within:border-agent"
          onSubmit={(e) => {
            e.preventDefault();
            submit(draft);
          }}
        >
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit(draft);
              }
            }}
            rows={2}
            placeholder="Message as the farmer… (Hindi, Punjabi, Hinglish or English)"
            className="block w-full resize-none bg-transparent px-1.5 py-1 text-[14px] placeholder:text-faint focus:outline-none"
            aria-label="Farmer message"
          />
          <div className="flex items-center justify-between">
            <button
              type="button"
              title="Share location (Bhawanigarh area)"
              aria-label="Share location"
              disabled={!valid || send.isPending}
              onClick={() => send.mutate({ lat: 30.27, lng: 76.05 }, { onError: (e) => toast(e.message, "error") })}
              className="flex size-8 items-center justify-center rounded-full border border-line text-muted hover:text-ink disabled:opacity-50"
            >
              <MapPin className="size-4" />
            </button>
            <button
              type="submit"
              aria-label="Send"
              disabled={!draft.trim() || !valid || send.isPending}
              className="flex size-8 items-center justify-center rounded-full bg-ink text-canvas disabled:bg-faint"
            >
              <ArrowUp className="size-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
