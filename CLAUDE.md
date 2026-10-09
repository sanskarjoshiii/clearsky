# CLAUDE.md

Project: **clearsky**, a WhatsApp-first system that books straw pickup so paddy farmers don't burn stubble (AWS Environmental Hacks, Oct 8–11, 2026).

## Shape of the system
- **Monorepo:** backend, infra, dashboard, data, satellite and video all live in this one repo.
- **WhatsApp = farmers only.** The agent collects the farmer's details (name, village, acres, harvest date), books through backend tools, and replies properly. It never messages operators, buyers or officers.
- **Dashboard = everyone else.** Officers (Burn Risk Radar), buyers, and baler operators (a simple, mobile-first view: stops, map, Done, capacity/availability).

## Always
- Before any work, read `CONTEXT.md`, `README.md`, `IMPLEMENTATION.md`, `PLAN.md`, `PROGRESS.md` (once it exists).
- **After every change** (code or docs, however small), update `CONTEXT.md`: current state, decisions, open questions, and one changelog line. Teammates' AI assistants rely on it.
- When the user says **"implement phase N"**, follow `PLAN.md` §0 (Protocol) exactly: check dependencies → ask all ❓ questions in one message → implement → run the Definition of Done checks → update `PROGRESS.md` and `CONTEXT.md` → stop and summarise.
- `IMPLEMENTATION.md` is the design source of truth; `PLAN.md` decides order and scope.
- The name is always lowercase **clearsky**, in prose, UI and identifiers (package `clearsky`, stack/table prefix `clearsky-dev-`, SSM `/clearsky/{stage}/…`). The logo is `logo.png` (shown in a circle in the UI).

## Never
- Invent secrets, model IDs, phone numbers, or real-world statistics. Ask.
- Run `sam deploy` or any destructive or paid AWS action without explicit approval in this session.
- Commit `.env` or secrets.
- Start the next phase without being asked.

## Commands
- `make install` · `make lint` · `make test` · `make build` · `make validate` · `make seed` · `make chat`
- Windows (no `make`): `.\make.ps1 <same target>`; deploy needs `.\make.ps1 deploy -Confirm yes`.
- Whole stack locally, no keys: `make dev` (API :8787, mock DB, seed, WhatsApp simulator, dev login) + `make dashboard` (:5173); `make e2e` runs the Playwright smoke tests.
- Farmer agent brain: `LLM_PROVIDER` (rules | openai | anthropic | gemini | bedrock). Team setup steps: `SETUP_GUIDE.md`.
- Dashboard: `cd dashboard && npm run dev`
