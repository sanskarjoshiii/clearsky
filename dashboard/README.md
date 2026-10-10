# clearsky dashboard

Web app for everyone except farmers (farmers use WhatsApp):

Three role apps, each with its own base path, layout, navigation and lazy-loaded bundle (`src/apps/<role>/`). People see **Admin / Baler / Buyer**; code and Cognito keep the group names `officer` / `operator` / `buyer`.

| App | Route | What |
|---|---|---|
| **Home** (public) | `/` | Field-video hero, live stats, who it's for, how it works, register CTA (`src/pages/home/`) |
| **Admin** (district officer, super admin) | `/admin` | Burn Risk Radar: map, villages by risk, **Alert village**, field drawer |
| | `/admin/fields`, `/bookings`, `/balers`, `/buyers` | Every table, searchable |
| | `/admin/demo` | DEMO_MODE only: demo clock, harvest wave, run risk/reminders, reset, runbook |
| | side panel | WA_MODE=simulator only: **farmer simulator**, chat as a farmer through the real WhatsApp pipeline |
| **Baler** (operator), phone-first | `/baler` | Today: stop list with Call + big **Done**, route map, availability |
| | `/baler/requests` | Open offers: **Accept · स्वीकार** or **Decline · मना करें** (with a reason) before the countdown ends |
| | `/baler/schedule` | Next 14 days: stops and booked acres per day (a day opens its route) |
| | `/baler/history` | Cleared fields with season totals |
| | `/baler/profile` | Acres/day, working radius, availability, contact number, sign out |
| **Buyer** (industry) | `/buyer` | Overview: KPIs + incoming tonnes chart |
| | `/buyer/deliveries` | Deliveries table + CSV export |
| | `/buyer/demand` | Demand / price / radius form + change history |
| | `/buyer/profile` | Plant details, sign out |
| | `/admin/approvals` | Self-registered balers and buyers: table, drawer with map pin, **Approve** / **Reject (reason)**; "N pending" badge on the rail |
| Public | `/impact`, `/login` | Live counters for the video; with sourced emission factors also pollution avoided: per-pollutant totals, season chart, the impact table (village groups, trend, formula, pollutant/week columns) and its methodology; sign-in |
| Registration | `/register` | Create an account: role cards → Cognito sign-up + email code → application form |
| | `/pending` | Waiting room: under review / rejected with reason + resubmit; moves to the role app by itself on approval |

**Routing rules** (`src/App.tsx`, `src/auth/RequireRole.tsx`, `homeFor` in `src/auth/AuthProvider.tsx`):
- **Each role signs in at its own address** with email + password: `/admin/login`, `/baler/login`, `/buyer/login`. An account only works on its own page. `/login` offers baler and buyer only; the admin address is not linked from anywhere.
- Signed out → that app's login page, then back to the page that was asked for.
- Signed in on another role's URL → your own home, with a notice ("That page is for buyers.").
- Signed in but not approved yet (`pending`) → `/pending`; such a user can open only `/register` and `/pending`.
- Each app has its own 404 inside its layout.
- Old links still work: `/officer/*` → `/admin/*`, `/operator` → `/baler` (query strings such as `?as=` are kept).

Design rules and tokens: [`../docs/design-system.md`](../docs/design-system.md). Tokens live only in `src/styles.css`.

## Run locally (no AWS, no keys)

```powershell
# terminal 1: backend API with mock DynamoDB + demo seed + simulator + dev login
cd backend
python -m uv run python scripts/dev_server.py        # macOS/Linux: uv run python scripts/dev_server.py

# terminal 2: dashboard
cd dashboard
npm install
npm run dev                                         # http://localhost:5173
```

Sign in at `/admin/login` (`admin@clearsky.local`), `/baler/login` (`b01@clearsky.local` … `b10@…`) or `/buyer/login` (`by01@clearsky.local` … `by03@…`); the local password is `clearsky-dev` (`DEV_PASSWORD`). Shortcut URLs (dev only): `/admin?as=officer.Sangrur&sim=1`, `/baler?as=operator.B01`, `/buyer?as=buyer.BY03`.

## Environment variables (`dashboard/.env.local`)

Nothing is needed locally. For the deployed stack:

| Variable | Value |
|---|---|
| `VITE_API_URL` | Stack output `ApiUrl` (no trailing slash) |
| `VITE_AUTH_MODE` | `cognito` (local default is `dev`) |
| `VITE_AWS_REGION` | `ap-south-1` |
| `VITE_USER_POOL_ID` | Stack output `UserPoolId` |
| `VITE_USER_POOL_CLIENT_ID` | Stack output `UserPoolClientId` |
| `VITE_MAP_STYLE_URL` | Optional. Empty = OpenFreeMap positron (free OSM vector tiles). Amazon Location: `https://maps.geo.ap-south-1.amazonaws.com/v2/styles/Monochrome/descriptor?key=YOUR_KEY&color-scheme=Light` |

## Tests

```powershell
npm run typecheck
npm test              # Vitest: components + route guards
npm run build
npm run e2e           # Playwright (smoke + one test per role app) against the local stack, using installed Google Chrome
                      # Windows without uv on PATH: $env:CLEARSKY_API_CMD="python -m uv run python scripts/dev_server.py"
npm run screens -- screens   # capture the main screens (desktop + phone) into ./screens
```

## Deploy (AWS Amplify Hosting)

`amplify.yml` builds this folder of the monorepo. In the Amplify console: connect the GitHub repo, branch `main`, monorepo root `dashboard`, set the `VITE_*` variables above, and add a rewrite rule so client routes work: source `</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp|mjs)$)([^.]+$)/>` → target `/index.html` → type `200 (Rewrite)`. Then set the stack parameter `CorsOrigins` to the Amplify URL.
