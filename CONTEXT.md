# ClearSky: Project Context

> **For AI assistants and teammates.** Read this first. It is the short, current picture of the project. For full detail, follow the links.
>
> **Update rules (mandatory after every change, code or docs):**
> 1. Edit **Current state** if what exists or works has changed.
> 2. Add or change rows in **Decisions** if a design choice was made or reversed.
> 3. Move items in and out of **Open questions** as they're asked and answered.
> 4. Add one line at the **top** of **Changelog**: `YYYY-MM-DD · who/tool · what changed · files`.
> 5. Keep it short. Detail belongs in `IMPLEMENTATION.md` / `PLAN.md` / `PROGRESS.md`; this file links to them.

_Last updated: 2026-10-07_

---

## 1. What ClearSky is (one paragraph)

ClearSky stops paddy stubble burning in Punjab/Haryana by fixing the logistics: a farmer tells a **WhatsApp agent** (Hindi/Punjabi voice or text) their village, acres and harvest date; the backend **books the nearest free baler** before the wheat-sowing deadline and **routes the straw to a paying buyer**. Baler operators, buyers and district officers use a **web dashboard**; officers get a **Burn Risk Radar** of fields that are harvested but not booked, and can alert a village with one click. Built for WeMakeDevs × AWS Environmental Hacks, **Oct 8–11, 2026** (Air track).

## 2. Current state

| Area | State |
|---|---|
| Phases 0–3 | 🟡 Code complete and tested (93 tests, ruff + mypy clean, 93% coverage). Each has a DoD item waiting on the team (see §5 and `PROGRESS.md`). |
| Phases 4–9 | ⬜ Not started. Next: Phase 4 (WhatsApp + voice + first deploy) when asked. |
| Backend | `backend/src/clearsky`: config, clock, logging, models, repos (11 tables), geo, village matching, pricing, **matcher**, FIRMS, seed, **farmer agent** (Strands, 9 tools), health + FIRMS-ingest Lambdas. |
| Infra | `infra/template.yaml`: tables, 2 buckets, HTTP API `/health`, FIRMS-ingest function, dependency **layer**. `sam validate --lint` ✅, clean `sam build` ✅. **Nothing deployed.** |
| Data | `data/seed/*.json` generated (seed 42): 31 places (approx coords), 10 balers, 3 fictional buyers, 60 synthetic fields. No FIRMS layer yet. |
| AWS account | Belongs to a teammate's friend: 416121583611, ap-south-1, user Kamran_03. Credentials ✅, Polly Kajal ✅, Location ✅. **Transcribe ❌ (SubscriptionRequired). Bedrock model not chosen.** Step-by-step for the owner and devs: `SETUP_GUIDE.md`. |
| Git | Local repo on branch `main` with the first commit. **No remote yet** → push once the GitHub URL is known (`SETUP_GUIDE.md` §9). |
| Dev machine | Windows: no `make`/`sam`/Docker daemon → use `.\make.ps1`; uv provides Python 3.12; `--local` mode replaces DynamoDB. |

Phase status (mirror of `PROGRESS.md`): 0 🟡 · 1 🟡 · 2 🟡 · 3 🟡 · 4 ⬜ · 5 ⬜ · 6 ⬜ · 7 ⬜ · 8 ⬜ (stretch) · 9 ⬜

### How to run things (Windows: `.\make.ps1 X`; macOS/Linux: `make X`)
- `install` · `lint` · `format` · `test` · `cov` · `validate` · `build` (layer + sam build) · `check-aws`
- `chat`: farmer agent in the terminal on an in-process mock DynamoDB with the seed (Bedrock is real; needs `BEDROCK_MODEL_ID`).
- `book-all`: matcher dry run over the seed. `gen-seed`. `seed` (deployed tables only). `firms` (needs MAP_KEY or CSVs).
- `deploy` refuses without `CONFIRM=yes` / `-Confirm yes` (team approval).

## 3. Architecture in brief

- **Monorepo** (`README.md` §9): `backend/` (Python 3.12, package `clearsky`, uv), `infra/` (AWS SAM), `dashboard/` (Vite + React + TS, not started), `data/`, `satellite/`, `video/`. `Makefile` + `make.ps1`.
- **WhatsApp → farmers only:** Meta webhook → API Gateway → λ `webhook` → SQS → λ `processor` → Transcribe (voice) → **Strands agent on Bedrock** with booking tools → reply text (+ Polly Hindi voice). No role routing. *(Phase 4; the agent itself exists.)*
- **Agent** (`agent/`): tools close over the verified phone (never an LLM argument); validation in tools; replies only state tool results; history = last 10 turns.
- **Matcher** (`domain/matching.py`): baler-day by distance + delay − village-cluster bonus; buyer by net price; one DynamoDB transaction (capacity, booking, field, buyer) prevents double booking; retries next-best on conflict.
- **Dashboard (Cognito groups `officer`, `buyer`, `operator`):** `/officer` radar · `/buyer` · `/operator` (simple, mobile) · `/impact`. *(Phases 5–7.)*
- **Lambda packaging:** dependencies in a layer built for Linux arm64 by uv; function zip is only our code.

Full design: `IMPLEMENTATION.md`. Build order: `PLAN.md`. Phase logs and deviations: `PROGRESS.md`.

## 4. Decisions

| Date | Decision | Why | Where |
|---|---|---|---|
| 2026-10-07 | Dependencies ship in a Lambda **layer** built with `uv pip install --python-platform aarch64-manylinux_2_28`. | SAM's pip builder on Windows pulled the Windows-only `pywin32`; this also makes builds fast | `infra/template.yaml`, `Makefile`, `make.ps1` |
| 2026-10-07 | `make.ps1` mirrors the Makefile; SAM via `uv tool run` when not installed. | Dev machine is Windows without make/sam | `make.ps1` |
| 2026-10-07 | Offline dev uses an in-process moto DynamoDB (`--local`). | No deploy yet and Docker isn't running; keeps the loop testable | `backend/src/clearsky/local.py` |
| 2026-10-07 | Seeded farmers are `synthetic=true` with placeholder numbers; senders must skip them. Seeded villages are a proposal with `approx=true` coords. | Never message strangers; never present guessed coordinates as real | `seed/generate.py`, `IMPLEMENTATION.md` §14 |
| 2026-10-07 | Demo pricing: baling ₹600/acre, transport ₹8/t·km, fee ₹50/t, buyers ₹1,500–1,900/t. | PLAN default OK; labeled demo, never real prices | `config.py`, `seed/generate.py` |
| 2026-10-07 | Oversized field (> baler's acres/day) books only an empty day; re-booking a booked field returns the existing booking; buyer condition pins demand. | Feasibility, retry safety, DynamoDB condition limits | `IMPLEMENTATION.md` §4 |
| 2026-10-07 | IST is a fixed UTC+05:30 offset. | Windows lacks tzdata; India has no DST | `clock.py` |
| 2026-10-07 | Project name is **ClearSky** (prose) / `clearsky` (identifiers). Previously "ParaliLink". | Team decision | All docs |
| 2026-10-07 | **Monorepo** for all parts. | One place for API + dashboard changes | `README.md` §9, `IMPLEMENTATION.md` §1.2 |
| 2026-10-07 | **WhatsApp is farmer-only.** Agent collects farmer info, books via tools, replies. | Keep the bot focused | `IMPLEMENTATION.md` §1.1, §7.3, §8 |
| 2026-10-07 | **Baler operators use a simple dashboard** with Cognito login (`operator` group, `custom:baler_id`). No operator WhatsApp, no signed links. | Follows from the above | `IMPLEMENTATION.md` §2.4, §9–11 |
| 2026-10-07 | Officer village alerts **flag** nearby balers on their dashboard (`Alerts.balers_flagged`). | Follows from the above | `IMPLEMENTATION.md` §2.6 |
| (earlier) | AWS serverless stack: Lambda, API GW, SQS, DynamoDB, Bedrock + Strands, Transcribe, Polly, Location, Cognito, Amplify, SAM. | Hackathon criteria, no idle cost | `README.md` §7 |
| (earlier) | Demo district Sangrur; buyers fictional; prices labeled demo. | Honest demo data | `IMPLEMENTATION.md` §5, §14 |

## 5. Open questions (ask the team; don't guess)

How to get each answer, step by step: **`SETUP_GUIDE.md`** (it ends with a fill-in reply template).

- **Bedrock model ID** (with tool use) for `BEDROCK_MODEL_ID`. The account lists many models/inference profiles in ap-south-1; access must be confirmed (`check_aws.py --invoke-bedrock`, billed).
- **Amazon Transcribe** returns `SubscriptionRequiredException` on account 416121583611; needs enabling before Phase 4 voice notes.
- **Deploy approval** for the dev stack (`clearsky-dev`, ap-south-1), then `seed`.
- **NASA FIRMS MAP_KEY** (or archive CSVs in `data/raw/firms/`).
- **Village list** confirmation for Sangrur (31 proposed in `data/seed/villages.json`) and whether to geocode with Amazon Location (needs a Place Index).
- Team phone numbers for demo **farmers** (WhatsApp test recipients, ≤ 5).
- Confirm or replace demo pricing values.
- GitHub remote URL (local repo + first commit exist; nothing pushed yet).
- Later phases: WhatsApp credentials + Graph version; Cognito demo users (officer, buyer, operator → baler_id); emission factor with source.

## 6. Team

| Member | Owns |
|---|---|
| Akshay | WhatsApp farmer bot + agent |
| P2 | Matcher, bookings, data, REST API |
| P3 | Dashboard (radar, buyer, operator) |
| P4 | Video, blog, testing |

## 7. Changelog (newest first)

- 2026-10-08 · Claude Code · Added `SETUP_GUIDE.md` (AWS access on the friend's account, Bedrock model, Transcribe activation, deploy, FIRMS key, villages, prices, demo phone numbers, GitHub) and linked it from README; `git init` on `main` + first commit; push pending a remote URL · `SETUP_GUIDE.md`, `README.md`, `CONTEXT.md`
- 2026-10-07 · Claude Code · Implemented Phases 0–3: backend package (config, clock, logging, models, repos, matcher, pricing, villages, FIRMS, seed, farmer agent), SAM template (tables, buckets, health API, FIRMS ingest, deps layer), scripts (check_aws, gen_seed, seed_dynamo, fetch_firms, book_all, chat_cli), Makefile + make.ps1, 93 tests; generated `data/seed`; PROGRESS.md created; README setup, IMPLEMENTATION §3.2/§4/§13/§14/§16 updated with as-built details · `backend/**`, `infra/**`, `data/seed/**`, `Makefile`, `make.ps1`, `.env.example`, `.gitignore`, `scripts/put_secrets.sh`, `PROGRESS.md`, `README.md`, `IMPLEMENTATION.md`, `CLAUDE.md`, `CONTEXT.md`
- 2026-10-07 · Claude Code · Renamed project to ClearSky everywhere (fixed `clearsky ` trailing-space identifiers); made monorepo explicit; WhatsApp now farmer-only; baler operators moved to a simple Cognito dashboard; updated Phase 3–7 and 9 tasks accordingly; added `CONTEXT.md` and `AGENTS.md`; added "update CONTEXT.md after every change" rule · `README.md`, `IMPLEMENTATION.md`, `PLAN.md`, `CLAUDE.md`, `AGENTS.md`, `CONTEXT.md`
