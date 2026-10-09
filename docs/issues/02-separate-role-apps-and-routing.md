---
title: "Separate the super-admin, baler and buyer apps with clean role-based routing"
assignee: kamranp03
labels: [feature, dashboard, ux]
---

## Why

All three roles currently share one `Shell` and one router (`dashboard/src/App.tsx`):
- `/officer/*` has 6 pages.
- `/buyer` and `/operator` are a single page each.
- The left rail is built from `navFor(role)` in `components/Shell.tsx`.

It works, but:
- The URLs don't say who the page is for (`/officer` is really the government **super admin**; "operator" is the **baler**).
- Balers and buyers have no room to grow: there's no profile, no history and no settings pages, and the accept/reject issue needs a "Requests" area for balers.
- Every role downloads every page (MapLibre and Recharts are in the main bundle for everyone).
- Wrong-role or signed-out users are redirected, but they lose the page they asked for.

## Target information architecture

| App | Base path | Layout | Pages |
|---|---|---|---|
| **Super admin** (district officer) | `/admin` | Desktop-first: icon rail + canvas + docked farmer simulator (simulator only while `WA_MODE=simulator`) | `/admin` Radar · `/admin/fields` · `/admin/bookings` · `/admin/balers` · `/admin/buyers` · `/admin/approvals` (registration issue) · `/admin/demo` (demo mode only) |
| **Baler** (operator) | `/baler` | **Phone-first**: top bar + bottom tab bar, big touch targets, Hindi labels | `/baler` Today (route + Done) · `/baler/requests` (accept/reject issue) · `/baler/schedule` (next 14 days) · `/baler/history` (cleared fields, acres, tonnes) · `/baler/profile` (machine capacity, radius, availability, phone) |
| **Buyer** (industry) | `/buyer` | Desktop-first, lighter rail | `/buyer` Overview (KPIs + incoming chart) · `/buyer/deliveries` (table + CSV export) · `/buyer/demand` (demand/price/radius form + change history) · `/buyer/profile` |
| Public | `/`, `/impact`, `/login`, `/register`, `/pending` | Plain | |

**Redirects for old links:**
- `/officer/*` → `/admin/*`
- `/operator` → `/baler`

Keep these for at least the hackathon (the runbook, the Playwright tests and `?as=` dev links use the old paths).

## Design

### Routing
- One `createBrowserRouter`, three **lazy** route trees (`lazy: () => import("./apps/admin/routes")`). Then the buyer bundle doesn't load MapLibre unless a buyer page needs it, and the baler bundle doesn't load Recharts.
- A single guard component `RequireRole roles={[…]}` (exists in `App.tsx`) extended to:
  - remember the requested URL (`state.from`) and return there after login;
  - send `pending` users (registration issue) to `/pending`;
  - send a signed-in user on another role's URL to **their own home** with a toast ("That page is for buyers").
- `homeFor(role)` in `auth/AuthProvider.tsx` becomes the single source of each role's landing page.
- A per-app 404 that stays inside the right layout.

### Code layout
```
dashboard/src/
  apps/admin/   (layout, routes, pages moved from pages/officer/*)
  apps/baler/   (layout with bottom tabs, pages from pages/Operator.tsx split up)
  apps/buyer/   (layout, pages from pages/Buyer.tsx split up)
  shared/       (components/ui.tsx, DataTable, MapView, hooks, api) – unchanged APIs
```
Move files with `git mv` so history is kept.

### Backend
Already role-scoped: `require("officer")`, `require("buyer")`, `require("operator")` in `handlers/api.py`, and the operator's `baler_id` comes only from the token. **No URL rename is needed on the API.** New pages may need small endpoints:
- `GET /api/operator/me/history?from&to` (DONE bookings + totals)
- `GET /api/operator/me/schedule?days=14` (counts per day)
- `GET /api/buyers/me/demand/history` (needs a `DemandChanges` record or an `updated_at` trail; keep it optional)

### Naming in the UI
Use **Admin / Baler / Buyer** everywhere the user sees it. Code can keep `officer` / `operator` group names (Cognito groups are already deployed with those names; renaming them is a breaking change and not worth it).

## Edge cases
- A dev `?as=` link must still work after the move (update `AuthProvider` handling and the docs).
- The `sim=1` URL flag and `localStorage` keys (`clearsky.simOpen`, `clearsky.simPhone`) stay admin-only.
- Deep link to `/baler/requests` from a future WhatsApp/SMS notification while signed out → login → back to requests.
- Phone widths (375–390 px) for the baler app; no horizontal scroll (`docs/design-system.md` rule 7).

## Acceptance criteria
- [ ] Each role has its own base path, layout and navigation; no role sees another role's nav items.
- [ ] Visiting another role's URL redirects to your own home with a toast; signed-out → login → back to the original URL.
- [ ] Old URLs (`/officer…`, `/operator`) redirect to the new ones.
- [ ] Baler app works one-handed on a 390 px screen (bottom tabs, ≥ 44 px targets).
- [ ] `npm run build` shows separate chunks per app; the buyer chunk doesn't include MapLibre unless a buyer page uses a map.
- [ ] Vitest: guard redirects (no user, wrong role, pending). Playwright: one test per role reaches every page in its app and is blocked from the others; existing smoke tests updated to the new paths.
- [ ] `dashboard/README.md`, `docs/demo_runbook.md`, `SETUP_GUIDE.md` §0 and `CONTEXT.md` updated with the new URLs.

## Files you'll touch
`dashboard/src/App.tsx`, `components/Shell.tsx` (split into per-app layouts), `auth/AuthProvider.tsx`, everything under `pages/` (moved), `e2e/smoke.spec.ts`, docs listed above; small additions in `backend/src/clearsky/handlers/api.py` for history/schedule.
