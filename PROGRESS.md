# Progress

Legend: ✅ done · 🟡 code complete and tested; a Definition-of-Done item is waiting on a team input or approval (listed) · ⬜ not started

| Phase | Status | Date | Notes |
|---|---|---|---|
| 0 Bootstrap | 🟡 | 2026-10-07 | All built and green. `check_aws`: Bedrock model ID not chosen; Transcribe not subscribed on the account. |
| 1 Data | 🟡 | 2026-10-07 | Tables, models, repos, seed, FIRMS code done. Waiting: deploy approval (seed AWS tables), FIRMS MAP_KEY (real layer), village list confirmation. |
| 2 Matching | 🟡 | 2026-10-07 | Engine done; coverage matching 94%, pricing 100%. `book_all` ran against a local mock DB; dev tables need deploy. |
| 3 Agent | 🟡 | 2026-10-09 | Provider-agnostic agent (OpenAI-compatible / Anthropic / Gemini / Bedrock) + rules bot fallback, both tested. Waiting: LLM API key + model ID for the live LLM check and transcripts. |
| 4 WhatsApp | 🟡 | 2026-10-09 | Webhook, processor, voice, templates, simulator mode, SAM resources, e2e script; tested locally end to end. Waiting: Meta app + WA secrets, STT choice, deploy approval. |
| 5 API/Operator dashboard/Buyer | 🟡 | 2026-10-09 | REST API, Cognito in SAM, operator done flow, buyer, reminders, demo-user script; tested. Waiting: deploy + Cognito users. |
| 6 Risk/Alerts | 🟡 | 2026-10-09 | Risk engine, inline re-scoring, village alerts, stats; DoD tests pass with fire history. Waiting: FIRMS key for real fire history, deploy. |
| 7 Dashboard | 🟡 | 2026-10-09 | All screens built from the reference design system; build + Vitest + Playwright smoke green locally. Waiting: deploy (Amplify) + Cognito. |
| 8 Satellite | ⬜ | | Stretch; not started (cut line 1 in PLAN.md). |
| 9 Demo/Submit | 🟡 | 2026-10-09 | Demo mode API + UI + `demo_clock.py` + runbook done. Not done: 3× runbook on the deployed stack, video, blog, submission (team). |

Test suite: **177 backend tests** (`make test`, coverage 91%), **8 Vitest + 3 Playwright** dashboard tests (`make e2e`); ruff, mypy, tsc clean; `sam validate --lint` and clean `sam build` pass.

---

## Phase 0 log: Bootstrap & AWS readiness
- **Built:** monorepo skeleton per README §9; `backend/pyproject.toml` (Python 3.12, uv); `config.py` (every §13 key, SSM secrets lazy + cached, env override); `clock.py` (IST, override, demo clock); `logging.py` (Powertools + `mask_phone`); `infra/template.yaml` (Globals, HTTP API, `GET /health`) + `samconfig.toml`; `Makefile` and `make.ps1` (Windows); `.env.example`, `.gitignore`, `scripts/put_secrets.sh`; `backend/scripts/check_aws.py`.
- **Commands run:** `.\make.ps1 install` · `lint` (ruff + format check + mypy: clean) · `test` · `validate` ("valid SAM Template") · `build` (clean build succeeded) · `check_aws.py`.
- **check_aws result:** ✅ credentials (account 416121583611, region ap-south-1) · ❌ Bedrock model (BEDROCK_MODEL_ID not set) · ❌ Transcribe (`SubscriptionRequiredException` on this account) · ✅ Polly Kajal neural (hi-IN) · ✅ Location reachable (0 maps, 0 place indexes) · ✅ Python 3.12.
- **Deviations:**
  - `make` and `sam` aren't installed on the Windows dev machine → added `make.ps1` with the same targets; SAM runs via `uv tool run --from aws-sam-cli sam` when not on PATH. `make.ps1` puts uv's Python 3.12 on PATH for `sam build`.
  - Python 3.12 is provided by uv (the machine's default is 3.14).
  - IST is a fixed UTC+05:30 offset (Windows has no tz database; India has no DST, so it's exact).
  - Lambda dependencies are built into a **layer** (`infra/.layer`, `make layer`) with `uv pip install --python-platform aarch64-manylinux_2_28`. SAM's own pip builder on Windows pulled the Windows-only `pywin32` (a transitive marker) and failed. Function zips now hold only our code (~0.1 MB); the layer is ~69 MB unzipped.
  - Polly lists Kajal as an en-IN voice with hi-IN as an additional language; `check_aws` checks that.
  - Bedrock invoke in `check_aws` is opt-in (`--invoke-bedrock`) because it is billed.
- **Open questions:** Bedrock model ID; enable Transcribe on the account; Git remote.
- **Next:** team answers → Phase 4 after approval.

## Phase 1 log: Data layer, seed data, FIRMS
- **Built:** all 11 tables in SAM (on-demand, GSIs, TTL on Conversations/ProcessedMessages) mirrored by `repo/schema.py` (a test keeps them identical); Media bucket (7-day lifecycle) + Data bucket; models (`models/`) with Decimal-safe (de)serialisation; one repository per table + `repo/transactions.py`; demo clock via `Settings`; `domain/geo.py`; `domain/villages.py` (rapidfuzz over English, aliases, Devanagari, Gurmukhi, with Roman spelling folding); `seed/generate.py` + `scripts/gen_seed.py`; `seed/load.py` + `scripts/seed_dynamo.py --reset [--set-clock]`; `domain/firms.py`, `scripts/fetch_firms.py` (API with MAP_KEY, or CSV fallback in `data/raw/firms/`), `handlers/firms_ingest.py` Lambda.
- **Seed:** 31 villages (10 towns + 21 villages in Sangrur, all `approx=true`), 10 balers (no operator phones), 3 fictional buyers ("Demo …", demo prices), 60 synthetic farmers/fields (`synthetic=true`), 20 marked for pre-booking (19 book, 1 no slot), 10 RED candidates. Reference date 2026-10-20.
- **Commands run:** `gen_seed.py --seed 42` twice → byte-identical files ✅; tests for repo CRUD/GSIs, village resolution ("Bhawanigarh", "bhavanigarh", "भवानीगढ़", "ਭਵਾਨੀਗੜ੍ਹ"…), seed determinism/loading, FIRMS aggregation on a synthetic fixture.
- **Not yet done (needs team):** `make seed` into AWS (needs deploy approval); real `firms_2022_2025.geojson` (needs FIRMS MAP_KEY or downloaded CSVs).
- **Deviations:**
  - Village names are a **proposal** (real Sangrur place names); coordinates are town centres plus offsets, flagged `approx=true` until geocoded with Amazon Location (no Place Index exists yet).
  - Seeded farmers carry placeholder numbers `+9199999xxxxx` and `synthetic=true`; Phase 4+ senders must skip synthetic farmers.
  - `Booking` also stores `village_id`, `lat`, `lng` (cluster bonus and stop ordering need them).
  - Added settings: `DDB_ENDPOINT_URL`, `DISTRICT`, `DISTRICT_BBOX` (approximate), `SEASON_START`, `HARVEST_LOOKBACK_DAYS`, `FIRMS_SOURCE/YEARS/DAY_RANGE`, matcher weights.
  - `clearsky/local.py`: in-process moto DynamoDB for offline dev (`--local` on scripts). Docker isn't running, so DynamoDB Local wasn't used.
- **Next:** deploy approval → `make seed`; FIRMS key → `make firms` then `fetch_firms.py --apply-db --upload`.

## Phase 2 log: Matching & booking engine
- **Built:** `domain/pricing.py` (§5, demo rates, ₹10 rounding); `domain/matching.py`: `find_candidates`, `choose_buyer`, `book_pickup`, `cancel_booking`, `reschedule`, `recompute_stop_order` (nearest neighbour), `has_capacity_before_deadline`, `Booked`/`NoSlot` results; single TransactWriteItems commit with retry on the next-best candidate; `scripts/book_all.py [--dry-run] [--local]`.
- **Demo values used (default OK in PLAN; labeled demo):** baling ₹600/acre, transport ₹8/tonne-km, platform fee ₹50/tonne, buyer prices ₹1,500–1,900/tonne.
- **Commands run:** `.\make.ps1 cov` → matching 94%, pricing 100%; `book_all.py --local --dry-run` and `--local` → 41 unbooked fields: 40 booked, 1 no slot.
- **Tests:** nearest baler · capacity (next day / other baler) · deadline (window and no-capacity) · cluster bonus · inactive/out-of-radius balers · buyer net price, skip full/out-of-radius buyers · no-buyer booking = free clearance · **concurrency: stale-read race → exactly one booking** · cancel frees capacity and reservation · idempotent re-booking · reschedule · oversized field · stop order.
- **Deviations:**
  - DynamoDB conditions can't do arithmetic, so the buyer update pins `demand_tonnes = :demand` and checks `reserved_tonnes <= :demand − tonnes` computed from the value read.
  - A field larger than a baler's daily capacity may book only an empty day (otherwise it could never be booked).
  - Booking an already-booked field returns the existing booking (`already_booked=true`) instead of an error, so model retries are safe.
  - When no buyer has room, the booking still happens with `buyer_id=None` and payout 0 ("free clearance") (PLAN default).
- **Not yet done:** `book_all --dry-run` against the dev tables (needs deploy).

## Phase 3 log: Farmer agent + local chat CLI
- **Built:** `agent/prompts.py` (farmer-only system prompt; today + weekday injected), `agent/tools.py` (9 tools; validation in code; ownership checks), `agent/agent.py` (`build_tools` closes over the phone, `build_agent`, `run_turn` → `AgentReply{text, booking, tool_calls, latency_ms, error}`; polite fallback on model errors), `agent/memory.py` (last 10 turns → alternating Bedrock messages), `scripts/chat_cli.py` (`--local`, `--today`, `--debug`, `--transcript`, `--model-id`, `-m`).
- **Tests:** tools reject acres 0/0.4/101/non-numeric, too-old / out-of-season / malformed dates, unknown village, unregistered farmer · **phone isolation** (B can't book, confirm, reschedule, cancel or see A's data; no tool exposes `phone`) · scripted-model run of the PLAN message books in one turn with "2026-10-25" in the reply · history on the second turn · off-topic makes no tool calls · model failure → fallback · missing model ID → config error.
- **Not yet done (needs team):** live `make chat` check with a real Bedrock model; `docs/agent_transcripts.md` (5 real transcripts) — run the commands in CONTEXT.md once a model ID is set.
- **Deviations:**
  - No role router (WhatsApp is farmer-only, per 2026-10-07 decision); `run_turn` handles new and known farmers.
  - Harvest dates more than `HARVEST_LOOKBACK_DAYS` (15) in the past are rejected ("past dates" test); recent past dates register as HARVESTED.
  - `register_field` is idempotent for identical calls (model retries).
  - Strands 1.58.1 API matched the design; history is passed via `Agent(messages=…)`, `callback_handler=None`.
- **Next:** set `BEDROCK_MODEL_ID` → `.\make.ps1 chat` → record transcripts → Phase 4 when asked.

## Phase 4 log: WhatsApp + voice (built 2026-10-09)
- **Built:** `channels/whatsapp.py` (verify challenge, HMAC signature, payload parser for text/audio/button/template-button/location/status, Graph client with retries, media download); `channels/notify.py` (single outbound path, `WA_MODE` simulator/cloud, synthetic-farmer guard, 24-hour rule → template vs interactive); `channels/templates.py` + `docs/whatsapp_templates.md`; `channels/voice.py` (Ogg duration check, Amazon Transcribe or OpenAI-compatible STT, Polly mp3 → S3 presigned); `handlers/webhook.py` (dedupe via `ProcessedMessages`, SQS or inline); `handlers/processor.py` (text/voice/buttons/location, rate limit, voice reply); SAM: `InboundQueue` + DLQ, `WebhookFunction`, `ProcessorFunction` (batch 1, partial-batch failures), alarms; `scripts/e2e.py`.
- **Tests:** signature valid/invalid, challenge, every payload type, Graph payload shapes and retries, media download, Ogg duration, STT providers, webhook inline + SQS paths, dedupe, buttons (confirm/later/alertbook, foreign field ignored), location, voice with/without STT, rate limit, cloud-mode rules (synthetic skip, template outside 24 h, buttons inside).
- **Deviations:** Bedrock replaced by a provider switch (`LLM_PROVIDER`) because the account has no usable Bedrock access (team decision 2026-10-09); `rules` bot is the default and the fallback. Transcribe is optional (`STT_PROVIDER`). `WA_MODE=simulator` added so the full loop runs without Meta.
- **Not yet done (needs team):** Meta app, WA secrets in SSM, test numbers, template approval, deploy, `scripts/e2e.py` against the stack, real voice note.

## Phase 5 log: REST API, Cognito, reminders (built 2026-10-09)
- **Built:** `handlers/api.py` (Powertools resolver; officer/buyer/operator routes, JSON errors, CORS), `auth.py` (Cognito claims; `DEV_AUTH` tokens for local only), `matching.mark_done` (DONE + CLEARED + buyer received in one transaction) + farmer "field cleared" message, `handlers/reminders.py` (once per day, templates/buttons), SAM: Cognito user pool + client + 3 groups + custom attributes, JWT authorizer, `ApiFunction`, `RemindersFunction` (18:00 Asia/Kolkata), scoped IAM policy; `scripts/create_demo_users.py`; `scripts/dev_server.py` (Lambda handlers behind a local HTTP server).
- **Tests:** auth 401/403, dev login off by default, Cognito claim parsing, operator isolation (another baler's booking → 403), done flow, capacity/availability update, buyer supply/demand validation, reminders selection + once-per-day.
- **Deviations:** officer = super admin with extra tables (`/api/balers`, `/api/buyers`, `/api/bookings`); `/api/me`; `/api/operator/me.next_stop_date`.

## Phase 6 log: Risk engine + alerts (built 2026-10-09)
- **Built:** `domain/risk.py` (score, level, reasons; field refresh; village aggregates; `run_all`), `handlers/risk_job.py` (hourly ScheduleV2), risk set to GREEN inside the booking transaction, re-score on cancel/confirm/no-slot, `domain/alerts.py` (30-min cooldown, WhatsApp offer with one-tap button, `balers_flagged`), `domain/stats.py`.
- **Tests:** formula + thresholds, booked/cleared/fire, damping, ≥ 5 RED fields with fire history (DoD), alert recipients + cooldown + operator visibility, HAAN → booked → GREEN in one request (DoD).
- **Deviation:** RED threshold 70 → **60** (configurable). With 70 a bookable field could never be RED (max 68 at 3 days to sowing), contradicting the DoD. Seed RED candidates now have 3–6 days to sowing. Without FIRMS data no bookable field reaches RED.

## Phase 7 log: Dashboard (built 2026-10-09)
- **Built:** `dashboard/` (Vite 8, React 19, TS strict, Tailwind v4, React Router 8, TanStack Query, MapLibre 6, Recharts 3, Amplify Auth v6). Design system measured from `designs/` → `docs/design-system.md`, tokens only in `src/styles.css`. Screens: login (dev role picker / Cognito), officer radar (KPIs, map, villages by risk, alert dialog, field drawer), fields/bookings/balers/buyers tables, demo controls, buyer supply, operator route (phone-first), public impact, docked farmer simulator (with inbox of alerted farmers). `amplify.yml`.
- **Verified:** `npm run typecheck`, `npm test` (8), `npm run build`, Playwright smoke (3: officer alert, simulator booking, operator Done) against the local stack; screenshots checked at 1440 px and 390 px.
- **Deviations:** deck.gl dropped (MapLibre layers are enough; TripsLayer animation is a video-only extra); basemap OpenFreeMap positron by default (CARTO now needs a key); MapLibre 6 worker URL set via Vite `?worker&url`.

## Phase 8 log: Satellite (not started)
- Stretch goal; skipped per the cut line. FIRMS fire history (Phase 1) covers the "where do fires happen" layer.

## Phase 9 log: Demo mode + docs (partly, 2026-10-09)
- **Built:** `/api/demo/clock`, `/api/demo/simulate` (`harvest_wave`, `run_risk`, `run_reminders`, `reset`), demo controls page, `scripts/demo_clock.py`, `docs/demo_runbook.md`.
- **Not done (team):** run the runbook 3× on the deployed stack, record the video, write/publish the blog, submission checklist.
