---
title: "Balers accept or reject assigned fields (offer → accept/decline → reassign)"
assignee: kamranp03
labels: [feature, backend, dashboard, matching, whatsapp]
---

## Why

Today the matcher **books instantly**:
1. `domain/matching.book_pickup` picks the best baler-day.
2. One DynamoDB transaction reserves capacity, writes a `Booking` with status `CONFIRMED`, and sets the field `BOOKED`.
3. The farmer is told the date and baler at once (`agent/tools.book_pickup`, `agent/rules._booked_text`).

The baler only finds out from their route. Real custom-hiring centres need to say **yes or no** (machine breakdown, a field too far off-road, already committed elsewhere). A silent no-show means a field that may be burnt. This is exactly what ClearSky exists to prevent.

## Proposed behaviour

The matcher makes an **offer** to the best baler. The baler **accepts** (booking confirmed, farmer told) or **declines** with a reason (the matcher offers the field to the next-best baler). If the baler doesn't answer within an SLA, the offer **expires** and is re-offered. If nobody can take it before the sowing deadline, the field shows up on the officer's risk radar and the farmer is told an officer will follow up (same as today's `no_baler_capacity`).

### Booking lifecycle (replaces `CONFIRMED → DONE | CANCELLED`)
```
OFFERED ──accept──► CONFIRMED ──done──► DONE
   │                    └──cancel──► CANCELLED
   ├──decline──► DECLINED   (→ matcher re-offers to the next baler)
   └──timeout──► EXPIRED    (→ matcher re-offers)
```
- `Field.status` stays `BOOKED` while an offer is open. Keeping one status avoids touching the risk/alert code paths, and the radar shows it as booked. Add `Field.booking_state = offered | confirmed` for the UI.
- Capacity (`BalerDays.booked_acres`) is **reserved at offer time** so two offers can't overbook the same day. It is released on decline/expire using the same transaction pattern as `cancel_booking`.
- `Field.declined_balers: list[str]`: `find_candidates` skips these balers for this field, so a decline never bounces back to the same baler.

### Settings (`config.py`)
- `OFFER_SLA_MINUTES` (default 120)
- `OFFER_MAX_ATTEMPTS` (default 3; after that, escalate to the officer)
- `AUTO_ACCEPT_DEMO` (default false; true keeps today's instant behaviour for demo-mode recordings)

### Farmer messages (WhatsApp, via `channels/notify.py`)
- On offer: "Aapki request {date} ke liye baler ko bhej di hai. Confirm hote hi batayenge." The current immediate "✅ … saaf hoga" moves to acceptance. Update `agent/rules.py` (`booked` text, and the ✅/❌ markers the draft logic relies on) and the LLM prompt (`agent/prompts.py`: "never say the pickup is confirmed until the tool says confirmed").
- On accept: "✅ {name} ji, {date} ko baler {operator} aayega." (new template `booking_confirmed`).
- On reassignment to a different date: tell the farmer the new date (new template `booking_changed`).
- Add both templates to `channels/templates.py` and `docs/whatsapp_templates.md` (they need Meta approval; outside the 24-hour window only approved templates can be sent).

### Baler dashboard (`/baler/requests` from the routing issue; today's `/operator` until then)
- **Requests** list: farmer name, village, acres, harvest date, proposed day, distance from base, a countdown to expiry, a map preview.
- Big **Accept · स्वीकार** and **Decline · मना करें** buttons. Decline opens a reason picker (Machine not available · Too far · Already full that day · Other + note).
- Today's route (`/api/operator/me/route`) shows only `CONFIRMED`/`DONE` stops. The stop order is recomputed on accept (`recompute_stop_order`).

### Admin
- Bookings table: status chips for Offered / Declined / Expired.
- Radar KPI "Offers waiting" and a field-drawer timeline of offers and declines (who, when, reason).
- Optional "Reassign" action for the officer.

### API (`handlers/api.py`)
| Method | Path | Who | Behaviour |
|---|---|---|---|
| GET | `/api/operator/me/requests` | operator | Open offers for the token's `baler_id` |
| POST | `/api/bookings/{id}/accept` | operator (own) | Conditional `status = OFFERED` and `expires_at > now` → `CONFIRMED`; notify the farmer |
| POST | `/api/bookings/{id}/decline` `{reason, note?}` | operator (own) | → `DECLINED`, release capacity, add to `declined_balers`, re-offer |
| POST | `/api/bookings/{id}/done` | operator (own) | Unchanged, but only from `CONFIRMED` |

### Expiry job
New Lambda `handlers/offers_job.py` on a ScheduleV2 `rate(15 minutes)` in `infra/template.yaml` (same pattern as `RiskJobFunction`). It finds `OFFERED` bookings past `expires_at` (new GSI `status-index` on `Bookings`, or a filtered scan at demo scale), marks them `EXPIRED`, releases capacity and re-offers.

### Data model changes
- `Booking`: `status` gains `OFFERED`/`DECLINED`/`EXPIRED`; new fields `offered_at`, `expires_at`, `responded_at`, `decline_reason`, `attempt`.
- `Field`: `declined_balers`, `booking_state`.
- Update `models/enums.py`, `models/entities.py`, `repo/schema.py` + `infra/template.yaml` (if a GSI is added), and `IMPLEMENTATION.md` §3.3 (state machines) and §4 (matching).

## Edge cases
- Accept and expiry racing at the same moment: both are conditional updates on `status = OFFERED`, so only one wins.
- Baler turns **Off duty** with open offers: their offers expire at once and are re-offered.
- Farmer cancels or reschedules while an offer is open: cancel the offer (release capacity) before rebooking. `matching.reschedule` already cancels first; extend it to offers.
- Offer near the deadline: if the remaining window is shorter than the SLA, shorten `expires_at` to the window, or skip the offer stage when `AUTO_ACCEPT_DEMO`.
- Officer alert flow (`alertbook:` button) creates an offer too. The alert DoD ("tap HAAN → GREEN") stays true because the field becomes `BOOKED` on offer.
- Seed pre-bookings stay `CONFIRMED` (`seed/load.py`).
- Reminders (`handlers/reminders.py`) only send "baler aayega" for `CONFIRMED`.

## Acceptance criteria
- [ ] A new booking creates an **offer**. The baler sees it, accepts it, and the farmer gets the confirmation on WhatsApp (simulator locally).
- [ ] Decline with reason → the next-best baler gets the offer; the declining baler never gets that field again.
- [ ] Offers expire after `OFFER_SLA_MINUTES` and are re-offered; after `OFFER_MAX_ATTEMPTS` the field is escalated (radar shows "no baler accepted" in the risk reasons; the farmer gets the follow-up message).
- [ ] No overbooking under concurrent offers/accepts (extend `tests/test_matching.py` with the stale-read pattern already used there).
- [ ] Route, stop order, stats (`domain/stats.py`) and buyer supply only count `CONFIRMED`/`DONE`.
- [ ] Rules bot and LLM agent wording updated; `tests/test_rules_bot.py` and `tests/test_agent_flow.py` updated.
- [ ] Playwright: farmer books → baler declines → second baler accepts → farmer sees confirmation.
- [ ] Docs: `IMPLEMENTATION.md` §3.3/§4/§8/§9, `docs/whatsapp_templates.md` (2 new templates), `docs/demo_runbook.md`, `CONTEXT.md`.

## Files you'll touch
`backend/src/clearsky/domain/matching.py` (offer/accept/decline/expire), `models/*`, `agent/{tools.py,rules.py,prompts.py}`, `channels/templates.py`, `handlers/{api.py,reminders.py}`, new `handlers/offers_job.py`, `infra/template.yaml`, tests; `dashboard` baler pages and admin bookings/drawer.
