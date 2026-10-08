# ClearSky: Build Plan (Phase-wise)

This plan is written so the team (or Claude Code) can run **"implement phase N"** and get a complete, tested slice of the system.

Read `CONTEXT.md` (current state), `README.md` (what and why) and `IMPLEMENTATION.md` (how: design source of truth) before any phase.

**Scope reminders:** one monorepo for everything. WhatsApp serves **farmers only**; baler operators, buyers and officers use the web dashboard.

---

## 0. Protocol for Claude Code (read every time)

When asked to **"implement phase N"**:

1. **Read** `CONTEXT.md`, `README.md`, `IMPLEMENTATION.md`, this file, and `PROGRESS.md`.
2. **Check prerequisites:** every earlier phase listed under *Depends on* must be marked ✅ in `PROGRESS.md`. If not, stop and tell the team which phase is missing.
3. **Ask first, in one batch:** collect every unanswered item from the phase's **❓ Ask the team** list, plus anything the docs leave genuinely ambiguous, and ask them in a **single message**. Don't start writing code that depends on an unanswered item. Items marked *(default OK)* can proceed with the stated default if the team says "use defaults".
4. **Implement** every task in the phase. Follow the file paths, names and designs in `IMPLEMENTATION.md`. If you must deviate, choose the simplest option that works and **record it** under *Deviations* in `PROGRESS.md`.
5. **Verify** with every command in **✅ Definition of Done**. Fix failures until all pass.
6. **Update `PROGRESS.md`:** phase status, what was built, commands run, deviations, open questions, and next steps.
7. **Update `CONTEXT.md`:** current state, decisions, open questions, and a changelog line (see the rules at the top of that file).
8. **Stop.** Summarise in ≤ 10 bullets. **Don't start the next phase** unless asked.

### Hard rules

- ❌ Never invent secrets, API keys, account IDs, phone numbers, model IDs or real-world statistics. Ask.
- ❌ Never commit `.env` or secrets. Only commit `.env.example`.
- ❌ Never run `sam deploy`, delete stacks, or create paid resources without explicit confirmation in the current session. `sam build`, local tests and `sam validate` are fine.
- ❌ Never use real company names for seeded buyers. Never present demo prices as real prices.
- ✅ After **every** change (code or docs, not only at phase end), update `CONTEXT.md` so a teammate's AI assistant can pick up from it.
- ✅ All config goes through `clearsky.config.settings`. All dates go through `clearsky.clock`.
- ✅ Mask phone numbers in logs.
- ✅ Keep functions small and typed (Pydantic v2 models, type hints). Tests live next to the logic they cover.
- ✅ Prefer working end-to-end over feature breadth. If time-boxed, cut scope, never quality of the core loop.
- ✅ If a library API differs from the snippets in the docs (e.g. Strands, the WhatsApp Graph version), check the installed version's docs and adapt. Note it in *Deviations*.

### Phase map and schedule

| Phase | Name | Depends on | Day (Oct) | Owner | Est. |
|---|---|---|---|---|---|
| 0 | Bootstrap & AWS readiness | – | 8 | Akshay | 1.5 h |
| 1 | Data layer, seed data, FIRMS | 0 | 8 | P2 | 3 h |
| 2 | Matching & booking engine | 1 | 8 | P2 | 3 h |
| 3 | Farmer agent + local chat CLI | 2 | 9 | Akshay | 4 h |
| 4 | WhatsApp + voice + first deploy | 3 | 9 | Akshay | 4 h |
| 5 | REST API (operator dashboard + buyer), Cognito, reminders | 4 | 10 | P2 | 4 h |
| 6 | Risk engine + officer alerts | 5 | 10 | P2 / P3 | 3 h |
| 7 | Dashboard (officer, buyer, operator, impact) | 5 (can start on mocks after 1) | 9–10 | P3 | 8 h |
| 8 | Satellite harvest layer *(stretch)* | 1 | 11 | P3 | 3 h |
| 9 | Demo mode, hardening, video, blog, submission | 6, 7 | 11 | All / P4 | full day |

**Cut lines if behind schedule:** drop Phase 8 → drop voice replies (keep voice input) → drop the buyer page (keep a buyer table on the officer page). **Never cut:** farmer booking loop, officer radar, the video.

> Hackathon rule: project code starts at kickoff (Oct 8). Before that, only learning, setup of accounts and access, and storyboard.

---

## Phase 0: Bootstrap & AWS Readiness

**Goal:** a monorepo skeleton that builds, tests and validates, with confirmed AWS access to every service we need.

**Depends on:** –

### ❓ Ask the team
1. AWS region? *(default OK: `ap-south-1`)*
2. AWS CLI profile name to use? Is `aws sts get-caller-identity` working?
3. Which Bedrock model have you enabled access for? (Give the exact model ID or inference profile ID.)
4. Python package manager: `uv` or `pip`? *(default OK: `uv`)*
5. Git remote URL (if any)?

### Tasks
1. Create the monorepo structure from `README.md` §9 (empty packages with `__init__.py`). Keep the existing `CONTEXT.md` and `AGENTS.md`.
2. `backend/pyproject.toml`: Python 3.12; deps `strands-agents`, `boto3`, `aws-lambda-powertools[all]`, `pydantic>=2`, `pydantic-settings`, `rapidfuzz`, `httpx`, `python-dateutil`; dev deps `pytest`, `moto[dynamodb,s3,sqs,ssm]`, `ruff`, `mypy`.
3. `backend/src/clearsky/config.py`: Settings with every key in `IMPLEMENTATION.md` §13. SSM-backed secrets loaded lazily and cached.
4. `backend/src/clearsky/clock.py`: `today()`, `now()` in IST; demo override via `Settings` table (stubbed until Phase 1).
5. `backend/src/clearsky/logging.py`: Powertools logger factory + `mask_phone()`.
6. `infra/template.yaml`: SAM skeleton with Globals (python3.12, arm64, timeout 30, memory 512, env vars), parameters `Stage`, a placeholder `HealthFunction` + HTTP API `GET /health`.
7. `Makefile`: `install`, `lint`, `test`, `build` (`sam build`), `validate` (`sam validate --lint`), `deploy` (guarded, prints a warning), `seed`, `chat`.
8. `.env.example`, `.gitignore`, `PROGRESS.md` (template with all phases ⬜), `scripts/put_secrets.sh` (reads from `.env`, writes SSM SecureStrings under `/clearsky/{stage}/…`).
9. `scripts/check_aws.py`: verifies caller identity, Bedrock model invoke ("ping"), Transcribe `hi-IN` support, Polly `describe_voices(LanguageCode='hi-IN')` includes the configured voice, Location Service reachable. Prints a ✅/❌ table.

### ✅ Definition of Done
- `make install && make lint && make test` pass (a trivial test is fine).
- `make validate` passes.
- `uv run python scripts/check_aws.py` shows all ✅ (or the team acknowledges any ❌ with a plan).
- `PROGRESS.md` exists, with Phase 0 ✅. `CONTEXT.md` reflects the new state.

### Out of scope
Any business logic. Any deploy.

---

## Phase 1: Data Layer, Seed Data, FIRMS

**Goal:** all DynamoDB tables defined in SAM, typed models and repositories, reproducible seed data for Sangrur, and the FIRMS fire-history layer with village scores.

**Depends on:** 0

### ❓ Ask the team
1. Confirm the target district: Sangrur, Punjab? *(default OK)*
2. Provide or approve a list of ~30 village/town names (I'll propose one). Should I geocode them with Amazon Location (needs a Place Index), or use synthetic points?
3. NASA FIRMS MAP_KEY (stored in SSM). If not available yet, should I use a manually downloaded FIRMS CSV placed in `data/raw/firms/`?
4. Team phone numbers to embed as demo farmers (E.164)? These will be test recipients on WhatsApp. (Operators don't need WhatsApp numbers; they log in to the dashboard.)
5. Approve to deploy the tables to the dev stack now? (Requires `sam deploy`.)

### Tasks
1. **SAM:** add every table from `IMPLEMENTATION.md` §3.1 (on-demand, GSIs, TTL on `Conversations.ttl` and `ProcessedMessages.ttl`), two S3 buckets (`MediaBucket` with a 7-day lifecycle; `DataBucket`), and outputs.
2. **Models** (`models/`): `Village`, `Farmer`, `Field`, `Baler`, `BalerDay`, `Buyer`, `Booking`, `Alert`, `ConversationTurn`, enums `FieldStatus`, `BookingStatus`, `RiskLevel`. Include serializers to and from DynamoDB (Decimal handling).
3. **Repositories** (`repo/`): one class per table with get/put/query by every GSI, and `repo/transactions.py` with a helper to build TransactWriteItems. Table names come from `settings.table_prefix`.
4. **Clock:** implement the `Settings` table override.
5. **Geo** (`domain/geo.py`): `haversine_km`, `jitter_point`, `bbox_contains`.
6. **Villages** (`domain/villages.py`): `resolve(name) -> list[Match]` using rapidfuzz over name, aliases, `name_hi` and `name_pa` (transliteration aliases included in the seed).
7. **Seed generator** (`scripts/gen_seed.py`): writes `data/seed/*.json` per `IMPLEMENTATION.md` §14, deterministic with `--seed`. Includes ~10 RED-candidate fields (harvested, unbooked, near deadline).
8. **Seeder** (`scripts/seed_dynamo.py --reset`): loads JSON into the tables (batch writes).
9. **FIRMS** (`scripts/fetch_firms.py` + `handlers/firms_ingest.py`): fetch VIIRS points for the district bbox for Oct–Nov of 2022–2025 (via API with MAP_KEY, or from the CSV fallback) → `data/layers/firms_2022_2025.geojson` → upload to `DataBucket/layers/` → compute and write `Villages.fire_history_score`.
10. **Tests:** repo CRUD and GSIs with moto; village resolution ("Bhawanigarh", "bhavanigarh", "भवानीगढ़"); seed determinism; FIRMS aggregation on a small fixture.

### ✅ Definition of Done
- `make test` passes, with the new tests.
- `uv run python scripts/gen_seed.py --seed 42` produces identical files on two runs.
- (After deploy approval) `make seed` loads data, and `aws dynamodb scan --table-name clearsky-dev-Villages --select COUNT` ≈ 30.
- `firms_2022_2025.geojson` exists, with > 0 features, and village scores are populated.

### Out of scope
Matching, the agent, WhatsApp.

---

## Phase 2: Matching & Booking Engine

**Goal:** given a field, reliably book the best baler-day and buyer with no double booking, and compute the payout.

**Depends on:** 1

### ❓ Ask the team
1. Demo values for `BALING_COST_PER_ACRE`, `TRANSPORT_COST_PER_TONNE_KM`, `PLATFORM_FEE_PER_TONNE`, and buyer `price_per_tonne` ranges? *(default OK: I'll propose demo numbers, labeled "demo")*
2. Should a booking be allowed when no buyer has capacity (straw goes to "village storage, pending")? *(default OK: yes)*

### Tasks
1. `domain/pricing.py`: per `IMPLEMENTATION.md` §5.
2. `domain/matching.py`: `find_candidates()`, `choose_buyer()`, `book_pickup(field_id)`, `cancel_booking(booking_id)`, `reschedule(field_id, new_date)`, `recompute_stop_order(baler_id, date)`. Use the transaction from `IMPLEMENTATION.md` §4, and retry the next-best candidate on `ConditionalCheckFailed`.
3. `has_capacity_before_deadline(field)`: a cheap check, used later by the risk engine.
4. Result types: `Booked`, `NoSlot(reason)`, all Pydantic.
5. `scripts/book_all.py --dry-run`: tries to book every unbooked seeded field and prints a summary table (booked / no slot / reason).
6. **Tests:**
   - picks the nearest baler when everything else is equal
   - respects capacity (two fields > capacity → second goes to another day or baler)
   - respects the deadline (no slot after `sowing_deadline - buffer`)
   - cluster bonus prefers a baler already in the village
   - buyer choice maximises net price; skips buyers without enough remaining demand
   - concurrency: two simulated concurrent bookings for the last capacity → exactly one succeeds (moto transaction conditions)
   - cancel frees capacity and buyer reservation

### ✅ Definition of Done
- `make test` passes; matching/pricing coverage ≥ 85% (`pytest --cov`).
- `scripts/book_all.py --dry-run` against the dev tables prints a sensible summary.

### Out of scope
LLM, WhatsApp.

---

## Phase 3: Farmer Agent + Local Chat CLI

**Goal:** a Strands agent that can hold a Hindi/English/Punjabi conversation, register a farmer and field, and book a pickup, testable from the terminal.

**Depends on:** 2

### ❓ Ask the team
1. Confirm `BEDROCK_MODEL_ID` (from Phase 0) and that it supports tool use.
2. Default reply language: Hindi in Devanagari, Hindi in Roman script (Hinglish), or match the farmer? *(default OK: match the farmer; Devanagari for voice)*
3. Bot name and greeting line? *(default OK: "ClearSky 🌾")*

### Tasks
1. `agent/prompts.py`: farmer system prompt per `IMPLEMENTATION.md` §7.3, with `{today}` injected.
2. `agent/tools.py`: tool implementations (pure functions that take `phone`), with input validation and friendly error strings.
3. `agent/agent.py`: `build_agent(phone, history, today)` factory (tools bound by closure) and `run_turn(phone, text) -> AgentReply{text, booking?}`, which loads and saves history.
4. `agent/memory.py`: `Conversations` read/write, last 10 turns, conversion to the Strands message format.
5. No role router: every WhatsApp sender is a farmer. `run_turn` handles both known farmers and new numbers (onboarding via `register_farmer`).
6. `scripts/chat_cli.py --phone +91… [--today 2026-10-20]`: REPL that prints the bot replies and the tool calls made (debug flag).
7. **Tests:**
   - tools reject bad inputs (acres 0, past dates, unknown village)
   - phone isolation: the agent built for phone A cannot read or modify phone B's data (call the tools directly)
   - with a stubbed model that emits scripted tool calls, a full booking happens and the reply text contains the booked date
8. Write `docs/agent_transcripts.md` with 5 real CLI transcripts: Hindi, Hinglish, Punjabi, English, and an off-topic message.

### ✅ Definition of Done
- `make test` passes.
- In `make chat`, the message "Mera 8 acre dhaan 24 tareekh ko katega, Bhawanigarh. Naam Gurpreet." results in a booking in DynamoDB and a confirmation in the reply, within ≤ 3 turns.
- An off-topic message gets a polite redirect.

### Out of scope
WhatsApp, voice.

---

## Phase 4: WhatsApp + Voice + First Deploy

**Goal:** a real farmer on WhatsApp can send text or a voice note and get booked, with a text and Hindi voice reply, running on AWS.

**Depends on:** 3

### ❓ Ask the team
1. WhatsApp Cloud API details: `WA_PHONE_NUMBER_ID`, `WA_ACCESS_TOKEN` (permanent system-user token preferred), `WA_APP_SECRET`, chosen `WA_VERIFY_TOKEN`. Have they been put in SSM via `scripts/put_secrets.sh`?
2. Which Graph API version does your Meta app use?
3. Test recipient numbers added in Meta (≤ 5)?
4. Approval to run `sam deploy` for the dev stack?
5. Should we create the farmer templates `pickup_reminder` and `village_alert` now? I'll provide the exact template text for you to submit in Meta Business Manager.

### Tasks
1. **SAM:** `WebhookFunction` (HTTP API `GET/POST /webhook/whatsapp`), `InboundQueue` + `InboundDLQ`, `ProcessorFunction` (SQS trigger, batch 1, timeout 120 s, memory 1024 MB), queue visibility timeout 720 s, IAM for Transcribe/Polly/Bedrock/S3/DDB/SSM. Alarm on DLQ depth.
2. `channels/whatsapp.py`: verify challenge, `verify_signature(raw_body, header)`, `parse_inbound(payload) -> list[Inbound]`, `send_text`, `send_audio_link`, `send_template`, `send_buttons`, `download_media(media_id) -> bytes`. Use httpx with timeouts and retries.
3. `channels/voice.py`: `transcribe_ogg(bytes, msg_id) -> str` (S3 upload, start job, poll ≤ 60 s, fetch transcript) and `synthesize(text) -> presigned_url` (Polly mp3 → S3 → presigned 1 h). Reject audio over 60 s with a friendly message.
4. `handlers/webhook.py`: GET verify; POST signature check → for each message, conditional put to `ProcessedMessages` → SQS send → 200.
5. `handlers/processor.py`: inbound → (voice? send "🎙️ Sun raha hoon…", then transcribe) → farmer agent `run_turn` → reply text (+ voice if the inbound was voice). Handle `location` messages (update the latest field's lat/lng) and button replies.
6. `channels/templates.py`: template names and parameter builders + `docs/whatsapp_templates.md` with the exact text to submit (Hindi + English).
7. `scripts/e2e.py`: posts a correctly signed fake webhook payload to the deployed URL and checks that a booking appears.
8. **Tests:** signature valid/invalid, verify challenge, payload parsing (text, audio, button, location, status), dedupe, processor with mocked WhatsApp/Transcribe/Polly.

### ✅ Definition of Done
- `make test` passes; `sam build` and `sam deploy` (approved) succeed; the outputs print `ApiUrl`.
- Meta webhook verification succeeds.
- From a team phone: a **text** message leads to a booking and a confirmation reply.
- From a team phone: a **Hindi voice note** leads to a booking, a text reply, **and** a voice reply.
- `scripts/e2e.py` passes. DLQ is empty.

### Out of scope
Operators, buyers, the dashboard. (None of these will ever be on WhatsApp.)

---

## Phase 5: REST API (Operator Dashboard + Buyer), Cognito, Reminders

**Goal:** the REST API is live for the dashboard; operators can sign in, see their stops and mark fields done; buyers can manage demand and see supply; farmer reminders go out on schedule.

**Depends on:** 4

### ❓ Ask the team
1. Cognito: OK to create a user pool with groups `officer`, `buyer` and `operator`? Email addresses for the first officer, buyer and operator demo users, and which seeded `baler_id` each operator maps to?
2. Reminder time: 18:00 IST? *(default OK)*

### Tasks
1. **SAM:** Cognito User Pool + App Client + groups (`officer`, `buyer`, `operator`) + custom attributes (`district`, `buyer_id`, `baler_id`); HTTP API JWT authorizer; `ApiFunction` (Powertools resolver) with all routes from `IMPLEMENTATION.md` §9 except demo routes; `RemindersFunction` + EventBridge Scheduler (cron 18:00 Asia/Kolkata).
2. `handlers/api.py`: routes for stats, villages, fields, field detail, buyers/me supply and demand, operator/me (get/put), operator/me/route (+ Amazon Location `CalculateRoute` for the polyline; fallback straight lines), operator/me/alerts, booking done, layers (presigned). Operator routes take `baler_id` from the JWT only.
3. **Booking done flow:** operator taps Done → booking DONE → field CLEARED → buyer `received_tonnes` → farmer WhatsApp "Khet saaf ho gaya ✅" ("Field cleared ✅") → stats update.
4. `handlers/reminders.py`: the farmer reminder jobs in `IMPLEMENTATION.md` §2.3, using templates outside the 24 h window and free-form text inside it. No operator messages.
5. Agent tool `confirm_harvest` wired to HAAN/NAHI button replies.
6. `scripts/create_demo_users.py`: creates the Cognito demo users from the answers above (prints temporary passwords once; never writes them to the repo).
7. **Tests:** API auth (group checks; an operator can't read or mark another baler's booking), operator route ordering, capacity/availability update, supply aggregation, reminders selection logic with the demo clock.

### ✅ Definition of Done
- `make test` passes; deployed.
- `curl` with an operator JWT to `/api/operator/me/route?date=` returns that baler's stops; `POST /api/bookings/{id}/done` clears the field, and the farmer gets a WhatsApp notification.
- The same call with another baler's booking id returns 403.
- `curl` with a buyer JWT to `/api/buyers/me/supply` returns a forecast.
- Running reminders manually (`aws lambda invoke`) with a demo clock set sends the expected farmer messages.

### Out of scope
Risk scoring, dashboard UI.

---

## Phase 6: Risk Engine + Officer Alerts

**Goal:** every field and village carries a live risk score, and officers can alert a village and watch fields flip to green.

**Depends on:** 5

### ❓ Ask the team
1. Confirm the risk weights and thresholds in `IMPLEMENTATION.md` §6? *(default OK)*
2. Emission factor for "PM2.5 avoided per tonne of straw not burnt": value **and source citation**. If none, should the impact page omit emissions? *(default: omit)*

### Tasks
1. `domain/risk.py`: per `IMPLEMENTATION.md` §6, returning `(score, level, reasons[])`.
2. `handlers/risk_job.py`: scores all open fields and updates village aggregates; EventBridge Scheduler hourly; also callable on demand.
3. Recompute a single field's risk immediately on booking, cancel and harvest confirmation (inline, so the map updates fast).
4. `POST /api/alerts`: select the village's unbooked fields → `village_alert` template to each farmer (button "HAAN, book karo" / "Yes, book it") → write `Alerts` with `balers_flagged` = balers within radius that have free capacity (shown on their operator dashboard via `/api/operator/me/alerts`; no WhatsApp to operators). A farmer tapping HAAN → `book_pickup` → reply.
5. `GET /api/villages`, `GET /api/fields`: include risk data. `GET /api/stats`: add `red_fields`, `fields_saved_after_alert`.
6. FIRE_REPORTED: during the risk job, if a FIRMS/NRT point (when available) is ≤ 500 m of a harvested, unbooked field → mark it. *(Optional; skip if no NRT key.)*
7. **Tests:** threshold boundaries, booked → 0, not harvested → damped, village aggregation, alert recipient selection, idempotent alerts (no duplicate within 30 min per village).

### ✅ Definition of Done
- `make test` passes; deployed.
- After `gen_seed` + `seed`, the risk job yields ≥ 5 RED fields in Sangrur.
- `POST /api/alerts` for a RED village sends WhatsApp to the test phones; tapping HAAN books the field, and its level becomes GREEN within one request.

### Out of scope
UI.

---

## Phase 7: Dashboard

**Goal:** a polished, phone-friendly web app for officers, buyers and baler operators (the operator view is deliberately simple), plus a public impact page, deployed on Amplify.

**Depends on:** 5 (UI work can start after Phase 1 using mock JSON in `dashboard/src/mocks/`)

### ❓ Ask the team
1. Amazon Location: map resource or API key + style name to use? Or fall back to free MapLibre demo tiles for development? *(default OK: Location API key)*
2. Amplify Hosting: connect the Git repo (needs the remote) or manual deploy via zip? *(default OK: Git)*
3. Brand: colors/logo? *(default OK: green #1B7F3B, amber #E8A317, red #D64545, wheat #F5E6C8)*

### Tasks
1. Scaffold Vite + React + TS + Tailwind + react-router + TanStack Query + Amplify Auth; `src/api/client.ts` with JWT injection; env vars `VITE_API_URL`, `VITE_USER_POOL_ID`, `VITE_USER_POOL_CLIENT_ID`, `VITE_MAP_STYLE_URL`.
2. **`/officer`** (most important screen):
   - Top KPI bar: acres registered / booked / cleared, RED fields, tonnes routed.
   - Map: deck.gl `ScatterplotLayer` field pins colored by level (pulse animation on RED), `HeatmapLayer` FIRMS toggle, village risk circles, harvest grid toggle (Phase 8).
   - Right panel: villages sorted by risk → expand shows fields; an **"Alert village"** button with a confirm dialog and toast; a field drawer with risk reasons, farmer (masked phone), and booking.
   - 10 s polling; smooth color transitions when levels change.
3. **`/buyer`**: demand/price form, Recharts stacked bars (booked vs delivered tonnes by date), deliveries table.
4. **`/operator`** (Cognito `operator` group, keep it simple): mobile-first stop list with call buttons, map with route polyline, big Done buttons, date switcher, "Available today" toggle + acres/day, banner for nearby village alerts, Hindi labels. After login, operators land here directly.
5. **`/impact`**: large animated counters (react-countup), fit for screen recording.
6. Loading/empty/error states everywhere; responsive down to a 375 px width.
7. Amplify Hosting config (`amplify.yml`).
8. **Tests:** component tests for KPI bar, risk legend and operator stop list (Vitest); Playwright smoke tests: officer logs in, sees the map, and alerts a village; operator logs in, sees stops, and marks one Done (against dev).

### ✅ Definition of Done
- `npm run build` passes; Vitest passes; Playwright smoke passes against dev.
- Deployed Amplify URL works on desktop and phone.
- Live demo: Alert village on the dashboard → tap HAAN on the phone → pin turns green within 10 s.

### Out of scope
Satellite processing.

---

## Phase 8: Satellite Harvest Layer *(stretch)*

**Goal:** show harvested land from Sentinel-2 that is **not registered**, as a village-level "unregistered at-risk acres" layer.

**Depends on:** 1

### ❓ Ask the team
1. Do we have time? (Only start if Phases 0–7 are ✅ by Oct 11 morning.)
2. Which block should be processed (one block only)? *(default OK: around Bhawanigarh)*
3. Pre-harvest and post-harvest date ranges? *(default OK: Sep 25–Oct 5 vs the latest 10 days)*

### Tasks
1. `satellite/ndvi_harvest.py`: `pystac-client` against the Earth Search STAC (`sentinel-2-l2a`), cloud filter < 20%, read B04/B08/SCL COGs with `rioxarray` (windowed to the bbox), compute NDVI for both dates, mask clouds, build a 500 m grid, and classify harvested cells per `IMPLEMENTATION.md` §2.9 → `harvest_grid.geojson` → `DataBucket/layers/`.
2. Village join: `est_harvested_acres` per village minus booked acres → `Villages.unregistered_at_risk_acres`.
3. Dashboard toggle "Satellite: harvested (unregistered)".
4. Document the method and its limits in `docs/satellite.md` (clouds and haze, 5-day revisit, Sentinel-1 as future work).

### ✅ Definition of Done
- GeoJSON is produced for one block, and the layer renders on the officer map.
- If processing fails due to clouds, the layer is shown as "Phase 2" in the video, and that's fine.

---

## Phase 9: Demo Mode, Hardening, Video, Blog, Submission

**Goal:** a smooth, repeatable demo; a 3-minute video; a Builder Center blog; submission.

**Depends on:** 6, 7

### ❓ Ask the team
1. Who records the voiceover? Language of the video (English with Hindi bot audio)? *(default OK)*
2. Submission links needed (repo, video URL, blog URL, deployed URL)?

### Tasks
1. **Demo mode:** `GET/PUT /api/demo/clock`, `POST /api/demo/simulate` (`harvest_wave`, `run_risk`, `run_reminders`, `reset`), and `scripts/demo_clock.py`. Gate it behind `DEMO_MODE` and the officer group.
2. **Demo runbook** `docs/demo_runbook.md`: exact click and message sequence for the recording (reset → set clock Oct 20 → farmer voice note → operator dashboard shows the new stop → operator taps Done → set clock Oct 26 → harvest_wave → radar RED → Alert → HAAN → GREEN → impact page).
3. **Hardening:** run the runbook 3 times end to end; fix flakiness; check the DLQ is empty and there are no errors in CloudWatch; set up the budget alarm.
4. **Video** (`video/`): Remotion project with the scenes from `README.md` §12:
   - Scene 1: FIRMS points animated by hour (1:30 pm vs 5 pm), using real data from Phase 1
   - Scene 2: split screen, farmer countdown vs empty plant yard
   - Scene 3: farmer phone screen recording (real) + operator dashboard + deck.gl TripsLayer trucks
   - Scene 4: radar screen recording (RED → GREEN)
   - Scene 5: AWS architecture animation following one message
   - Scene 6: impact counters + closing line
   - Export at 1080p, ≤ 3:00.
5. **Blog** (`docs/blog.md`): problem → insight (3 pm gap) → build → AWS services → what fought back → results. Publish on AWS Builder Center.
6. **README:** final screenshots/GIFs, deployed URL, video link.
7. **Submission checklist:** repo public, README complete, video ≤ 3 min uploaded, blog link, deployed URL, team members verified on Builder Center.

### ✅ Definition of Done
- Runbook passes 3 times in a row without manual fixes.
- Video exported and uploaded; blog published; submission sent before the deadline.

---

## PROGRESS.md template (create in Phase 0)

```markdown
# Progress

| Phase | Status | Date | Notes |
|---|---|---|---|
| 0 Bootstrap | ⬜ | | |
| 1 Data | ⬜ | | |
| 2 Matching | ⬜ | | |
| 3 Agent | ⬜ | | |
| 4 WhatsApp | ⬜ | | |
| 5 Operator/Buyer/API | ⬜ | | |
| 6 Risk/Alerts | ⬜ | | |
| 7 Dashboard | ⬜ | | |
| 8 Satellite | ⬜ | | |
| 9 Demo/Submit | ⬜ | | |

## Phase N log
- Built:
- Commands run:
- Deviations:
- Open questions:
- Next:
```
