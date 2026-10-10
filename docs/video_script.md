# clearsky: 3-minute video script

**Length:** 3:00 exactly. **Voice-over pace:** about 150 words a minute (each block below fits its slot when read calmly).
**Language:** English voice-over; the WhatsApp bot speaks Hinglish/Hindi on screen (add English subtitles under bot messages).
**Rule:** every number shown on screen comes from the live app or from a cited source. No made-up statistics (see "Fill in before recording").

| # | Section | Time | Length |
|---|---|---|---|
| 1 | Opening film (`introvideo.mp4`) | 0:00 – 0:10 | 10 s |
| 2 | Team | 0:10 – 0:25 | 15 s |
| 3 | Explainer: problem → solution → how it works → AWS → before/after | 0:25 – 1:15 | 50 s |
| 4 | Live demo: WhatsApp → baler → buyer → admin | 1:15 – 2:45 | 90 s |
| 5 | Outro | 2:45 – 3:00 | 15 s |

---

## 1. Opening film · 0:00 – 0:10

Use `introvideo.mp4` as is (farmer sends a voice note → baler bales the field → plant manager gets the straw → baler driver confirms).

| Time | Screen | Voice-over |
|---|---|---|
| 0:00 – 0:08 | Intro film, original audio | *(none, let the film speak)* |
| 0:08 – 0:10 | Last frame fades to white; the round **clearsky** logo grows in the centre, tagline under it: **"Straw pickup instead of stubble fires."** | *(none)* |

---

## 2. Team · 0:10 – 0:25

Four quick cards, 3.5 s each: photo or short face clip on the left, name + role on the right, one line of what they built. Each person says their own line (or one narrator reads all four).

| Time | Card | Line (spoken) |
|---|---|---|
| 0:10 – 0:14 | **[Name]** · @sanskarjoshiii | "I built the core: the WhatsApp agent, matching and the AWS backend." |
| 0:14 – 0:17 | **Kamran Pathan** · @kamranp03 | "I built the dashboards, approvals and the pollution-impact view." |
| 0:17 – 0:21 | **[Name]** · @akkki007 | "I took it live: AWS deployment, the AI model and WhatsApp." |
| 0:21 – 0:25 | **[Name]** | "I handled testing, this video and the blog." |

---

## 3. Explainer · 0:25 – 1:15

**Layout:** split screen, two 8:9 halves of the 16:9 frame. Left half (960×1080): the presenter talking to camera. Right half (960×1080): the animation, five separate clips rendered from `video/` (`3a-problem.mp4` 12 s, `3b-idea.mp4` 9 s, `3c-how-it-works.mp4` 12 s, `3d-aws.mp4` 11 s, `3e-before-after.mp4` 6 s; 30 fps). No titles on screen: the presenter says them, the clips only show the supporting animation. Same look as the dashboard: white canvas, hairlines, green / amber / red only for risk, teal for straw, violet for the AI agent.

**Hackathon track (Air):** the explainer is framed on the track card. Scene 3a closes on the chips **Stubble burning · AQI · Pollution exposure**; scene 3c labels the risk score **Track** and the village alert **Warn**; scene 3e ends on **"Change what happens on the bad days."** (Indoor air and school safety are not part of clearsky, so they are left out.)

### 3a. The problem · 0:25 – 0:37 (12 s)

| Animation (right side) | Voice-over |
|---|---|
| The Punjab outline draws in with **Amritsar, Jalandhar, Ludhiana, Bathinda, Patiala**, and **Delhi** to the south-east. Fields appear as gold dots; a bar shows *Paddy harvest → Wheat sowing* squeezing to "only weeks to clear the straw". Fields ignite in waves, smoke drifts south-east to Delhi, and an **AQI** meter there slides to the bad end. Closes on the chips **Stubble burning · AQI · Pollution exposure**. Optional sourced number on the AQI card (`video/src/content.ts` → `problemStat`). | "Every October, after the paddy harvest, farmers get only weeks to sow wheat. Clearing straw is slow and costly, so many burn it, and the smoke drifts all the way to Delhi." |

### 3b. The idea · 0:37 – 0:46 (9 s)

| Animation | Voice-over |
|---|---|
| Farmer, baler and industry appear far apart; dashed lines reach for each other and stop short: "No link between them". The clearsky logo lands in the middle, solid lines connect all three, and three things flow through it: a violet **pickup request** (farmer → baler), teal **straw** bales (farmer → industry) and a **₹ payment** (industry → farmer). Tag on the farmer: "Only needs WhatsApp". | "That straw isn't waste. Industries buy it as fuel, and balers can collect it. clearsky connects them, and the farmer only needs WhatsApp." |

### 3c. How it works · 0:46 – 0:58 (12 s)

| Animation | Voice-over |
|---|---|
| Three cards light up in turn. **1 · Understands the farmer:** a voice note plays, the Hinglish text types out (*"Mera 8 acre dhaan 24 tareekh ko katega, Khanna. Naam Gurpreet."*) and Name / Village / Acres / Harvest tick in violet. **2 · Books the nearest free baler:** a search radius grows on a mini map, the nearest free baler (6 km) is picked, a pellet plant is linked, "Booked · capacity reserved". **3 · Tracks fields about to burn (Track · Warn):** NASA fire history and days-to-sowing feed a gauge that swings to Red, then "Village alert on WhatsApp" fires and the field turns green when booked. | "An AI agent understands Hindi or Punjabi, even voice notes. A matcher books the nearest free baler and a buyer. And a risk score tracks fields about to burn, and warns them first." |

### 3d. Built on AWS · 0:58 – 1:09 (11 s)

| Animation | Voice-over |
|---|---|
| Four lanes light up as they are named, with a violet packet moving through the active one: **01 Every message** WhatsApp → API Gateway → Lambda → SQS · **02 Voice** Transcribe → Lambda (AI agent) → Polly · **03 Bookings** two bookings race for a baler's last slot and the **DynamoDB transaction** lets exactly one win ("B → next free baler") · **04 Every hour** EventBridge Scheduler → risk Lambda (+ NASA FIRMS) → Burn Risk Radar. Footer: Cognito, S3, CloudWatch. | "It runs serverless on AWS: Lambda and SQS take every message, Transcribe and Polly handle Hindi voice, DynamoDB transactions stop double-booking, and EventBridge rescores risk every hour." |

> Only name services that are switched on in the deployed stack. If Transcribe is not enabled (`STT_PROVIDER`), drop it from the line and the diagram. If the LLM runs on Bedrock, add "Bedrock" to the agent box.

### 3e. Before and after · 1:09 – 1:15 (6 s)

| Animation | Voice-over |
|---|---|
| Two columns. **Before:** Calls around → Waits (clock spinning) → Burns the field (red flame). **With clearsky:** One WhatsApp message → Pickup confirmed → Straw sold, farmer paid. The "before" column greys out as the "after" one builds; end line with the logo: **"Change what happens on the bad days."** | "Before: calls, waiting, a fire. After: one message, a pickup, a payment." |

---

## 4. Live demo · 1:15 – 2:45

Screen recordings of the real app. Prepare the state with `docs/demo_runbook.md` (Reset → demo clock). Use the **offer flow** (the baler taps Accept), because it shows the full loop. Zoom 100 %, 1440×900, notifications off. For WhatsApp, record a real phone (needs issue #4 done) or the farmer simulator on `/admin`.

### 4a. WhatsApp agent · 1:15 – 1:45 (30 s)

| Time | Screen | Voice-over |
|---|---|---|
| 1:15 – 1:25 | Phone. The farmer sends a voice note (or types): *"Mera 8 acre dhaan 24 tareekh ko katega, Bhawanigarh. Naam Gurpreet."* Subtitle: *"My 8 acres of paddy will be cut on the 24th, Bhawanigarh. Name Gurpreet."* | "Meet Gurpreet. One voice note in Hindi gives us the name, village, acres and harvest date. No app, no forms." |
| 1:25 – 1:35 | The agent replies in Hinglish: the request is sent to the nearest baler. Highlight the parsed details with a violet outline. | "The agent understands it, finds the best baler nearby and sends the job, all in seconds." |
| 1:35 – 1:45 | *(cut back here after 4b's Accept)* ✅ *"Gurpreet ji, … ko baler … aapka khet saaf karne aayega. Parali na jalayein. 🙏"* plus the Hindi voice reply playing (Polly). | "When the baler accepts, Gurpreet gets a confirmation, in text and as a Hindi voice reply." |

### 4b. Baler dashboard · 1:45 – 2:07 (22 s)

| Time | Screen | Voice-over |
|---|---|---|
| 1:45 – 1:52 | Phone-sized browser, `/baler/requests`: the new request (farmer, acres, distance, payout). Tap **Accept**. | "The baler gets the job on a phone: place, acres, pay. One tap accepts." |
| 1:52 – 2:00 | `/baler` **Today**: numbered stops on the route map, capacity left for the day. | "The day becomes a route: every stop in order, with capacity left." |
| 2:00 – 2:07 | Tap **Done · हो गया** → confirm → the stop turns green → (inset) the farmer's phone gets "aapka khet aaj saaf ho gaya". | "When the field is cleared, one tap on Done, and the farmer is told immediately." |

### 4c. Industry buyer dashboard · 2:07 – 2:22 (15 s)

| Time | Screen | Voice-over |
|---|---|---|
| 2:07 – 2:14 | `/buyer` **Overview**: tonnes needed vs tonnes on the way, incoming deliveries. | "The industry buyer sees exactly how much straw is coming, and from where." |
| 2:14 – 2:22 | **Demand**: change the tonnes needed → save; **Deliveries**: export CSV. | "They update demand anytime, and clearsky routes the next bales to match." |

### 4d. Super-admin (district officer) dashboard · 2:22 – 2:45 (23 s)

| Time | Screen | Voice-over |
|---|---|---|
| 2:22 – 2:30 | `/admin` **Burn Risk Radar**: the map with green / amber / red rings; Demo controls → **Harvest wave** makes one village light up red. | "The district officer gets a Burn Risk Radar: every field scored live, with high-risk villages in red." |
| 2:30 – 2:38 | Click the red village → **Alert** → **Send WhatsApp offer** → toast "Offer sent to N farmers". Inset: a farmer taps **HAAN, book karo**, and the pin turns solid green. | "One click offers every farmer there a pickup. They say yes, and red turns green before anything burns." |
| 2:38 – 2:45 | **Approvals**: approve a new baler's registration; then a quick look at `/impact`. | "The officer also approves new balers and buyers, and tracks the impact across the district." |

---

## 5. Outro · 2:45 – 3:00 (15 s)

| Time | Screen | Voice-over |
|---|---|---|
| 2:45 – 2:53 | Back to the intro film's look: a cleared field with neat bales, a clear blue sky. The `/impact` counters overlay the shot. | "No fire. The straw becomes fuel, farmers earn instead of burning, and the sky stays clear." |
| 2:53 – 3:00 | White end card: round clearsky logo, **"Straw pickup instead of stubble fires."**, `github.com/sanskarjoshiii/clearsky`, "Built on AWS · AWS Environmental Hacks 2026", the four team names. | "clearsky: one WhatsApp message instead of one more fire." |

---

## Fill in before recording

| What | Why | Where it shows |
|---|---|---|
| **Names** of @sanskarjoshiii, @akkki007 and the fourth member, and confirm each person's line | Not in the repo; don't guess | 2. Team, outro card |
| **STAT CARD 1** (e.g. area burnt, fire count or air-quality impact) **with its source** shown in small text on the card | We never put an unsourced number on screen | 3a |
| **Emission factors with citations** in `EMISSION_FACTORS` (`SETUP_GUIDE.md` §9b) | Without them the app hides "pollution avoided"; then cut that counter from 3e and the outro and say "acres cleared, tonnes routed" | 3e, 4d, 5 |
| Deployed stack + real WhatsApp number (issue #4) | Real-phone shots and the Polly voice reply need it; otherwise record the simulator | 4a, 4b |
| Which AWS services are actually on (Transcribe? Bedrock?) | Name only what runs | 3d |

## Recording checklist

- Record the demo (4a–4d) as one continuous take per role, then cut. Order of real actions: farmer message → baler Accept → farmer ✅ → Done → buyer → radar alert → approvals.
- Before the take: `make test` and `make e2e` green, demo Reset, demo clock set (`docs/demo_runbook.md`).
- Use synthetic or team phone numbers only; blur any real number on screen.
- Subtitles for every Hindi/Hinglish line; captions for the full voice-over (judges often watch muted).
- Background music low under the voice-over; the intro film keeps its own audio.
- Final export 1920×1080, ≤ 3:00, then upload and put the link in `README.md`.
