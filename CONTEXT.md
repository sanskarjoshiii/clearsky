# clearsky: Project Context

> **For AI assistants and teammates.** Read this first. It is the short, current picture of the project. For full detail, follow the links.
>
> **Update rules (mandatory after every change, code or docs):**
> 1. Edit **Current state** if what exists or works has changed.
> 2. Add or change rows in **Decisions** if a design choice was made or reversed.
> 3. Move items in and out of **Open questions** as they're asked and answered.
> 4. Add one line at the **top** of **Changelog**: `YYYY-MM-DD · who/tool · what changed · files`.
> 5. Keep it short. Detail belongs in `IMPLEMENTATION.md` / `PLAN.md` / `PROGRESS.md`; this file links to them.

_Last updated: 2026-10-10_

---

## 1. What clearsky is (one paragraph)

clearsky stops paddy stubble burning in Punjab/Haryana by fixing the logistics: a farmer tells a **WhatsApp agent** (Hindi/Punjabi voice or text) their village, acres and harvest date; the backend **books the nearest free baler** before the wheat-sowing deadline and **routes the straw to a paying buyer**. Baler operators, buyers and district officers use a **web dashboard**; officers get a **Burn Risk Radar** of fields that are harvested but not booked, and can alert a village with one click. Built for WeMakeDevs × AWS Environmental Hacks, **Oct 8–11, 2026** (Air track).

## 2. Current state

| Area | State |
|---|---|
| Phases 0–7, 9 | 🟡 **Code complete and tested locally end to end.** Every remaining DoD item needs a team input (LLM key, AWS deploy, Meta/WhatsApp, FIRMS key). Phase 8 (satellite, stretch) not started. |
| GitHub issues | ✅ Issues #2, #1, #3 and #5 are **merged to `main`** (PRs #6, #10, #7, #9 + follow-up #8 separate sign-in pages, 2026-10-10) and closed. Open: **#4** production setup (@akkki007). **#5 has no numbers yet: the team must supply sourced emission factors.** What was verified: `PROGRESS.md` (issue log). |
| Backend | `backend/src/clearsky`: config, clock, models, repos (11 tables), matcher, pricing, risk, alerts, stats, demo, FIRMS, seed; **farmer agent** (Strands, any LLM via `LLM_PROVIDER`, plus a deterministic **rules bot** default/fallback); WhatsApp channel (`whatsapp`, `notify`, `voice`, `templates`); Lambdas: webhook, processor, api, risk_job, reminders, **offers_job**, health, firms_ingest; `auth.py`; `domain/registration.py`, `domain/offers.py`, `domain/impact.py`. Test counts: `PROGRESS.md`. |
| Dashboard | `dashboard/`: **three role apps**, each with its own layout, nav, 404 and lazy chunk (`src/apps/<role>/`): **Admin** `/admin` (radar + Fields/Bookings/Balers/Buyers/Approvals/Demo, docked **farmer simulator**), **Baler** `/baler` (phone-first: Today/Schedule/History/Profile), **Buyer** `/buyer` (Overview/Deliveries + CSV/Demand + history/Profile); public `/impact`, `/login`, `/register`, `/pending`. Design system from `designs/` → `docs/design-system.md`. |
| Offers | A booking is first an **offer** to the best baler (`OFFERED`, capacity reserved). The baler accepts or declines on `/baler/requests`; decline / no answer in `OFFER_SLA_MINUTES` → next baler; after `OFFER_MAX_ATTEMPTS` → radar "no baler accepted" + farmer told. The farmer hears ✅ only on accept. `AUTO_ACCEPT_DEMO=true` restores instant booking. |
| Impact | Pollution avoided = straw tonnes × sourced emission factor, snapshotted on each `DONE` booking; public table at `/impact`. **`EMISSION_FACTORS` is empty: nothing is shown until the team provides published values.** |
| Registration | Balers and buyers **register themselves** (Cognito self sign-up → application form → `/pending`); the officer approves or rejects on `/admin/approvals`. Approval creates the `Baler`/`Buyer` row + Cognito group/attribute. Works locally with dev auth. |
| Infra | `infra/template.yaml`: 12 tables (incl. `Applications`), buckets, SQS + DLQ, Cognito (officer/buyer/operator; **self sign-up on**), JWT HTTP API (+ public `/api/stats`, `/api/impact`), 8 functions (incl. `OffersJobFunction`, every 15 min), hourly + 18:00 IST schedules, alarms, deps layer, parameter `EmissionFactors`. **Deployed 2026-10-10** as `clearsky-dev`. `sam validate --lint` passes (2026-10-10). |
| Data | `data/seed/*.json` (seed 42): 31 places (approx coords), 10 balers, 3 fictional buyers, 60 synthetic fields (10 RED candidates: 3–6 days to sowing). No FIRMS layer yet. |
| AWS account | **Akshay's account 370042934648, ap-south-1** (replaces the friend's 416121583611, whose key failed). Shared IAM user **`clearsky-dev`** (AdministratorAccess, tagged `expires=2026-10-12`; **delete after the hackathon**) with one access key, handed to the team privately, never in Git. Budget `clearsky-monthly-10usd` emails at 80% actual / 100% forecast. **Stack `clearsky-dev` deployed 2026-10-10** (OpenAI gpt-4o-mini, WhatsApp cloud mode; outputs in the changelog). Bedrock unusable → LLM API key instead. **Transcribe ✅ and Polly Kajal ✅ on this account (2026-10-10)**; `STT_PROVIDER=transcribe` chosen. Local-dev media bucket `clearsky-dev-media-local-370042934648` (delete after deploy). |
| Git | Remote `https://github.com/sanskarjoshiii/clearsky`. `main` pushed; issues #1–#5 tracked on GitHub (texts also in `docs/issues/`). Issues #1, #2, #3, #5 merged to `main` and closed; #4 (production setup) is open, assigned to @akkki007. |
| Dev machine | Windows: no `make`/`sam`/Docker → `.\make.ps1`; uv provides Python 3.12; local stack uses an in-process moto DynamoDB. Windows Application Control blocked `backend\.venv\Scripts\python.exe` for a while on 2026-10-09 and later let it run again; if `uv run` fails with "os error 4551", that is the cause. |

Phase status (mirror of `PROGRESS.md`): 0 🟡 · 1 🟡 · 2 🟡 · 3 🟡 · 4 🟡 · 5 🟡 · 6 🟡 · 7 🟡 · 8 ⬜ (stretch) · 9 🟡

### How to run things (Windows: `.\make.ps1 X`; macOS/Linux: `make X`)
- **Whole system locally, no keys:** `dev` (API on :8787: mock DB + seed + simulator + dev login) and `dashboard` (http://localhost:5173). Sign in at `/admin/login` (`admin@clearsky.local`), `/baler/login` (`b01@clearsky.local`), `/buyer/login` (`by01@clearsky.local`), password `clearsky-dev` (`DEV_PASSWORD`). Dev shortcut URLs still work: `/admin?as=officer.Sangrur&sim=1`, `/baler?as=operator.B01`, `/buyer?as=buyer.BY03`; `/register` (new applicant). Old `/officer…` and `/operator` links redirect.
- `install` · `lint` · `format` · `test` · `cov` · `e2e` · `validate` · `build` (layer + sam build) · `check-aws`
- `dev-cloud`: like `dev` but real WhatsApp (WA_* from `.env`); tunnel with `ngrok http 8787` for Meta's webhook (SETUP_GUIDE §7.0).
- `chat`: farmer agent in the terminal (rules bot, or the LLM configured in `.env`). `book-all`: matcher dry run. `gen-seed`. `seed` (deployed tables). `firms` (needs MAP_KEY or CSVs).
- `deploy` refuses without `CONFIRM=yes` / `-Confirm yes` (team approval).
- Everything the team must do by hand: **`SETUP_GUIDE.md`** (step by step, with a reply template).

## 3. Architecture in brief

- **Monorepo** (`README.md` §9): `backend/` (Python 3.12, package `clearsky`, uv), `infra/` (AWS SAM), `dashboard/` (Vite + React 19 + TS + Tailwind v4 + MapLibre), `data/`, `docs/`, `designs/` (UI references), `.agents/skills/` (design skill). `Makefile` + `make.ps1`.
- **WhatsApp → farmers only:** Meta webhook → API Gateway → λ `webhook` (signature, dedupe) → SQS → λ `processor` → STT (Transcribe or OpenAI-compatible) → **farmer agent** → reply text (+ Polly voice). `WA_MODE=simulator` records messages for the dashboard's farmer simulator instead of sending; synthetic (seed/test) farmers are never messaged.
- **Agent** (`agent/`): `LLM_PROVIDER` = `rules` (default, no LLM) | `openai` (+ any OpenAI-compatible via `LLM_BASE_URL`) | `anthropic` | `gemini` | `bedrock`. Same 9 tools for all; tools close over the verified phone; the rules bot answers if the LLM fails.
- **Risk** (`domain/risk.py`): RED ≥ 60 (changed from 70, see `IMPLEMENTATION.md` §6), YELLOW ≥ 40. Red needs FIRMS fire history or "no baler free".
- **Matcher** (`domain/matching.py`): baler-day by distance + delay − village-cluster bonus; buyer by net price; one DynamoDB transaction (capacity, booking, field, buyer) prevents double booking; retries next-best on conflict. The booking is written `OFFERED`; `accept_offer` / `release_offer` are conditional transactions too. `domain/offers.py` adds farmer messages, re-offer and escalation; `handlers/offers_job.py` expires unanswered offers.
- **Impact** (`domain/impact.py`): `EMISSION_FACTORS` (JSON, each factor with a source) × straw tonnes × `BURN_FRACTION`; snapshot on `mark_done`; `GET /api/impact` (public, masked names); `scripts/backfill_impact.py`.
- **Dashboard (Cognito groups `officer`, `buyer`, `operator`; UI names Admin / Baler / Buyer):** `/admin/*` · `/baler/*` (simple, mobile) · `/buyer/*` · `/impact`. One router, three lazy apps (`src/App.tsx`); `homeFor(role)` is the single source of landing pages; `RequireRole` handles signed-out (→ login → back), wrong role (→ own home + notice) and `pending` (→ `/pending`).
- **Registration:** a signed-in user in no group is `pending` (`auth.from_claims`) and may call only `/api/me` and `/api/register*`. `domain/registration.py` does submit / approve / reject / deactivate; table `Applications`.
- **Lambda packaging:** dependencies in a layer built for Linux arm64 by uv; function zip is only our code.

Full design: `IMPLEMENTATION.md`. Build order: `PLAN.md`. Phase logs and deviations: `PROGRESS.md`.

## 4. Decisions

| Date | Decision | Why | Where |
|---|---|---|---|
| 2026-10-09 | **LLM via API key**, provider-agnostic (`LLM_PROVIDER`); deterministic **rules bot** is the default and the fallback. | Bedrock not accessible on the AWS account (team decision) | `agent/llm.py`, `agent/rules.py`, `IMPLEMENTATION.md` §7.1 |
| 2026-10-09 | Speech-to-text is pluggable (`STT_PROVIDER`: transcribe / openai / none). | Transcribe not enabled on the account | `channels/voice.py` |
| 2026-10-09 | `WA_MODE=simulator` + dashboard farmer simulator; dev server wraps the real Lambda handlers; `DEV_AUTH` role picker locally only. | Full loop testable and demoable before Meta/AWS setup | `channels/notify.py`, `scripts/dev_server.py`, `dashboard/src/components/Simulator.tsx` |
| 2026-10-09 | Risk RED threshold **60** (was 70), configurable. | With 70 a bookable field could never be RED, contradicting Phase 6 DoD | `domain/risk.py`, `IMPLEMENTATION.md` §6 |
| 2026-10-09 | Officer = government **super admin**: radar + all tables + demo controls. | User request | `handlers/api.py`, dashboard |
| 2026-10-09 | Dashboard design system measured from `designs/`: violet = WhatsApp agent, green/amber/red = risk only, teal = straw, ink buttons, hairlines. MapLibre only (deck.gl dropped); OpenFreeMap basemap by default. | Reference taste; fewer deps; CARTO now needs a key | `docs/design-system.md`, `dashboard/src/styles.css` |
| 2026-10-09 | Phase 8 (satellite) skipped. | Stretch, cut line 1 | `PLAN.md` |
| 2026-10-07 | Dependencies ship in a Lambda **layer** built with `uv pip install --python-platform aarch64-manylinux_2_28`. | SAM's pip builder on Windows pulled the Windows-only `pywin32`; this also makes builds fast | `infra/template.yaml`, `Makefile`, `make.ps1` |
| 2026-10-07 | `make.ps1` mirrors the Makefile; SAM via `uv tool run` when not installed. | Dev machine is Windows without make/sam | `make.ps1` |
| 2026-10-07 | Offline dev uses an in-process moto DynamoDB (`--local`). | No deploy yet and Docker isn't running; keeps the loop testable | `backend/src/clearsky/local.py` |
| 2026-10-07 | Seeded farmers are `synthetic=true` with placeholder numbers; senders must skip them. Seeded villages are a proposal with `approx=true` coords. | Never message strangers; never present guessed coordinates as real | `seed/generate.py`, `IMPLEMENTATION.md` §14 |
| 2026-10-07 | Demo pricing: baling ₹600/acre, transport ₹8/t·km, fee ₹50/t, buyers ₹1,500–1,900/t. | PLAN default OK; labeled demo, never real prices | `config.py`, `seed/generate.py` |
| 2026-10-07 | Oversized field (> baler's acres/day) books only an empty day; re-booking a booked field returns the existing booking; buyer condition pins demand. | Feasibility, retry safety, DynamoDB condition limits | `IMPLEMENTATION.md` §4 |
| 2026-10-07 | IST is a fixed UTC+05:30 offset. | Windows lacks tzdata; India has no DST | `clock.py` |
| 2026-10-07 | Project name is **clearsky** (prose) / `clearsky` (identifiers). Previously "ParaliLink". | Team decision | All docs |
| 2026-10-07 | **Monorepo** for all parts. | One place for API + dashboard changes | `README.md` §9, `IMPLEMENTATION.md` §1.2 |
| 2026-10-07 | **WhatsApp is farmer-only.** Agent collects farmer info, books via tools, replies. | Keep the bot focused | `IMPLEMENTATION.md` §1.1, §7.3, §8 |
| 2026-10-07 | **Baler operators use a simple dashboard** with Cognito login (`operator` group, `custom:baler_id`). No operator WhatsApp, no signed links. | Follows from the above | `IMPLEMENTATION.md` §2.4, §9–11 |
| 2026-10-07 | Officer village alerts **flag** nearby balers on their dashboard (`Alerts.balers_flagged`). | Follows from the above | `IMPLEMENTATION.md` §2.6 |
| (earlier) | AWS serverless stack: Lambda, API GW, SQS, DynamoDB, Bedrock + Strands, Transcribe, Polly, Location, Cognito, Amplify, SAM. | Hackathon criteria, no idle cost | `README.md` §7 |
| (earlier) | Demo district Sangrur; buyers fictional; prices labeled demo. | Honest demo data | `IMPLEMENTATION.md` §5, §14 |

| 2026-10-09 | Role apps at `/admin`, `/baler`, `/buyer`; UI says Admin / Baler / Buyer, code and Cognito keep `officer` / `operator` / `buyer`. Shared modules stay in `src/components`, `src/api`, `src/lib`, `src/auth` (not moved to `src/shared/`). | Issue #2; renaming Cognito groups would be a breaking change; moving shared folders is churn with no user benefit | `dashboard/src/apps/*`, `dashboard/src/App.tsx` |
| 2026-10-09 | Chunks split with prioritised `codeSplitting` groups (React first). | Otherwise React landed in the charts chunk and every role downloaded the charts | `dashboard/vite.config.ts` |
| 2026-10-09 | Buyer demand history lives in the `Settings` table (`demand_history#<buyer_id>`, last 20), not on the `Buyer` row. | Keeps the committed seed files byte-identical | `repo/settings_repo.py` |
| 2026-10-09 | Self-registration: Cognito self sign-up + `Applications` table; no group = `pending`; approval order row → attribute → group → `APPROVED`, each step conditional on `PENDING`; a half-finished approval is finished by pressing Approve again. Officer can deactivate a baler (`SUSPENDED`). | Issue #1; Cognito owns passwords; idempotent approval | `domain/registration.py`, `auth.py`, `infra/template.yaml` |
| 2026-10-09 | The application form has no map-pin picker; the location is the chosen village's centre (the API accepts an optional `lat`/`lng` within 25 km). The admin drawer shows the pin. | Keeps the map bundle out of the public registration page | `pages/register/ApplicationForm.tsx` |
| 2026-10-09 | The local dev server handles one request at a time (lock). | The Powertools resolver keeps the current event on a shared object; parallel browser requests could read each other's token/query (found by Playwright) | `backend/scripts/dev_server.py` |

| 2026-10-09 | Bookings start as **offers** (`OFFERED → CONFIRMED / DECLINED / EXPIRED`); capacity and buyer reservation are taken at offer time; the field is `BOOKED` (+ `booking_state`) while an offer is open. | Issue #3: a silent no-show is a burnt field | `domain/matching.py`, `domain/offers.py`, `IMPLEMENTATION.md` §3.3, §4.1 |
| 2026-10-09 | Balers that refused a field are derived from its `DECLINED`/`EXPIRED` bookings (`matching.refused_balers`), not stored as `Field.declined_balers`. A baler who let an offer **expire** is excluded too. | One source of truth; no list updates inside the transaction; no change to the seed files | `domain/matching.py` |
| 2026-10-09 | Offer reply to the farmer starts with 📨 (no ✅); ✅ comes with `booking_confirmed` on accept. Three new templates: `booking_confirmed`, `booking_changed`, `booking_delayed` (the issue listed two; the third is the "no baler accepted" follow-up). | The farmer must never be told "confirmed" before a baler accepted | `agent/rules.py`, `channels/templates.py`, `docs/whatsapp_templates.md` |
| 2026-10-09 | Engine tests (`test_matching.py`) run with `AUTO_ACCEPT_DEMO=true`; offers have their own tests (`test_offers.py`). Seed pre-bookings are confirmed (`auto_accept=True`). | Keeps the commit/capacity/stop-order tests about the engine | `backend/tests/` |
| 2026-10-09 | **No emission factor ships with clearsky.** `EMISSION_FACTORS` replaces `EMISSION_FACTOR_PM25_KG_PER_TONNE`; a factor without a source is ignored; nothing about pollution is shown until the team configures published values. Tests and Playwright use values labelled "TEST VALUE". | Project rule: never invent real-world statistics | `domain/impact.py`, `config.py`, `dashboard/playwright.config.ts` |
| 2026-10-09 | The farmer's cleared message with a PM2.5 figure is a **new** template `field_cleared_impact`, used only when a PM2.5 factor is configured; `field_cleared` is unchanged. | The issue proposed adding a parameter to `field_cleared`; a separate template keeps the existing one valid | `channels/templates.py` |
| 2026-10-09 | `/impact` is a lazy route. | It now draws a chart; keeps the chart library out of the main bundle | `dashboard/src/App.tsx` |

| 2026-10-09 | **Separate sign-in per role**: `/admin/login`, `/baler/login`, `/buyer/login`, each email + password. An account works only on its own page (another role's account gets "Wrong email or password" and is signed out). `/login` offers only baler and buyer; the admin address is linked nowhere. The all-in-one role picker is gone. Local dev credentials: `admin@clearsky.local`, `<baler id>@clearsky.local`, `<buyer id>@clearsky.local`, or the email used at registration, all with `DEV_PASSWORD` (default `clearsky-dev`). | User request: roles must not see each other | `dashboard/src/pages/Login.tsx`, `auth/AuthProvider.tsx` (`signIn`, `loginFor`), `handlers/api.py` (`_dev_credentials`) |

## 5. Open questions (ask the team; don't guess)

How to get each answer, step by step: **`SETUP_GUIDE.md`** (it ends with a fill-in reply template).

- **LLM provider + model ID + API key** (`LLM_PROVIDER`, `LLM_MODEL_ID`, `LLM_API_KEY`). Until then the rules bot answers.
- **Speech-to-text choice**: enable Transcribe, or an OpenAI-compatible STT model, or none.
- **New AWS access key** for the dev laptop (old key revoked), then **deploy approval** (`clearsky-dev`, ap-south-1), `seed`, Cognito users, Amplify.
- **Meta WhatsApp Cloud API**: app, phone number id, permanent token, app secret, verify token, test recipients (≤ 5 farmer phones), template approval.
- **NASA FIRMS MAP_KEY** (or archive CSVs): needed for fire history → red risk.
- **Village list** confirmation (31 in `data/seed/villages.json`, approx coords) and **demo prices**.
- **Emission factors with source citations** (PM2.5 first; optionally PM10, CO, CO₂, black carbon), in kg per tonne of rice straw burnt in the open → `EMISSION_FACTORS` + the table in `README.md` §16. Until then all pollution figures stay hidden. Also: keep `BURN_FRACTION` at 1.0 ("if burnt") or supply a sourced lower value? (`SETUP_GUIDE.md` §9b)
- **Offer SLA**: are 120 minutes to answer and 3 balers before escalation right for real custom hiring centres? (`OFFER_SLA_MINUTES`, `OFFER_MAX_ATTEMPTS`)
- **Three new WhatsApp templates** (`booking_confirmed`, `booking_changed`, `booking_delayed`) and optionally `field_cleared_impact` need Meta approval (`docs/whatsapp_templates.md`).
- Should the demo video use the offer flow (baler taps Accept) or `AUTO_ACCEPT_DEMO=true`?
- Video, blog, submission (Phase 9 team tasks).

## 6. Team

| Member | Owns |
|---|---|
| Akshay | WhatsApp farmer bot + agent |
| P2 | Matcher, bookings, data, REST API |
| P3 | Dashboard (radar, buyer, operator) |
| P4 | Video, blog, testing |

## 7. Changelog (newest first)

- 2026-10-10 · Claude Code (issue #4, step F) · Stack switched to **`WaMode=cloud`**; Meta callback → `https://h5n589so32.execute-api.ap-south-1.amazonaws.com/webhook/whatsapp` (verify GET 200/403 and signed POST 200 checked against AWS) · infra/samconfig.toml
- 2026-10-10 · Claude Code (issue #4, step E) · **Dashboard live at https://clearsky.akkki.tech** (CloudFront alias + ACM cert `ab1e5a76…`, us-east-1; first cert failed on Vercel's CAA records → added `amazon.com` CAA). Backend `CorsOrigins=https://clearsky.akkki.tech` (verified: other origins get no CORS header) · infra/samconfig.toml, SETUP_GUIDE.md §6a
- 2026-10-10 · Claude Code (issue #4, step E) · Dashboard hosted on **S3 + CloudFront** instead of Amplify (no repo-owner access needed): stack `clearsky-dev-web` (`infra/web.yaml`), `make web-deploy`, live at https://d2spj2b1ns3qsi.cloudfront.net (Cognito mode). ACM cert for clearsky.akkki.tech requested (us-east-1), waiting on Vercel DNS records. Fixed CORS preflight 401: added `OPTIONS /api/{proxy+}` route without authorizer. Restored committed `dashboard/package-lock.json` (a stray local npm install had dropped test deps) · infra/web.yaml, infra/template.yaml, Makefile, SETUP_GUIDE.md §6a
- 2026-10-10 · Claude Code (issue #4, steps B+E) · Officer login created in Cognito (akshaynazare3@gmail.com, district Sangrur; password kept outside the repo); verified sign-in → `/api/me` role officer. Stack switched to `LlmProvider=openai LlmModelId=gpt-4o-mini` (UPDATE_COMPLETE, Lambda env confirmed); WhatsApp still simulator mode · infra/samconfig.toml
- 2026-10-10 · Claude Code (issue #4, step D) · **Stack `clearsky-dev` deployed** to 370042934648/ap-south-1 (LlmProvider=rules, WaMode=simulator, SttProvider=transcribe). ApiUrl `https://h5n589so32.execute-api.ap-south-1.amazonaws.com`, UserPool `ap-south-1_zGnFjqKGw`, client `5gsk5tvlsbuece8gcvcg0bjuda`. Secrets → SSM, seeded (31 villages), /health ✅, /api 401 without token ✅. Pulled PRs #6–#10 first (223 tests green) · infra/samconfig.toml, CONTEXT.md
- 2026-10-10 · Claude Code (issue #4, step B) · LLM_PROVIDER=openai chosen; `.env` has empty LLM_MODEL_ID/LLM_API_KEY for Akshay to fill; `.env.example` now lists LLM_*/STT_PROVIDER · .env.example
- 2026-10-10 · Claude Code (issue #4, step C) · Voice on the new account: Transcribe ✅ + Polly Kajal ✅ (ap-south-1). Local test bucket `clearsky-dev-media-local-370042934648` (private, 1-day expiry; delete after deploy); `.env` STT_PROVIDER=transcribe. Real round trip Hindi audio → transcript ✅. Transcribe wait 60 s → `TRANSCRIBE_TIMEOUT_S` (default 90; a job took 61.6 s) · config.py, voice.py, SETUP_GUIDE.md
- 2026-10-10 · Claude Code (issue #4) · Local WhatsApp webhook: `make dev-cloud` (WA_MODE=cloud, clearsky profile) + ngrok → Meta callback `<ngrok>/webhook/whatsapp`; verified GET challenge + signed POST through the tunnel · Makefile, SETUP_GUIDE.md §7.0
- 2026-10-10 · Claude Code (issue #4, step D) · New AWS account 370042934648: created shared IAM user `clearsky-dev` (admin) + access key (kept outside the repo), $10 monthly budget alarm; SETUP_GUIDE §3 updated · CONTEXT.md, SETUP_GUIDE.md
- 2026-10-10 · Claude Code · Reviewed and tested the stacked PRs #6 → #10 → #7 → #9 → #8 (@kamranp03) on the full head: ruff + 223 pytest, dashboard typecheck + 25 Vitest + build, 13 Playwright e2e, `sam validate --lint` all green; checked auth (role only from Cognito groups, client can write only `email`, `/api/dev/login` 404 without `DEV_AUTH`). Merged all five to `main` with merge commits, pulled locally · `CONTEXT.md`
- 2026-10-09 · Claude Code · Separate sign-in page and credentials per role (`/admin/login`, `/baler/login`, `/buyer/login`); role picker removed; signed-out visitors go to their app's own login; dev registration asks for email + password; backend dev login checks email + `DEV_PASSWORD` against one role. 223 backend tests, 25 Vitest, 13 Playwright pass · `dashboard/src/{pages/Login.tsx,App.tsx,auth/*,pages/register/Register.tsx}`, `dashboard/e2e/*`, `backend/src/clearsky/{handlers/api.py,config.py}`, `backend/tests/test_api.py`, docs

- 2026-10-09 · Claude Code · Python unblocked: ran everything for issues #1, #2, #3, #5. 222 backend tests, mypy, 24 Vitest, 12 Playwright all pass. Fixed: a malformed `EMISSION_FACTORS` entry is now ignored instead of crashing settings; one impact test used the wrong history window · `backend/src/clearsky/{config.py,domain/impact.py}`, `backend/tests/test_impact.py`, `PROGRESS.md`

- 2026-10-09 · Claude Code · **Issue #5** (pollution avoided): `domain/impact.py` (sourced `EMISSION_FACTORS`, `BURN_FRACTION`, snapshot, public table), snapshot in `mark_done`, `GET /api/impact` (public), impact in stats / route / history / supply / done response, template `field_cleared_impact`, `scripts/backfill_impact.py`, SAM parameter + public route; dashboard `/impact` (per-pollutant counters, season chart, `ImpactTable`, `Sparkline`, methodology), admin Bookings column + field drawer block, baler Done toast + History, buyer KPI + Deliveries column. **No factor values included; team input needed.** Backend tests in `tests/test_impact.py` · `backend/src/clearsky/{domain/impact.py,domain/matching.py,domain/stats.py,handlers/api.py,config.py,models/entities.py,channels/templates.py}`, `backend/scripts/backfill_impact.py`, `backend/tests/test_impact.py`, `infra/template.yaml`, `.env.example`, `dashboard/src/{pages/Impact.tsx,components/ImpactTable.tsx,components/Sparkline.tsx,lib/impact.ts,…}`, docs
- 2026-10-09 · Claude Code · **Issue #3** (balers accept or decline): booking lifecycle `OFFERED → CONFIRMED | DECLINED | EXPIRED`, `domain/offers.py` (accept, decline, expire, re-offer, escalate, reassign), `handlers/offers_job.py` + 15-minute schedule, endpoints `/api/operator/me/requests`, `/api/bookings/{id}/accept|decline|reassign`, risk reasons for refusals, stats/route/supply/reminders count only confirmed work, rules bot + prompt + tools wording, 3 templates; dashboard `/baler/requests` (cards, countdown, reason picker, tab badge), admin Bookings chips + Reassign, "Offers waiting" KPI, drawer timeline; 20 offer tests + updated bot/agent/webhook tests · `backend/src/clearsky/{domain/matching.py,domain/offers.py,domain/risk.py,domain/stats.py,handlers/*,agent/*,channels/templates.py,models/*,repo/bookings.py,seed/load.py}`, `backend/tests/*`, `infra/template.yaml`, `dashboard/src/apps/**`, `dashboard/e2e/*`, docs

- 2026-10-09 · Claude Code · **Issue #1** (self-registration + approval): `pending` role, `Applications` table (schema + SAM), `domain/registration.py` (submit, approve, reject, duplicates, deactivate), endpoints `/api/register*`, `/api/applications*`, `/api/balers/{id}/active`, dev login for applicants; Cognito self sign-up on, IAM + `USER_POOL_ID` for the API function; dashboard `/register`, `/pending`, `/admin/approvals` (rail badge), Balers deactivate/reactivate; 13 backend tests (Cognito via moto), Vitest pending guard, Playwright register → approve → baler app and reject → resubmit · `backend/src/clearsky/{auth.py,config.py,domain/registration.py,handlers/api.py,models/*,repo/*}`, `backend/tests/test_registration.py`, `infra/template.yaml`, `dashboard/src/{pages/register/*,apps/admin/pages/Approvals.tsx,auth/*,api/*,pages/Login.tsx}`, `dashboard/e2e/register.spec.ts`, `IMPLEMENTATION.md`, `SETUP_GUIDE.md`, `dashboard/README.md`
- 2026-10-09 · Claude Code · **Issue #2** (role apps + routing): pages moved with `git mv` into `dashboard/src/apps/{admin,baler,buyer}`; lazy route chunks; `RequireRole` (login → back to the requested URL; wrong role → own home + notice); `/officer/*` and `/operator` redirect; baler app phone-first with Schedule / History / Profile; buyer app with Deliveries (CSV), Demand (history), Profile; new endpoints `/api/operator/me/schedule`, `/history`, `/api/buyers/me/demand/history`, operator profile fields; Vitest scoped to `src/`; dev server serialises requests · `dashboard/src/**`, `dashboard/e2e/*`, `dashboard/vite.config.ts`, `backend/src/clearsky/handlers/api.py`, `backend/src/clearsky/repo/settings_repo.py`, `backend/scripts/dev_server.py`, `backend/tests/test_api.py`, docs

- 2026-10-09 · Claude Code · Pushed all local commits to `main`; created GitHub issues from `docs/issues/` (@kamranp03: registration/approval, role apps + routing, baler accept/reject, pollution impact; @akkki007: production setup + WhatsApp on own number) · `CONTEXT.md`

- 2026-10-09 · Claude Code · Name is lowercase **clearsky** everywhere (docs, UI, bot replies); logo `logo.png` added, shown as a circle (`dashboard/public/logo.png`, favicon, rail, login, impact, README); login role rows no longer overflow · 33 files + `dashboard/public/*`, `logo.png`

- 2026-10-09 · Claude Code · Wrote 4 GitHub issues as `docs/issues/*.md` + `scripts/create_github_issues.ps1`. @kamranp03: (1) baler/buyer self-registration with super-admin approval, (2) separate admin/baler/buyer apps and routing, (3) baler accepts/declines assigned fields (offer → accept/decline → reassign), (5) sourced pollution-avoided per cleared field + public impact page with a model-style impact table (ref designs/modelling-1.jpg). @akkki007: (4) production setup end to end (AWS deploy, LLM key, WhatsApp on our own number), then remove the farmer simulator. SETUP_GUIDE §7.4b added · `docs/issues/*`, `scripts/create_github_issues.ps1`, `SETUP_GUIDE.md`, `CONTEXT.md`
- 2026-10-09 · Claude Code · Implemented Phases 4–7 and 9 (code): provider-agnostic LLM + rules bot; WhatsApp webhook/processor/notify/voice/templates with simulator mode; REST API with Cognito roles + dev auth; risk engine (RED ≥ 60), alerts, reminders, stats, demo mode; SAM for all of it; local dev server; dashboard (design system from `designs/`, officer super-admin, buyer, operator, impact, farmer simulator); Playwright smoke tests; docs: `SETUP_GUIDE.md` rewritten for the LLM-key path + Meta + Amplify, `docs/design-system.md`, `docs/demo_runbook.md`, `docs/whatsapp_templates.md`, `dashboard/README.md`; PROGRESS/IMPLEMENTATION/README updated · `backend/**`, `dashboard/**`, `infra/template.yaml`, `scripts/put_secrets.*`, `docs/**`, `Makefile`, `make.ps1`, root docs
- 2026-10-08 · Claude Code · Added `SETUP_GUIDE.md` (AWS access on the friend's account, Bedrock model, Transcribe activation, deploy, FIRMS key, villages, prices, demo phone numbers, GitHub) and linked it from README; `git init` on `main` + first commit; push pending a remote URL · `SETUP_GUIDE.md`, `README.md`, `CONTEXT.md`
- 2026-10-07 · Claude Code · Implemented Phases 0–3: backend package (config, clock, logging, models, repos, matcher, pricing, villages, FIRMS, seed, farmer agent), SAM template (tables, buckets, health API, FIRMS ingest, deps layer), scripts (check_aws, gen_seed, seed_dynamo, fetch_firms, book_all, chat_cli), Makefile + make.ps1, 93 tests; generated `data/seed`; PROGRESS.md created; README setup, IMPLEMENTATION §3.2/§4/§13/§14/§16 updated with as-built details · `backend/**`, `infra/**`, `data/seed/**`, `Makefile`, `make.ps1`, `.env.example`, `.gitignore`, `scripts/put_secrets.sh`, `PROGRESS.md`, `README.md`, `IMPLEMENTATION.md`, `CLAUDE.md`, `CONTEXT.md`
- 2026-10-07 · Claude Code · Renamed project to clearsky everywhere (fixed `clearsky ` trailing-space identifiers); made monorepo explicit; WhatsApp now farmer-only; baler operators moved to a simple Cognito dashboard; updated Phase 3–7 and 9 tasks accordingly; added `CONTEXT.md` and `AGENTS.md`; added "update CONTEXT.md after every change" rule · `README.md`, `IMPLEMENTATION.md`, `PLAN.md`, `CLAUDE.md`, `AGENTS.md`, `CONTEXT.md`
