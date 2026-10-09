# clearsky: Project Context

> **For AI assistants and teammates.** Read this first. It is the short, current picture of the project. For full detail, follow the links.
>
> **Update rules (mandatory after every change, code or docs):**
> 1. Edit **Current state** if what exists or works has changed.
> 2. Add or change rows in **Decisions** if a design choice was made or reversed.
> 3. Move items in and out of **Open questions** as they're asked and answered.
> 4. Add one line at the **top** of **Changelog**: `YYYY-MM-DD · who/tool · what changed · files`.
> 5. Keep it short. Detail belongs in `IMPLEMENTATION.md` / `PLAN.md` / `PROGRESS.md`; this file links to them.

_Last updated: 2026-10-09_

---

## 1. What clearsky is (one paragraph)

clearsky stops paddy stubble burning in Punjab/Haryana by fixing the logistics: a farmer tells a **WhatsApp agent** (Hindi/Punjabi voice or text) their village, acres and harvest date; the backend **books the nearest free baler** before the wheat-sowing deadline and **routes the straw to a paying buyer**. Baler operators, buyers and district officers use a **web dashboard**; officers get a **Burn Risk Radar** of fields that are harvested but not booked, and can alert a village with one click. Built for WeMakeDevs × AWS Environmental Hacks, **Oct 8–11, 2026** (Air track).

## 2. Current state

| Area | State |
|---|---|
| Phases 0–7, 9 | 🟡 **Code complete and tested locally end to end.** Every remaining DoD item needs a team input (LLM key, AWS deploy, Meta/WhatsApp, FIRMS key). Phase 8 (satellite, stretch) not started. |
| GitHub issues | 🟡 Issues #2 are implemented on this branch (2026-10-09). The work is split into stacked branches: `issue-2-role-apps-routing` → `issue-1-registration-approval` → `issue-3-baler-accept-decline` → `issue-5-pollution-avoided` → `feature/separate-role-logins`; each builds on the one before. What was verified: `PROGRESS.md` (issue log). |
| Backend | `backend/src/clearsky`: config, clock, models, repos (11 tables), matcher, pricing, risk, alerts, stats, demo, FIRMS, seed; **farmer agent** (Strands, any LLM via `LLM_PROVIDER`, plus a deterministic **rules bot** default/fallback); WhatsApp channel (`whatsapp`, `notify`, `voice`, `templates`); Lambdas: webhook, processor, api, risk_job, reminders, health, firms_ingest; `auth.py`. Test counts: `PROGRESS.md`. |
| Dashboard | `dashboard/`: **three role apps**, each with its own layout, nav, 404 and lazy chunk (`src/apps/<role>/`): **Admin** `/admin` (radar + Fields/Bookings/Balers/Buyers/Demo, docked **farmer simulator**), **Baler** `/baler` (phone-first: Today/Schedule/History/Profile), **Buyer** `/buyer` (Overview/Deliveries + CSV/Demand + history/Profile); public `/impact`, `/login`. Design system from `designs/` → `docs/design-system.md`. |
| Infra | `infra/template.yaml`: tables, buckets, SQS + DLQ, Cognito (officer/buyer/operator), JWT HTTP API, 7 functions, hourly + 18:00 IST schedules, alarms, deps layer. `sam validate --lint` ✅, `sam build` ✅. **Nothing deployed.** |
| Data | `data/seed/*.json` (seed 42): 31 places (approx coords), 10 balers, 3 fictional buyers, 60 synthetic fields (10 RED candidates: 3–6 days to sowing). No FIRMS layer yet. |
| AWS account | Friend's account 416121583611, ap-south-1. **The access key on the dev laptop now fails (`InvalidClientTokenId`) → new key needed.** Bedrock unusable → LLM API key instead. Transcribe was `SubscriptionRequired` → optional (`STT_PROVIDER`). Polly Kajal ✅ (2026-10-07). |
| Git | Remote `https://github.com/sanskarjoshiii/clearsky`. `main` pushed; issues #1–#5 tracked on GitHub (texts also in `docs/issues/`). Issues #2 are on this branch; #4 (production setup) is assigned to @akkki007. |
| Dev machine | Windows: no `make`/`sam`/Docker → `.\make.ps1`; uv provides Python 3.12; local stack uses an in-process moto DynamoDB. Windows Application Control blocked `backend\.venv\Scripts\python.exe` for a while on 2026-10-09 and later let it run again; if `uv run` fails with "os error 4551", that is the cause. |

Phase status (mirror of `PROGRESS.md`): 0 🟡 · 1 🟡 · 2 🟡 · 3 🟡 · 4 🟡 · 5 🟡 · 6 🟡 · 7 🟡 · 8 ⬜ (stretch) · 9 🟡

### How to run things (Windows: `.\make.ps1 X`; macOS/Linux: `make X`)
- **Whole system locally, no keys:** `dev` (API on :8787: mock DB + seed + simulator + dev login) and `dashboard` (http://localhost:5173). Dev URLs: `/admin?as=officer.Sangrur&sim=1`, `/baler?as=operator.B01`, `/buyer?as=buyer.BY03`. Old `/officer…` and `/operator` links redirect.
- `install` · `lint` · `format` · `test` · `cov` · `e2e` · `validate` · `build` (layer + sam build) · `check-aws`
- `chat`: farmer agent in the terminal (rules bot, or the LLM configured in `.env`). `book-all`: matcher dry run. `gen-seed`. `seed` (deployed tables). `firms` (needs MAP_KEY or CSVs).
- `deploy` refuses without `CONFIRM=yes` / `-Confirm yes` (team approval).
- Everything the team must do by hand: **`SETUP_GUIDE.md`** (step by step, with a reply template).

## 3. Architecture in brief

- **Monorepo** (`README.md` §9): `backend/` (Python 3.12, package `clearsky`, uv), `infra/` (AWS SAM), `dashboard/` (Vite + React 19 + TS + Tailwind v4 + MapLibre), `data/`, `docs/`, `designs/` (UI references), `.agents/skills/` (design skill). `Makefile` + `make.ps1`.
- **WhatsApp → farmers only:** Meta webhook → API Gateway → λ `webhook` (signature, dedupe) → SQS → λ `processor` → STT (Transcribe or OpenAI-compatible) → **farmer agent** → reply text (+ Polly voice). `WA_MODE=simulator` records messages for the dashboard's farmer simulator instead of sending; synthetic (seed/test) farmers are never messaged.
- **Agent** (`agent/`): `LLM_PROVIDER` = `rules` (default, no LLM) | `openai` (+ any OpenAI-compatible via `LLM_BASE_URL`) | `anthropic` | `gemini` | `bedrock`. Same 9 tools for all; tools close over the verified phone; the rules bot answers if the LLM fails.
- **Risk** (`domain/risk.py`): RED ≥ 60 (changed from 70, see `IMPLEMENTATION.md` §6), YELLOW ≥ 40. Red needs FIRMS fire history or "no baler free".
- **Matcher** (`domain/matching.py`): baler-day by distance + delay − village-cluster bonus; buyer by net price; one DynamoDB transaction (capacity, booking, field, buyer) prevents double booking; retries next-best on conflict.
- **Dashboard (Cognito groups `officer`, `buyer`, `operator`; UI names Admin / Baler / Buyer):** `/admin/*` · `/baler/*` (simple, mobile) · `/buyer/*` · `/impact`. One router, three lazy apps (`src/App.tsx`); `homeFor(role)` is the single source of landing pages; `RequireRole` handles signed-out (→ login → back) and wrong role (→ own home + notice).
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
| 2026-10-09 | The local dev server handles one request at a time (lock). | The Powertools resolver keeps the current event on a shared object; parallel browser requests could read each other's token/query (found by Playwright) | `backend/scripts/dev_server.py` |

## 5. Open questions (ask the team; don't guess)

How to get each answer, step by step: **`SETUP_GUIDE.md`** (it ends with a fill-in reply template).

- **LLM provider + model ID + API key** (`LLM_PROVIDER`, `LLM_MODEL_ID`, `LLM_API_KEY`). Until then the rules bot answers.
- **Speech-to-text choice**: enable Transcribe, or an OpenAI-compatible STT model, or none.
- **New AWS access key** for the dev laptop (old key revoked), then **deploy approval** (`clearsky-dev`, ap-south-1), `seed`, Cognito users, Amplify.
- **Meta WhatsApp Cloud API**: app, phone number id, permanent token, app secret, verify token, test recipients (≤ 5 farmer phones), template approval.
- **NASA FIRMS MAP_KEY** (or archive CSVs): needed for fire history → red risk.
- **Village list** confirmation (31 in `data/seed/villages.json`, approx coords) and **demo prices**.
- Emission factor with a source citation, or keep emissions off the impact page.
- Video, blog, submission (Phase 9 team tasks).

## 6. Team

| Member | Owns |
|---|---|
| Akshay | WhatsApp farmer bot + agent |
| P2 | Matcher, bookings, data, REST API |
| P3 | Dashboard (radar, buyer, operator) |
| P4 | Video, blog, testing |

## 7. Changelog (newest first)

- 2026-10-09 · Claude Code · **Issue #2** (role apps + routing): pages moved with `git mv` into `dashboard/src/apps/{admin,baler,buyer}`; lazy route chunks; `RequireRole` (login → back to the requested URL; wrong role → own home + notice); `/officer/*` and `/operator` redirect; baler app phone-first with Schedule / History / Profile; buyer app with Deliveries (CSV), Demand (history), Profile; new endpoints `/api/operator/me/schedule`, `/history`, `/api/buyers/me/demand/history`, operator profile fields; Vitest scoped to `src/`; dev server serialises requests · `dashboard/src/**`, `dashboard/e2e/*`, `dashboard/vite.config.ts`, `backend/src/clearsky/handlers/api.py`, `backend/src/clearsky/repo/settings_repo.py`, `backend/scripts/dev_server.py`, `backend/tests/test_api.py`, docs

- 2026-10-09 · Claude Code · Pushed all local commits to `main`; created GitHub issues from `docs/issues/` (@kamranp03: registration/approval, role apps + routing, baler accept/reject, pollution impact; @akkki007: production setup + WhatsApp on own number) · `CONTEXT.md`

- 2026-10-09 · Claude Code · Name is lowercase **clearsky** everywhere (docs, UI, bot replies); logo `logo.png` added, shown as a circle (`dashboard/public/logo.png`, favicon, rail, login, impact, README); login role rows no longer overflow · 33 files + `dashboard/public/*`, `logo.png`

- 2026-10-09 · Claude Code · Wrote 4 GitHub issues as `docs/issues/*.md` + `scripts/create_github_issues.ps1`. @kamranp03: (1) baler/buyer self-registration with super-admin approval, (2) separate admin/baler/buyer apps and routing, (3) baler accepts/declines assigned fields (offer → accept/decline → reassign), (5) sourced pollution-avoided per cleared field + public impact page with a model-style impact table (ref designs/modelling-1.jpg). @akkki007: (4) production setup end to end (AWS deploy, LLM key, WhatsApp on our own number), then remove the farmer simulator. SETUP_GUIDE §7.4b added · `docs/issues/*`, `scripts/create_github_issues.ps1`, `SETUP_GUIDE.md`, `CONTEXT.md`
- 2026-10-09 · Claude Code · Implemented Phases 4–7 and 9 (code): provider-agnostic LLM + rules bot; WhatsApp webhook/processor/notify/voice/templates with simulator mode; REST API with Cognito roles + dev auth; risk engine (RED ≥ 60), alerts, reminders, stats, demo mode; SAM for all of it; local dev server; dashboard (design system from `designs/`, officer super-admin, buyer, operator, impact, farmer simulator); Playwright smoke tests; docs: `SETUP_GUIDE.md` rewritten for the LLM-key path + Meta + Amplify, `docs/design-system.md`, `docs/demo_runbook.md`, `docs/whatsapp_templates.md`, `dashboard/README.md`; PROGRESS/IMPLEMENTATION/README updated · `backend/**`, `dashboard/**`, `infra/template.yaml`, `scripts/put_secrets.*`, `docs/**`, `Makefile`, `make.ps1`, root docs
- 2026-10-08 · Claude Code · Added `SETUP_GUIDE.md` (AWS access on the friend's account, Bedrock model, Transcribe activation, deploy, FIRMS key, villages, prices, demo phone numbers, GitHub) and linked it from README; `git init` on `main` + first commit; push pending a remote URL · `SETUP_GUIDE.md`, `README.md`, `CONTEXT.md`
- 2026-10-07 · Claude Code · Implemented Phases 0–3: backend package (config, clock, logging, models, repos, matcher, pricing, villages, FIRMS, seed, farmer agent), SAM template (tables, buckets, health API, FIRMS ingest, deps layer), scripts (check_aws, gen_seed, seed_dynamo, fetch_firms, book_all, chat_cli), Makefile + make.ps1, 93 tests; generated `data/seed`; PROGRESS.md created; README setup, IMPLEMENTATION §3.2/§4/§13/§14/§16 updated with as-built details · `backend/**`, `infra/**`, `data/seed/**`, `Makefile`, `make.ps1`, `.env.example`, `.gitignore`, `scripts/put_secrets.sh`, `PROGRESS.md`, `README.md`, `IMPLEMENTATION.md`, `CLAUDE.md`, `CONTEXT.md`
- 2026-10-07 · Claude Code · Renamed project to clearsky everywhere (fixed `clearsky ` trailing-space identifiers); made monorepo explicit; WhatsApp now farmer-only; baler operators moved to a simple Cognito dashboard; updated Phase 3–7 and 9 tasks accordingly; added `CONTEXT.md` and `AGENTS.md`; added "update CONTEXT.md after every change" rule · `README.md`, `IMPLEMENTATION.md`, `PLAN.md`, `CLAUDE.md`, `AGENTS.md`, `CONTEXT.md`
