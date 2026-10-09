---
title: "Pollution avoided per cleared field and on the public impact page (with a model-style impact table)"
assignee: kamranp03
labels: [feature, dashboard, backend, impact]
---

## Why

ClearSky's whole point is that straw that is baled is straw that isn't burnt. Today we show **acres cleared** and **tonnes routed**, but not the thing judges and officials care about most: **how much air pollution we prevented**.

The plumbing exists but is switched off:
- `EMISSION_FACTOR_PM25_KG_PER_TONNE` in `backend/src/clearsky/config.py` defaults to `None`.
- `domain/stats.py` returns `pm25_avoided_kg = None`.
- `/impact` (`dashboard/src/pages/Impact.tsx`) hides the counter when it is `None`.

We need a **sourced** calculation, shown:
1. on the public `/impact` page (totals + a chart),
2. **next to every completed field**: an impact table modelled on the reference below, plus the field drawer, the baler's Done confirmation and the buyer deliveries,
3. optionally to the farmer on WhatsApp after their field is cleared.

## Reference design

![Reference: model table with grouped rows, trend sparklines, formula pills and period columns](https://github.com/sanskarjoshiii/clearsky/blob/main/designs/modelling-1.jpg?raw=true)

`designs/modelling-1.jpg` (also see `designs/proto-screen-3.jpg`). How we map it:

| Reference element | ClearSky impact table |
|---|---|
| Group header chips ("ARR & Summary", "Account Summary") | **Village** groups (chip with village name; collapsible), plus a "District total" group at the top |
| Row with `#`/`$` icon + variable name | One **cleared field**: farmer name (masked in public view, e.g. "Gurpreet S."), acres, cleared date |
| **Trend** sparkline | Cumulative pollution avoided for that row over the season (for a field: a step on its cleared day; for a village: the running total) |
| **Formula** pill (lavender) | The calculation, shown transparently: `# 20 t straw × PM2.5 factor` (hover → full factor + source citation) |
| Period columns (Jan '24 …) | One column per **pollutant**: PM2.5 kg · PM10 kg · CO kg · CO₂ t · black carbon kg (only those with a sourced factor). Or, in a toggle "By week", columns per week of the season |
| "+ New variable" row | Not needed (read-only) |

Follow `docs/design-system.md`. The formula pill uses the agent-soft lavender because it is a machine calculation (rule 1). Numbers are tabular. Sparklines use the data ramp (`data-1..3`), never risk colours.

## The calculation (must be sourced)

```
straw_tonnes_not_burnt = booking.est_tonnes          (later: actual tonnes if the baler records them)
avoided_<pollutant>    = straw_tonnes_not_burnt × EF_<pollutant>   (EF in kg per tonne of rice straw burnt in the open)
```
- **Do not invent factors.** Use published, peer-reviewed emission factors for **open burning of rice straw / crop residue**, for example a compilation such as Andreae (2019), *Atmos. Chem. Phys.*, or Indian field studies. The team picks the paper, records the **exact value, unit and citation**, and gets one teammate to double-check them. If a pollutant has no agreed factor, it is not shown.
- Store factors as config, one per pollutant, each with its citation:
  - `EMISSION_FACTORS` in `config.py`: a small dict/JSON setting `{pollutant: {kg_per_tonne, source, url}}` replacing the single `EMISSION_FACTOR_PM25_KG_PER_TONNE`.
  - Expose `source` and `url` through the API so the UI can show "Source: …" under every number.
- Optional **fraction actually burnt** (`BURN_FRACTION`, default 1.0): not every unbooked field would have been fully burnt. If the team uses a value below 1, it needs its own citation; otherwise keep 1.0 and say "if burnt".
- Label every number as an **estimate**, never a measurement.

### Snapshot per booking
When a booking becomes `DONE` (`domain/matching.mark_done`), write an impact snapshot onto the booking: `impact = {pollutant: kg, …}`, `impact_factors_version`, `impact_tonnes`. Then:
- history doesn't silently change if the factors are edited later (a re-compute script handles deliberate changes);
- the stats and table are cheap reads.

Add a backfill script `scripts/backfill_impact.py` for existing DONE bookings.

## Where it appears

| Surface | What | Files |
|---|---|---|
| **Public `/impact`** | Totals per pollutant (animated counters); a cumulative line or area chart over the season; the **impact table** (reference-style) grouped by village; a methodology footnote with citations | `dashboard/src/pages/Impact.tsx`, new `components/ImpactTable.tsx`, `components/Sparkline.tsx` |
| **Admin** | Same impact table on the radar page or its own `/admin/impact`; an "Avoided" column in Bookings for DONE rows; an impact block in the field drawer for cleared fields | `pages/officer/*`, `components/FieldDrawer.tsx` |
| **Baler** | After **Done**: "Field cleared · ~X kg PM2.5 avoided (estimate)"; season total on the History page (routing issue) | `pages/Operator.tsx` |
| **Buyer** | "Pollution avoided by straw you received" KPI and a column in Deliveries | `pages/Buyer.tsx` |
| **Farmer (optional)** | The cleared message adds "Aapke khet se lagbhag X kg dhuan (PM2.5) rukne ka anumaan" | `channels/templates.py` (`field_cleared` gets a 2nd parameter, so it **needs re-approval in Meta**), `docs/whatsapp_templates.md` |

## API
- `GET /api/stats`: add `impact: {pollutant: {kg, source, url}}` and `impact_estimate: true`; remove `pm25_avoided_kg` (keep it until the UI is switched).
- `GET /api/impact?group=village|field&period=season|week`: public, returns rows for the table. **Public rows must not expose phone numbers**; use masked farmer names or "Field in {village}". Each row has `{label, village, acres, tonnes, cleared_date, impact: {...}, trend: [{date, cumulative}]}`.
- `GET /api/fields/{id}` (admin) and `/api/operator/me/route` (stop rows): include `impact` for DONE bookings.

## Edge cases
- No factors configured → all impact UI hidden gracefully (today's behaviour), with an admin hint "Add emission factors (with sources) to show pollution avoided".
- Cancelled or declined bookings never count; only DONE.
- Units: kg for particulates and CO; tonnes for CO₂. Indian number formatting (`fmtNum`).
- Public page performance: aggregate server-side; the table paginates by village.
- Accessibility: sparklines get an `aria-label` with the final value; the table needs keyboard expansion of groups.

## Acceptance criteria
- [ ] Emission factors chosen from published sources, with value, unit and citation recorded in config and in `README.md` §16 (Sources).
- [ ] Every DONE booking stores an impact snapshot; the backfill script fills existing ones.
- [ ] `/impact` shows totals, a season chart, and the reference-style table (village groups, trend sparkline, formula pill, pollutant columns) with a methodology footnote.
- [ ] Cleared fields show their avoided pollution in the admin drawer, admin bookings, the baler's Done confirmation and buyer deliveries.
- [ ] Everything says "estimate" and links to the source; nothing appears if factors are missing.
- [ ] Backend tests: calculation, snapshot on done, no impact for cancelled, stats aggregation, no phone numbers in public rows. Vitest: `ImpactTable` groups/expands, `Sparkline` renders. Playwright: mark a field Done → `/impact` total increases.
- [ ] Docs: `IMPLEMENTATION.md` (new §: impact methodology), `docs/design-system.md` (impact table component), `CONTEXT.md`.

## Files you'll touch
`backend/src/clearsky/{config.py,domain/stats.py,domain/matching.py,handlers/api.py,models/entities.py}`, new `domain/impact.py` and `scripts/backfill_impact.py`, tests; `dashboard/src/pages/{Impact.tsx,Operator.tsx,Buyer.tsx}`, `components/{FieldDrawer.tsx,ImpactTable.tsx,Sparkline.tsx}`, `api/{types.ts,hooks.ts}`.
