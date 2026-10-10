# clearsky: demo video script (Team Atherion)

**Length:** 3:30 maximum. **Voice-over pace:** about 150 words a minute (each block fits its slot when read calmly).
**Language:** English narration; the WhatsApp part is spoken in Hindi on camera (add English subtitles).
**Rules for every number on screen:** it comes from the live app or from a cited source. Prices and payouts are **demo prices** and must be called that (CLAUDE.md, PLAN.md).

| # | Section | Time | Length | Who |
|---|---|---|---|---|
| 1 | Team introduction | 0:00 – 0:24 | 24 s | Sanskar, Kamran, Akshay, Anushka |
| 2 | Bridge + 10-second overview film | 0:24 – 0:38 | 14 s | Sanskar, then `introvideo.mp4` |
| 3 | Explainer: problem → idea → how it works → AWS → before/after | 0:38 – 1:28 | 50 s | Presenter + clips 3a–3e |
| 4 | Live demo A: WhatsApp booking in Hindi (on camera) | 1:28 – 2:04 | 36 s | Sanskar |
| 5 | Live demo B: website walkthrough (screen recording) | 2:04 – 2:59 | 55 s | Voice-over **to be written after recording** |
| 6 | Impact: pollution avoided | 2:59 – 3:16 | 17 s | Presenter, on `/impact` |
| 7 | Outro: our goal, thank you | 3:16 – 3:30 | 14 s | Sanskar (team in frame) |

---

## 1. Team introduction · 0:00 – 0:24

Each person on camera (or a face card + name), 5–7 s each. Lower-third: **name · role**.

| Time | Speaker | Line |
|---|---|---|
| 0:00 – 0:07 | **Sanskar Joshi** | "We are Team Atherion. I'm Sanskar: I built the core, the WhatsApp agent and the AWS backend, and deployed it." |
| 0:07 – 0:12 | **Kamran Pathan** | "I'm Kamran. I built the dashboards and the approvals for every role." |
| 0:12 – 0:17 | **Akshay** | "I'm Akshay. I worked on the AI model and on testing the whole system." |
| 0:17 – 0:24 | **Anushka** | "I'm Anushka. I worked on the pollution-impact view and **[confirm: e.g. the emission-factor method behind it]**." |

> Anushka's second topic is a placeholder: put in what she actually worked on before recording.

---

## 2. Bridge + overview film · 0:24 – 0:38

| Time | Screen | Voice |
|---|---|---|
| 0:24 – 0:28 | Sanskar on camera | "Let's take a quick look at what we built." |
| 0:28 – 0:38 | `introvideo.mp4` full screen (10 s: farmer voice note → baler → plant manager → baler driver), its own audio | *(none)* |

---

## 3. Explainer · 0:38 – 1:28 (50 s)

**Layout:** split screen, two 8:9 halves. Left: the presenter. Right: the matching clip from `video/` (no titles on the clips; the presenter says them). The clips are already cut to these exact lengths: `3a-problem.mp4` 12 s, `3b-idea.mp4` 9 s, `3c-how-it-works.mp4` 12 s, `3d-aws.mp4` 11 s, `3e-before-after.mp4` 6 s.

> Presenter: Sanskar by default. For more energy, each member can present their own part (e.g. Anushka the problem, Akshay "how it works", Sanskar AWS); the timings stay the same.

### 3a. The problem · 0:38 – 0:50 (12 s) · clip `3a-problem.mp4`
**Clip shows:** Punjab drawing in (Amritsar, Jalandhar, Ludhiana, Bathinda, Patiala), fields igniting in waves, smoke drifting to Delhi, an AQI meter sliding to "Severe", then the chips *Stubble burning · AQI · Pollution exposure*.
**Voice:** "Every October, after the paddy harvest, farmers get only weeks to sow wheat. Clearing straw is slow and costly, so many burn it, and the smoke drifts all the way to Delhi."

### 3b. The idea · 0:50 – 0:59 (9 s) · clip `3b-idea.mp4`
**Clip shows:** farmer, baler and industry with no link; the clearsky hub connects them; a pickup request, straw and a ₹ payment flow through it.
**Voice:** "That straw isn't waste. Industries buy it as fuel, and balers can collect it. clearsky connects them, and the farmer only needs WhatsApp."

### 3c. How it works · 0:59 – 1:11 (12 s) · clip `3c-how-it-works.mp4`
**Clip shows:** (1) the AI agent turning a Hinglish voice note into name, village, acres and date; (2) the matcher finding the nearest free baler (6 km) and a buyer; (3) the burn-risk gauge swinging to red (**Track**) and a village alert on WhatsApp (**Warn**).
**Voice:** "An AI agent understands Hindi or Punjabi, even voice notes. A matcher books the nearest free baler and the buyer who pays best. And a risk score tracks fields about to burn, and warns them first."

### 3d. Built on AWS · 1:11 – 1:22 (11 s) · clip `3d-aws.mp4`
**Clip shows:** four lanes lighting up in this order: messages (API Gateway, Lambda, SQS), voice (Transcribe, AI agent, Polly), bookings (two requests race for one slot, the DynamoDB transaction lets one win), every hour (EventBridge Scheduler, risk scorer, Burn Risk Radar).
**Voice:** "It runs serverless on AWS: Lambda and SQS take every message, Transcribe and Polly handle Hindi voice, DynamoDB transactions stop double-booking, and EventBridge rescores risk every hour."

### 3e. Before and after · 1:22 – 1:28 (6 s) · clip `3e-before-after.mp4`
**Clip shows:** Before (calls around, waits, burns the field) vs with clearsky (one WhatsApp message, pickup confirmed, straw sold and farmer paid), ending on "Change what happens on the bad days."
**Voice:** "Before: calls, waiting, a fire. After: one message, a pickup, a payment."

---

## 4. Live demo A: WhatsApp booking in Hindi · 1:28 – 2:04 (36 s)

**Setup:** Sanskar on camera holding the phone; the phone's screen recording plays **next to him** (split screen). Use the live number (issue #4) and a phone that is in the WhatsApp test-recipient list.

| Time | Who / screen | Line |
|---|---|---|
| 1:28 – 1:32 | Sanskar to camera | "So let's move to the actual demo of our system." |
| 1:32 – 1:38 | Sanskar opens the clearsky chat (screen recording starts) | "clearsky understands Hindi, Punjabi, Hinglish and English. I'll speak in Hindi." |
| 1:38 – 1:48 | Sanskar holds the mic button and records a voice note | **Hindi (spoken):** "मैं संस्कार जोशी हूँ। मेरी 6 एकड़ धान की कटाई परसों है, और मुझे 4-5 दिन में खेत साफ़ करवाना है। मेरी ज़मीन **[village]** में है।" · *Subtitle:* "I'm Sanskar Joshi. My 6 acres of paddy will be harvested the day after tomorrow, and I need the field cleared within 4–5 days. My land is in [village]." |
| 1:48 – 1:58 | Screen: the agent's reply arrives (text + Hindi voice reply) | Let the reply play for 2–3 s, then Sanskar: "In seconds the AI agent has booked a pickup with the nearest baler, and tells me my estimated payout." |
| 1:58 – 2:04 | Sanskar to camera | "No app, no form, no phone calls. Just one message." |

**Before recording, check:**
- **[village]** must be a village the system knows (the pilot list is in Sangrur district, e.g. **Bhawanigarh**; see `data/seed/villages.json`). A village outside the list makes the agent ask again.
- Say the **harvest date** ("परसों" / "24 तारीख") as above: the agent needs it to book. If it asks a follow-up question anyway, answer it on camera; that shows the conversation.
- The payout is a **demo estimate**: on screen add a small caption "demo prices".
- Rehearse the exact sentence twice with the live number first; if a baler has to accept before the ✅, have Kamran (or a second screen) accept it on the baler dashboard during this scene, or set `AUTO_ACCEPT_DEMO=true` for the recording.

---

## 5. Live demo B: website walkthrough · 2:04 – 2:59 (55 s)

**Screen recording of the live site** (clearsky.akkki.tech), with Sanskar's voice-over. **The voice-over is written after the recording is done.** Planned order and time boxes:

| Time | Screen (planned) | Voice-over |
|---|---|---|
| 2:04 – 2:14 | **Home page**: hero film, live field data, who it's for | *(to be added after recording)* |
| 2:14 – 2:29 | **Super admin**: Burn Risk Radar, a red village → Alert → WhatsApp offer; Bookings (the booking from demo A); Approvals | *(to be added after recording)* |
| 2:29 – 2:44 | **Baler**: request from demo A → Accept → route → **Done** | *(to be added after recording)* |
| 2:44 – 2:59 | **Buyer**: straw on the way, deliveries, demand and price | *(to be added after recording)* |

---

## 6. Impact: pollution avoided · 2:59 – 3:16 (17 s)

**Screen:** the public `/impact` page (and the home page's live cards). Read the numbers **from the screen at recording time**; don't invent any.

| Time | Screen | Voice |
|---|---|---|
| 2:59 – 3:08 | `/impact` counters: acres cleared, tonnes of straw routed | "Every acre we clear is an acre that doesn't burn. In our pilot, that's **[X] acres** and **[Y] tonnes** of straw that went to industry instead of into the air." |
| 3:08 – 3:16 | Impact table / pollution avoided | "That's less smoke in the AQI, and fewer people exposed to it: for every acre we clear, the fire, and the smoke from it, simply never happens." |

> **Pollution avoided in kg (PM2.5 and others)** shows only when the team sets published emission factors with their citation (`EMISSION_FACTORS`, `SETUP_GUIDE.md` §9b). If they are set, add: "…and about **[Z] kg** of PM2.5 avoided, from published emission factors." Do **not** state an AQI number: we don't measure AQI, we prevent fires.

---

## 7. Outro · 3:16 – 3:30 (14 s)

**Screen:** team in frame, then the end card: round clearsky logo, "Straw pickup instead of stubble fires.", `github.com/sanskarjoshiii/clearsky`, `clearsky.akkki.tech`, "Built on AWS · AWS Environmental Hacks 2026", Team Atherion: Sanskar · Kamran · Akshay · Anushka.

| Time | Speaker | Line |
|---|---|---|
| 3:16 – 3:26 | Sanskar | "That's clearsky. Our goal: no farmer should have to choose between sowing on time and clean air. One message, and the fire never starts." |
| 3:26 – 3:30 | All four | "We are Team Atherion. Thank you!" |

---

## Recording checklist

- **Order of real actions:** WhatsApp booking (demo A) → the same booking on the admin Bookings page → baler accepts and marks Done → buyer sees the delivery → `/impact` counters. Recording them in this order makes demo B and the impact numbers show the booking from demo A.
- Before the takes: the deployed stack is up, WhatsApp is on the live number, the test phone is in the recipient list, and the demo clock and data look right (`docs/demo_runbook.md`).
- Captions for the full voice-over and English subtitles for every Hindi line (judges often watch muted). Add "demo prices" wherever a payout or price is on screen.
- Explainer clips: drop `3a`–`3e` back to back on the right half at 0:38; each fades in and out.
- Background music low under the voice-over; the overview film keeps its own audio.
- Export 1920×1080, under 3:30, upload, and put the link in `README.md`.
