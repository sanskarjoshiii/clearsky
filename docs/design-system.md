# clearsky design system

Derived from the references in `designs/` with `.agents/skills/design-from-references` (colours sampled with `probe.py`, not eyeballed). Tokens live in **one file**: `dashboard/src/styles.css` (`@theme`). A hex value anywhere else is a bug.

## The taste in one paragraph

Quiet, dense, white. A government operations instrument, not a marketing site. An off-white frame holds one floating white canvas; hairlines, not shadows, do the separating; large tight display titles sit over dense tables and maps. Colour is rare and always means something: **violet is the machine talking to farmers, green/amber/red is burn risk, teal-blue is straw.** Everything else is ink on white.

## Rules (hold every PR against these)

1. **Violet means the WhatsApp agent acted.** Agent messages, the farmer simulator, the "via WhatsApp" chip, the planned route. Never a chart series, never a generic primary button.
2. **Green / amber / red mean burn risk and nothing else.** Risk pills, map pins, village circles, alert banners. Never decoration, never a button fill. Risk is always also written in words ("Red", "Amber", "Green"), never colour alone.
3. **Straw quantities use the teal-blue ramp** (`data-1..3`): tonnes, acres, capacity bars. Separated by value, not by new hues.
4. **Ink buttons, not coloured ones.** Primary = ink fill; secondary = white with a hairline; ghost for tertiary. One primary per surface.
5. **Hairlines, not shadows.** Elevation is a 1 px border (`line`), with the canvas getting a faint ring. Shadows only on things that float over content (dialogs, drawers, toasts).
6. **Dense inside data, generous around it.** 40 px table rows and 36 px headers; 36–40 px page gutters and 24 px between blocks. Numbers are tabular (`.tabular`).
7. **Phone first for operators and farmers.** Operator targets are ≥ 44 px, Done buttons are 48 px full-width, labels carry Hindi (`Done · हो गया`). Nothing scrolls sideways at 375 px.

## Tokens (`dashboard/src/styles.css`)

| Role | Token | Value | Source |
|---|---|---|---|
| App frame | `frame` | `#fafafc` | reference rail/background |
| Canvas | `canvas` | `#ffffff` | |
| Sunken / chips | `sunken` | `#f6f6f8` | |
| Hover | `hover` | `#f3f3f5` | |
| Hairline | `line` / `line-strong` | `#e8e8ea` / `#d9d9dc` | reference borders `#e1–e8` |
| Ink | `ink`, `ink-2` | `#1c1c1c`, `#3a3a3c` | reference title text `#1c1c1c` |
| Muted / faint text | `muted`, `faint` | `#6f6f73`, `#9b9ba0` | reference header text `#6f–71` |
| Agent violet | `agent`, `agent-strong` | `#5330b4`, `#43249a` | reference CTA `#542cb1–#522cb5` |
| Agent soft / line | `agent-soft`, `agent-line` | `#efebfc`, `#d4cdec` | formula pill `#efebfc`, chat border `#d4cdec` |
| Risk green | `ok`, `ok-soft`, `ok-line` | `#1b7f3b`, `#e3f8ec`, `#a9dfbf` | PLAN brand green; delta pill `#d3f9e4` |
| Risk amber | `warn`, `warn-fill`, `warn-soft` | `#b7790a`, `#e8a317`, `#fff4dc` | PLAN brand amber (text darkened for AA) |
| Risk red | `risk`, `risk-fill`, `risk-soft` | `#c93a3a`, `#d64545`, `#fff0f1` | PLAN brand red; delta pill `#fff0f1` |
| Data ramp | `data-1..3` | `#396799`, `#4da2a9`, `#79d7bd` | reference chart series |
| Wheat | `wheat` | `#f5e6c8` | PLAN brand |

Map colours are mirrored as `--map-*` CSS variables (MapLibre reads them at runtime).

**Contrast:** text on soft fills uses the darker step (`ok`, `warn`, `risk`), not the fill colour; amber text is `#b7790a` because `#e8a317` on white is below 3:1.

### Type

Inter (UI), Noto Sans Devanagari / Gurmukhi (Hindi, Punjabi).

| Role | Size / weight | Tracking |
|---|---|---|
| Page title | 38 px (30 px phone) / 600 | −0.032em |
| KPI value | 26 px / 600, tabular | −0.018em |
| Card title | 15 px / 500 | −0.018em |
| Body | 14 px / 400 | 0 |
| Table | 13 px | 0 |
| Labels / hints | 12–13 px muted | 0 |

### Radius & spacing

Canvas 14 px · cards 10 px · controls 8 px · chips 6 px · pills full. Canvas inset 8 px from the frame; page gutters 40 px desktop / 16 px phone.

## Components (as built)

| Component | File | Notes |
|---|---|---|
| Rail layout: icon rail · canvas · docked panel | `components/Shell.tsx` `RailLayout` | Shared by the admin and buyer apps (`apps/admin/Layout.tsx`, `apps/buyer/Layout.tsx`), each passing its own nav. 60 px rail; phone gets a bottom bar. The right panel is the farmer simulator (reference "assistant panel"), admin only. |
| Impact table | `components/ImpactTable.tsx` | The reference "model" table (`designs/modelling-1.jpg`) for pollution avoided. Group header **chips** (district total, then one collapsible chip per village, keyboard-operable with `aria-expanded`); one row per cleared field (masked name, acres, cleared date); a **Trend** sparkline; a **Formula** pill in agent lavender, because it is a machine calculation (rule 1), with the factor and source on hover; one right-aligned tabular column per pollutant, or per week. Paginates by village (8, then "Show more"). Renders nothing without sourced factors. |
| Sparkline | `components/Sparkline.tsx` | 96×24 inline SVG, stepped cumulative line in the data ramp (`data-1..3`), never a risk colour; `role="img"` with the final value in its `aria-label`. |
| Request card | `apps/baler/pages/Requests.tsx` | One open offer: who and where, three sunken facts (day, acres, straw), a countdown pill, and two 48 px buttons (secondary Decline, ink Accept). Declining swaps the buttons for a 2×2 reason picker. No colour: an offer is not a risk state. |
| Baler layout: top bar · bottom tabs | `apps/baler/Layout.tsx` | Phone-first: 52 px top bar, bottom tab bar with ≥ 56 px targets and Hindi labels; the tabs move into the top bar on wide screens. Steppers and day arrows are 44 px. |
| KPI strip | `ui.tsx` `KpiStrip` | Cells divided by hairlines in one bordered box; badge = small outlined pill. |
| Risk pill | `ui.tsx` `RiskPill` | Outlined pill with dot + word + optional score; RED pulses on the map only. |
| Data table | `components/DataTable.tsx` | Sticky 36 px header, 40 px rows, hairline grid, keyboard-activatable rows. |
| Chips | `ui.tsx` `Chip` | Neutral grey for categories; `agent` tone only for "via WhatsApp". |
| Map | `components/MapView.tsx` | OpenFreeMap positron basemap (or Amazon Location style). Unbooked field = ring in its risk colour, booked = solid dot, village = translucent circle sized by unbooked acres. |
| Farmer simulator | `components/Simulator.tsx` | Farmer messages right in bordered cards; agent replies left with a violet "clearsky agent" label; WhatsApp buttons as lavender pills; composer with violet hairline. |
| Dialog / drawer / toast | `ui.tsx`, `FieldDrawer.tsx` | The only surfaces with shadows. |

## Translation notes

The references are product UI, and so is clearsky, so no marketing translation was needed. The `/impact` page is the only "presentation" surface: same canvas and hairlines, sized up (60 px headline, 64 px counters), one count-up animation, no colour beyond ink.
