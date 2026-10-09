# Demo runbook (3-minute video)

The exact clicks and messages for the recording. Run it **three times in a row without fixes** before recording (PLAN.md Phase 9).

Works the same locally (`make dev` + `make dashboard`) and on the deployed stack. With `WA_MODE=simulator` the farmer is the dashboard's **Farmer on WhatsApp** panel; with `WA_MODE=cloud` the farmer is a real team phone (a verified test number).

> **Fire history:** red pins need the FIRMS layer (SETUP_GUIDE §5). Without it, the radar can show at most amber, because the risk formula is driven by urgency + fire history + baler capacity.

## Windows to open

1. **Admin** (district officer): `/admin?sim=1` (radar + farmer panel). Deployed: sign in as the officer.
2. **Baler**: a second browser window (or phone) at `/baler`, signed in as the baler who gets the booking.
3. **Impact**: `/impact` (public, no sign-in).

## Sequence

| # | Where | Action | What the viewer sees |
|---|---|---|---|
| 1 | Admin → Demo controls | **Reset** → confirm | Demo day = 20 Oct, fresh seed, radar mostly green |
| 2 | Farmer panel | Send `Mera 8 acre dhaan 24 tareekh ko katega, Bhawanigarh. Naam Gurpreet.` (or a Hindi voice note on a real phone) | Agent replies in Hinglish: "✅ Gurpreet ji, 8 acre ka khet 25 Oct ko saaf hoga…" (plus a Hindi voice reply on a real phone with Polly) |
| 3 | Admin → Bookings → All | Find Gurpreet's row | Booked on 25 Oct with a named baler and buyer |
| 4 | Baler window | Sign in as that baler → **Next stops: 25 Oct** | Gurpreet is a numbered stop on the route map |
| 5 | Baler window | **Done · हो गया** → confirm | Stop turns green; farmer panel shows "✅ … aapka khet aaj saaf ho gaya" |
| 6 | Admin → Demo controls | Clock **Day →** to 26 Oct, then **Harvest wave** (Auto) | A high-fire-history village fills with amber/red rings |
| 7 | Admin → Radar | Click that village → **Alert** → **Send WhatsApp offer** | Toast: "Offer sent to N farmers · M balers flagged"; baler window shows the admin-alert banner |
| 8 | Farmer panel | Pick an alerted farmer from the panel's **Inbox** list (or use the real phone that got the alert); tap **HAAN, book karo** | "✅ … khet … ko saaf hoga"; within 10 s the pin turns into a solid green dot |
| 9 | Impact | Show counters | Acres booked/cleared, tonnes routed, "saved after alert" ≥ 1 |

## Before recording

- `make test` and `make e2e` green; DLQ empty; no errors in CloudWatch (deployed).
- Browser zoom 100 %, window 1440×900, notifications off.
- Clear the farmer panel (↺) between takes.
- For the video's real-phone scene use a team phone in the WhatsApp test-recipient list.
