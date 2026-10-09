---
title: "Self-registration for balers and buyers with super-admin approval"
assignee: kamranp03
labels: [feature, dashboard, backend, auth]
---

## Why

Today every dashboard account is created by hand (`backend/scripts/create_demo_users.py`). The Cognito pool is admin-only (`AllowAdminCreateUserOnly: true` in `infra/template.yaml`), and balers/buyers exist only as seed rows (`B01–B10`, `BY01–BY03`). That works for a demo but not for onboarding real custom-hiring centres (balers) and industries (buyers).

We want **anyone to apply** as a baler operator or an industry buyer. The **district officer (super admin)** reviews and approves or rejects. Only an approved applicant can use their dashboard, and approval also **creates their `Baler` or `Buyer` record** so the matcher can start using them.

## How it fits the current system

| Piece today | Where | What changes |
|---|---|---|
| Cognito pool, groups `officer`/`buyer`/`operator`, custom attrs `custom:baler_id` / `custom:buyer_id` | `infra/template.yaml` (UserPool, UserPoolClient, groups) | Allow self sign-up; keep `custom:*` attributes **not** client-writable (already true: `WriteAttributes: [email]`) so nobody can give themselves a role |
| Role resolution from JWT claims; no group → `None` → 401 | `backend/src/clearsky/auth.py` (`from_claims`) | Signed-in user without a group becomes role **`pending`** (can only call registration endpoints) |
| `Balers` / `Buyers` tables + models | `models/entities.py`, `repo/balers.py`, `repo/buyers.py` | Approval writes a new row (`B11…`, `BY04…`); the matcher picks it up automatically (`BalersRepo.list_active`, `BuyersRepo.list_all`) |
| Officer = super admin | `handlers/api.py`, `dashboard/src/pages/officer/*` | New **Approvals** page and endpoints |
| Login page | `dashboard/src/pages/Login.tsx` | Add "Create account" → `/register`; signed-in-but-pending users see `/pending` |

## Recommended design

**Cognito self sign-up + an `Applications` table.** Cognito handles passwords, email verification and resets, so we never handle passwords ourselves. Our API stores the business details and does the approval.

### Flow
1. Applicant opens `/register` and picks **Baler operator** or **Industry buyer**. They enter email + password, then verify their email with the 6-digit Cognito code (Amplify `signUp` / `confirmSignUp`).
2. Once signed in with no group, the dashboard routes them to the **application form** and calls `POST /api/register`.
3. The officer sees the request on **`/admin/approvals`** (see the routing issue) and opens a drawer with all details and a map pin.
   - **Approve:** the API, in this order:
     1. creates the `Baler`/`Buyer` row with a new id
     2. `AdminUpdateUserAttributes` sets `custom:baler_id` / `custom:buyer_id`
     3. `AdminAddUserToGroup` puts them in `operator` / `buyer`
     4. marks the application `APPROVED`
   - **Reject:** the application becomes `REJECTED` with a reason the applicant can see.
4. The applicant's dashboard polls `GET /api/register/me`. On approval it refreshes the Cognito session (`fetchAuthSession({ forceRefresh: true })`, so the new group is in the ID token) and lands on their home page.

### Data model (new table `Applications`)
| Attribute | Notes |
|---|---|
| `application_id` (PK) | `AP-…` |
| `sub` (GSI `sub-index`) | Cognito user id: one open application per user |
| `email` | from the token, not the form |
| `role` | `operator` \| `buyer` |
| `status` (GSI `status-index`, sort `created_at`) | `PENDING` \| `APPROVED` \| `REJECTED` |
| `name`, `phone` (E.164, validated), `org_name` (CHC or company) | |
| `village_id` + `lat`/`lng` | village picked via `domain/villages.resolve`; optional map pin to refine |
| **Baler only:** `acres_per_day` (1–60), `radius_km` (5–50), `machine_details` (free text) | becomes the `Baler` row |
| **Buyer only:** `type` (`pellet`/`cbg`/`boiler`/`biomass_power`), `price_per_tonne`, `demand_tonnes`, `max_radius_km` | becomes the `Buyer` row (prices remain "demo" in the demo stack) |
| `reviewed_by`, `reviewed_at`, `reject_reason`, `entity_id` (the created `B…`/`BY…`) | audit |

Add the table to **both** `infra/template.yaml` and `backend/src/clearsky/repo/schema.py`. `tests/test_template_schema.py` fails if they differ.

### API (all under the existing JWT authorizer `/api/{proxy+}`)
| Method | Path | Who | Behaviour |
|---|---|---|---|
| POST | `/api/register` | role `pending` | Validate with Pydantic; 409 if an open application exists |
| GET | `/api/register/me` | `pending` or any role | Current application + status |
| GET | `/api/applications?status=` | officer | List, newest first |
| POST | `/api/applications/{id}/approve` | officer | Idempotent, conditional on `status = PENDING`; returns the created entity |
| POST | `/api/applications/{id}/reject` `{reason}` | officer | Reason required |

**IAM:** add `cognito-idp:AdminAddUserToGroup` and `cognito-idp:AdminUpdateUserAttributes` on the `UserPool` ARN to `AppAccessPolicy`. Add `USER_POOL_ID` to the function environment (`!Ref UserPool`).

**Cognito changes:** `AdminCreateUserConfig.AllowAdminCreateUserOnly: false`. Keep `AutoVerifiedAttributes: [email]`. Optionally lower sign-up abuse with a password policy (already strict) and a simple rate limit on `POST /api/register`.

**Local dev (`DEV_AUTH`):** the dev role picker gets "New applicant (pending)". Approve then stores the `baler_id`/`buyer_id` on the application, and `/api/dev/accounts` lists approved accounts so the flow is testable without Cognito.

### Dashboard
- `/register`: role choice (two big cards) → Cognito sign-up → email code → application form (village search with the same fuzzy matching, number inputs with units, Hindi helper labels for balers).
- `/pending`: status card ("Under review", or the rejection reason with "Edit and resubmit").
- `/admin/approvals`: table (name, role, org, village, submitted, status) with filters. The drawer has every field, a map pin and **Approve** / **Reject (reason)**. Show a KPI badge "N pending" in the admin rail.
- Follow `docs/design-system.md` (ink primary buttons, hairline cards; no colour for status except risk).

## Edge cases to handle
- An applicant signs up but never submits the form: they stay `pending` with no application, and the form is shown again.
- Approving twice, or approving after reject: the conditional update returns 409.
- Officer rejects → applicant edits → resubmits: a new application, keeping the history.
- **Approved baler or buyer deactivated later:** add an officer action that sets `Baler.active=false` and removes the group. Their existing CONFIRMED bookings stay; tie this into the accept/reject issue.
- Duplicate org registering twice: warn when the phone number or org name matches an existing baler/buyer.
- Token refresh after approval (see flow step 4). Without it the user keeps getting 401/403 until they sign in again.

## Acceptance criteria
- [ ] A new user can sign up, verify their email and submit a baler or buyer application on the deployed stack and locally (dev auth).
- [ ] A pending user can reach only `/pending` / `/register` pages and the registration endpoints (API returns 403 elsewhere).
- [ ] The officer sees pending applications, can approve/reject, and approval creates the `Baler`/`Buyer` row plus the Cognito group and attribute.
- [ ] After approval the user lands on their own dashboard without contacting anyone.
- [ ] An approved baler becomes bookable: a farmer near their base gets matched to them (verify with the simulator).
- [ ] Rejected users see the reason.
- [ ] Backend tests: validation, role gating, idempotent approve, reject reason required, entity creation, Cognito calls mocked (moto `cognito-idp`).
- [ ] Playwright: register (dev auth) → officer approves → applicant sees the operator/buyer home.
- [ ] `IMPLEMENTATION.md` (§3 data model, §9 API, §11 auth), `CONTEXT.md`, `SETUP_GUIDE.md` §5 updated. `scripts/create_demo_users.py` stays for seeding demo accounts.

## Files you'll touch
`infra/template.yaml`, `backend/src/clearsky/{auth.py,handlers/api.py,repo/schema.py,models/entities.py}`, new `repo/applications.py` + `domain/registration.py`, tests, `dashboard/src/{App.tsx,auth/AuthProvider.tsx,pages/Login.tsx}`, new `pages/register/*` and `pages/admin/Approvals.tsx`.
