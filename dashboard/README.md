# clearsky dashboard

Web app for everyone except farmers (farmers use WhatsApp):

| Route | Who | What |
|---|---|---|
| `/officer` | District officer (super admin) | Burn Risk Radar: map, villages by risk, **Alert village**, field drawer |
| `/officer/fields`, `/bookings`, `/balers`, `/buyers` | Officer | Every table, searchable |
| `/officer/demo` | Officer (DEMO_MODE) | Demo clock, harvest wave, run risk/reminders, reset, runbook |
| `/buyer` | Industry buyer | Demand + price form, incoming tonnes chart, deliveries |
| `/operator` | Baler operator | Phone-first stop list with Call + big **Done**, route map, availability |
| `/impact` | Public | Live counters for the video |
| Side panel | Officer (WA_MODE=simulator) | **Farmer simulator**: chat as a farmer through the real WhatsApp pipeline |

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

Sign in with the role picker. Shortcut URLs (dev only): `/officer?as=officer.Sangrur&sim=1`, `/operator?as=operator.B01`, `/buyer?as=buyer.BY03`.

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
npm test              # Vitest component tests
npm run build
npm run e2e           # Playwright smoke tests against the local stack, using installed Google Chrome
                      # Windows without uv on PATH: $env:CLEARSKY_API_CMD="python -m uv run python scripts/dev_server.py"
npm run screens -- screens   # capture the main screens (desktop + phone) into ./screens
```

## Deploy (AWS Amplify Hosting)

`amplify.yml` builds this folder of the monorepo. In the Amplify console: connect the GitHub repo, branch `main`, monorepo root `dashboard`, set the `VITE_*` variables above, and add a rewrite rule so client routes work: source `</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp|mjs)$)([^.]+$)/>` → target `/index.html` → type `200 (Rewrite)`. Then set the stack parameter `CorsOrigins` to the Amplify URL.
