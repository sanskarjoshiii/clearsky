# clearsky: Setup Guide

**Where things stand (2026-10-09):** every phase in `PLAN.md` except the satellite stretch (Phase 8) is built and tested on a laptop. That covers:
- the WhatsApp farmer agent
- the booking engine
- the officer (government super-admin), baler-operator and industry-buyer dashboards
- risk scores and village alerts
- reminders and demo mode

What's left needs **your accounts and approvals**: an LLM API key, the AWS deploy, WhatsApp (Meta), and a few confirmations. This guide walks through each one in order. Where a step must be done by your friend (the AWS account owner), it says so.

> ⚠️ **Never paste passwords, API keys or tokens into chat, WhatsApp groups, or any committed file.** Secrets go only in `.env` (Git ignores it) or AWS SSM (step 4.4).

---

## Quick checklist

| # | What | Who | Time | Needed for |
|---|---|---|---|---|
| 0 | Try everything locally (nothing needed) | You | 10 min | Seeing it work today |
| 1 | LLM API key + model ID | You | 10 min | Smarter farmer replies (the rules bot works without it) |
| 2 | Voice notes: pick speech-to-text | You / friend | 10 min | Voice notes on WhatsApp |
| 3 | New AWS access keys | Friend | 10 min | Anything on AWS: **the old key on this laptop now fails** (`InvalidClientTokenId`) |
| 4 | Deploy to AWS | You (friend's OK) | 30 min | Live system |
| 5 | Dashboard users (Cognito) | You | 5 min | Signing in to the deployed dashboard |
| 6 | Dashboard hosting (Amplify) | You | 15 min | Dashboard URL for judges/phones |
| 7 | WhatsApp Cloud API (Meta) | You | 45 min + template approval | Real WhatsApp messages |
| 8 | NASA FIRMS key | Anyone | 5 min | Fire-history map and **red** risk |
| 9 | Confirm villages + demo prices | Team | 15 min | Demo honesty |
| 9b | Emission factors with sources | Team | 30 min | Showing pollution avoided (nothing is shown without them) |
| 10 | Video, blog, submission | Team | | Hackathon submission |

At the end there is a **reply template** to paste back to Claude.

---

## 0. See it working on your laptop (no keys, no AWS)

Everything runs locally: a mock database with the demo data, the farmer agent (rules bot), and a **farmer simulator** (a WhatsApp stand-in inside the dashboard).

```powershell
cd C:\Users\prema\Desktop\clearsky
git pull
.\make.ps1 install              # Python deps (first time)

# terminal 1: backend
.\make.ps1 dev                  # wait for "clearsky API on http://127.0.0.1:8787"

# terminal 2: dashboard
.\make.ps1 dashboard            # opens on http://localhost:5173
```

1. Open <http://localhost:5173/admin/login> and sign in as the district officer: `admin@clearsky.local`, password `clearsky-dev`. (Each role has its own sign-in page: balers use `/baler/login` with e.g. `b01@clearsky.local`, buyers `/buyer/login` with e.g. `by03@clearsky.local`, same local password. On the deployed stack everyone uses their own Cognito email and password.)
2. Click the round **violet chat button** at the bottom-left of the rail. The **Farmer on WhatsApp** panel opens.
3. Tap the **Hinglish** sample, or type: `Mera 8 acre dhaan 24 tareekh ko katega, Bhawanigarh. Naam Gurpreet.` The agent books a baler and replies.
4. In a second browser window go to <http://localhost:5173/baler?as=operator.B01> and press **Next stops**. Your farmer's field is a stop; press **Done · हो गया** and the farmer panel gets "khet saaf ho gaya ✅".
5. Try **Buyer** (`/buyer?as=buyer.BY03`), the **Demo controls** page, and **Impact** (`/impact`).

Each role has its own app: **Admin** at `/admin`, **Baler** at `/baler` (phone-first, with Schedule / History / Profile tabs) and **Buyer** at `/buyer` (Overview / Deliveries / Demand / Profile). Old `/officer` and `/operator` links redirect.

Automated checks: `.\make.ps1 test` (backend) and `.\make.ps1 e2e` (dashboard; uses your installed Google Chrome).

**What changed with the four GitHub issues (2026-10-09):** a farmer's request now goes to a baler as an **offer**; the baler opens **Requests** and taps **Accept** (or **Decline**), and only then does the farmer get the ✅ confirmation. Balers and buyers can **register themselves** and the admin approves them. And the impact page can show **pollution avoided**, but only after you give us sourced emission factors (step 9b).

The full demo story is in `docs/demo_runbook.md`.

---

## 1. LLM API key (the farmer agent's brain)

Bedrock isn't usable on the AWS account, so clearsky can now use **any of these** (setting `LLM_PROVIDER`):

| Provider | `LLM_PROVIDER` | Get a key at | Extra setting |
|---|---|---|---|
| OpenAI | `openai` | <https://platform.openai.com/api-keys> | none |
| Anthropic (Claude) | `anthropic` | <https://console.anthropic.com/settings/keys> | none |
| Google Gemini | `gemini` | <https://aistudio.google.com/apikey> | none |
| Any OpenAI-compatible API (e.g. Groq, OpenRouter, Together) | `openai` | the provider's console | `LLM_BASE_URL` = the provider's OpenAI-compatible base URL (from its docs) |

Without a key, `LLM_PROVIDER=rules` (the default) runs a deterministic bot. It handles Hindi, Punjabi, Hinglish and English booking, status, cancel and HAAN/NAHI. It is also the automatic fallback if the LLM call fails.

### 1.1 Get the key
1. Sign in to the provider's console (links above). Add a payment method if it asks; a hackathon uses a few cents to a few dollars.
2. Create an API key and copy it.
3. Pick a **model that supports tool/function calling** from the provider's model list page and copy its exact **model ID**. Smaller/cheaper models are fine for this short-form chat. Claude doesn't pick it for you.

### 1.2 Put it in `.env` (repo root)
`.env` doesn't exist yet the first time: `copy .env.example .env`, then `notepad .env` and make sure these lines exist (add any that are missing):

```
LLM_PROVIDER=openai            # or anthropic / gemini
LLM_MODEL_ID=<model id from the provider>
LLM_API_KEY=<your key>
LLM_BASE_URL=                  # only for OpenAI-compatible providers other than OpenAI
```

### 1.3 Test it
```powershell
cd C:\Users\prema\Desktop\clearsky\backend
python -m uv run python scripts\check_aws.py --invoke-llm      # "LLM provider ✅" and "LLM invoke ✅" (one tiny billed call)
cd ..
.\make.ps1 chat                                                # type a farmer message; /quit to exit
```
Restart `.\make.ps1 dev` after changing `.env`. Then tell Claude **"LLM key set"** and it will record the 5 sample conversations (`docs/agent_transcripts.md`).

---

## 2. Voice notes: choose speech-to-text

Farmers can send voice notes. Pick **one**:

| Option | `.env` | Notes |
|---|---|---|
| **A. Amazon Transcribe** (Hindi `hi-IN`) | `STT_PROVIDER=transcribe` | Needs Transcribe enabled on the AWS account (it returned `SubscriptionRequiredException` on 2026-10-07): see 2.1 |
| **B. OpenAI-compatible speech API** | `STT_PROVIDER=openai`, `STT_MODEL_ID=<speech-to-text model id>`, optional `STT_BASE_URL`, `STT_API_KEY` (or it reuses `LLM_API_KEY`) | Works with OpenAI or any provider exposing `/audio/transcriptions` |
| C. No voice yet | `STT_PROVIDER=none` | Voice notes get "please type" (default) |

Voice **replies** use Amazon Polly (voice "Kajal", already verified on the account). They need the deployed stack (`MEDIA_BUCKET`) and work automatically when a farmer sends a voice note.

### 2.1 (Option A) Friend: enable Transcribe
1. AWS console → region **Asia Pacific (Mumbai) ap-south-1** → search **Amazon Transcribe** → **Real-time transcription**. If it opens and works, you're done.
2. If you see a subscription/activation error: **Billing and Cost Management → Payment methods** (add/verify a card), and check **Account** for "activation pending". New accounts can take up to 24 h.
3. Still blocked: **Support → Create case → Account and billing → Account → Activation**: *"Amazon Transcribe in ap-south-1 returns SubscriptionRequiredException for this account. Please enable it."*

---

## 3. New AWS access keys (Friend, then you)

**Done 2026-10-10:** clearsky now uses Akshay's account **370042934648**. The shared IAM user `clearsky-dev` (AdministratorAccess) and the $10 budget already exist. Ask Akshay for the access key CSV (shared privately), then follow §3.3. The old `Kamran_03` key (account 416121583611) is no longer used.

To rotate or remove the key later: `aws iam list-access-keys --user-name clearsky-dev`, then `aws iam delete-access-key --user-name clearsky-dev --access-key-id <id>`. Delete the user after the hackathon.

### 3.1 Friend: create a user and key for you
1. Sign in to <https://console.aws.amazon.com>, region **ap-south-1 (Mumbai)**.
2. **IAM → Users → Create user** → name `clearsky-dev` → **Attach policies directly** → **AdministratorAccess** → **Create user**. (Simplest for a 4-day hackathon; **delete it afterwards**.)
3. Open the user → **Security credentials → Create access key → Command Line Interface (CLI)** → confirm → **Create**.
4. Give you the **Access key ID** and **Secret access key** privately (in person or a password-manager share).

### 3.2 Friend: budget alarm
**Billing and Cost Management → Budgets → Create budget → Use a template → Monthly cost budget → $10 → email → Create.** clearsky is serverless and should cost cents; this is a safety net.

### 3.3 You: save and check the key
```powershell
aws configure --profile clearsky        # paste key id + secret; region ap-south-1; output json
$env:AWS_PROFILE = "clearsky"           # in every new PowerShell window (or add to your PowerShell profile)
aws sts get-caller-identity             # shows the friend's 12-digit account
cd C:\Users\prema\Desktop\clearsky
.\make.ps1 check-aws                    # ✅/❌ table (read-only, free)
```

---

## 4. Deploy to AWS (needs your friend's OK)

Creates one CloudFormation stack **`clearsky-dev`** in **ap-south-1** with:
- DynamoDB tables, 2 S3 buckets, an SQS queue and DLQ
- Lambdas: webhook, processor, API, risk job, reminders, health, FIRMS ingest
- an HTTP API and a Cognito user pool
- an hourly schedule and an 18:00 IST schedule, plus 3 CloudWatch alarms

Idle cost is near zero (everything is on-demand).

### 4.1 Choose the stack settings
Open `infra\samconfig.toml` and edit the `parameter_overrides` line, for example:
```toml
parameter_overrides = "Stage=dev DemoMode=true LlmProvider=openai LlmModelId=<model id> WaMode=simulator SttProvider=none TtsProvider=polly CorsOrigins=*"
```
- `LlmProvider` / `LlmModelId` / `LlmBaseUrl`: same as step 1 (`rules` needs nothing).
- `WaMode=simulator` for the first deploy. Switch to `cloud` after step 7.
- `SttProvider`: from step 2. `SttModelId` if you chose option B.
- `CorsOrigins`: `*` now; the Amplify URL after step 6.
- Optional `AlarmEmail=you@example.com` (confirm the subscription email AWS sends).

### 4.2 Build and deploy
```powershell
cd C:\Users\prema\Desktop\clearsky
$env:AWS_PROFILE = "clearsky"
.\make.ps1 build
.\make.ps1 deploy -Confirm yes
```
SAM shows a **change set**. Read it, type **y**. It takes about 5 minutes and ends with **Outputs**. Copy them somewhere; you need `ApiUrl`, `WebhookUrl`, `UserPoolId`, `UserPoolClientId`, `DataBucketName`, `MediaBucketName`.

### 4.3 Point your `.env` at the stack
```
TABLE_PREFIX=clearsky-dev-
DATA_BUCKET=<DataBucketName>
MEDIA_BUCKET=<MediaBucketName>
```

### 4.4 Store secrets in AWS (SSM)
The Lambdas read secrets from SSM, not from `.env`:
```powershell
.\scripts\put_secrets.ps1       # copies LLM_API_KEY, STT_API_KEY, FIRMS_MAP_KEY and WA_* from .env (empty ones are skipped)
```
Run it again whenever a key changes, then `.\make.ps1 deploy -Confirm yes`. Lambdas cache secrets for the life of a container, and a deploy starts fresh containers.

### 4.5 Load demo data and check
```powershell
.\make.ps1 seed                                    # deletes items in clearsky-dev-* tables and loads the demo seed
aws dynamodb scan --table-name clearsky-dev-Villages --select COUNT    # Count: 31
```
Open `<ApiUrl>/health` in a browser → `{"ok": true, ...}`.

### 4.6 Removing everything later
```powershell
cd infra
python -m uv tool run --from aws-sam-cli sam delete --stack-name clearsky-dev
```

---

## 5. Dashboard users (Cognito)

**Balers and buyers register themselves.** On the login page they press **Create an account**, choose *Baler operator* or *Industry buyer*, verify their email with a 6-digit code, and fill in a short form. The officer then opens **Admin → Approvals**, checks the details and presses **Approve** (or **Reject** with a reason). Approval creates their baler/buyer record and lets them sign in to their own app; nobody has to create a user by hand.

The **officer** account (and any demo accounts) is still created by the team (passwords print once; share them privately):
```powershell
cd C:\Users\prema\Desktop\clearsky\backend
python -m uv run python scripts\create_demo_users.py `
  --officer officer@yourteam.in `
  --buyer buyer@yourteam.in:BY03 `
  --operator operator1@yourteam.in:B01 --operator operator2@yourteam.in:B02
```
Buyer IDs: `BY01` Demo Pellet Plant, `BY02` Demo CBG Plant, `BY03` Demo Boiler Unit. Baler IDs: `B01`–`B10` (see the Balers table). Self-registered balers and buyers get the next ids (`B11`, `BY04`, …) on approval.

Try it locally first (no AWS): on <http://localhost:5173/login> press **Create an account**, apply as a baler, then sign in as **Admin** in another browser window and approve it under **Approvals**. The first window moves to the baler app by itself.

> Deploying this version changes the user pool to allow self sign-up and adds the `Applications` table and three Cognito admin permissions for the API function. Sign-up emails use Cognito's built-in sender, which has a low daily limit; for real volumes connect Amazon SES to the user pool.

---

## 6a. Host the dashboard on S3 + CloudFront (what we use; no GitHub access needed)
Stack `clearsky-dev-web` (`infra/web.yaml`): private S3 bucket + CloudFront (HTTPS, SPA routing).
```bash
aws cloudformation deploy --template-file infra/web.yaml --stack-name clearsky-dev-web --region ap-south-1   # once
make web-deploy      # build dashboard/ with the backend stack's VITE_* values, upload, invalidate
```
Custom domain `clearsky.akkki.tech` (DNS on Vercel):
1. ACM certificate in **us-east-1** (DNS validation) → add its validation CNAME in Vercel DNS → wait for `ISSUED`. Vercel adds CAA records (letsencrypt/pki.goog/sectigo) that make ACM fail with `CAA_ERROR`: add `@ CAA 0 issue "amazon.com"` first. A failed cert can't be retried; request a new one with `--idempotency-token <new>`.
2. `aws cloudformation deploy ... --parameter-overrides DomainName=clearsky.akkki.tech CertificateArn=<arn>`.
3. Vercel DNS: `clearsky` CNAME → the stack's `CloudFrontDomain`.
4. Backend `CorsOrigins=https://clearsky.akkki.tech` in `samconfig.toml` → deploy.

## 6. Host the dashboard (AWS Amplify)

1. AWS console → **AWS Amplify → Create new app → GitHub** → authorize → repo **`sanskarjoshiii/clearsky`**, branch **`main`**.
2. Tick **"My app is a monorepo"** → root directory **`dashboard`**. Amplify detects `dashboard/amplify.yml`.
3. **Environment variables:**
   | Name | Value |
   |---|---|
   | `VITE_API_URL` | `ApiUrl` output (no trailing `/`) |
   | `VITE_AUTH_MODE` | `cognito` |
   | `VITE_AWS_REGION` | `ap-south-1` |
   | `VITE_USER_POOL_ID` | `UserPoolId` output |
   | `VITE_USER_POOL_CLIENT_ID` | `UserPoolClientId` output |
4. **Save and deploy.** When it's live, go to **Hosting → Rewrites and redirects → Manage → Add rewrite**: source `</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp|mjs)$)([^.]+$)/>`, target `/index.html`, type **200 (Rewrite)**.
5. Put the Amplify URL (e.g. `https://main.xxxx.amplifyapp.com`) in `CorsOrigins` (step 4.1) and run `.\make.ps1 deploy -Confirm yes` again.
6. Open the Amplify URL → sign in with a step-5 user.

(Quick alternative: run the dashboard on your laptop against the deployed API. Create `dashboard\.env.local` with the same five variables, then `.\make.ps1 dashboard`.)

---

## 7. WhatsApp Cloud API (Meta)

Farmers only. Operators, buyers and officers never use WhatsApp.

### 7.0 Test the webhook against your laptop (before any deploy)
Meta needs a public HTTPS URL, so tunnel the local server:
```bash
make dev-cloud                 # API on :8787 with WA_MODE=cloud: reads WA_* from .env, really sends replies
ngrok http 8787                # second terminal; copy the https://….ngrok-free.app URL
```
- Meta → **WhatsApp → Configuration → Webhook**: Callback URL = `<ngrok url>/webhook/whatsapp`, Verify token = `WA_VERIFY_TOKEN` → **Verify and save** → subscribe **`messages`**.
- Message the test number from a test-recipient phone; the reply comes from your laptop (no SQS locally: the webhook processes inline).
- The free ngrok URL changes every restart → update the callback URL each time. After deploying, switch it to the stack's `WebhookUrl`.
- `make dev` (simulator mode) does **not** work for this: it replaces `WA_APP_SECRET`/`WA_VERIFY_TOKEN` with local dummies.
- Voice notes locally: set `STT_PROVIDER=transcribe` and `MEDIA_BUCKET=<a private bucket>` in `.env` (we use `clearsky-dev-media-local-370042934648`, 1-day expiry). Transcribe batch jobs take ~10–60 s, so the reply is slow; `TRANSCRIBE_TIMEOUT_S` (default 90) caps the wait.
- Uses the `clearsky` AWS profile (botocore can't read `aws login` credentials). The mock DB resets on restart.

### 7.1 Create the Meta app
1. Go to <https://developers.facebook.com> → **My Apps → Create app** → use case **Other** → type **Business** → name `clearsky` → create (create or select a Business portfolio when asked).
2. In the app dashboard, **Add product → WhatsApp → Set up**.
3. **WhatsApp → API Setup**: Meta gives you a free **test phone number**. Copy:
   - **Phone number ID** → `WA_PHONE_NUMBER_ID`
   - **Temporary access token** → `WA_ACCESS_TOKEN` (expires in 24 h; see 7.4 for a permanent one)
4. **App settings → Basic → App secret → Show** → `WA_APP_SECRET`.
5. Invent a random **verify token** (e.g. 24 random letters and digits) → `WA_VERIFY_TOKEN`.
6. Note the **Graph API version** shown in API Setup (e.g. `v23.0`). If it differs, set `WA_API_VERSION` in `.env` and as an env var later.

### 7.2 Add test recipients (up to 5 phones)
**API Setup → To → Manage phone number list → Add phone number** (format `+91XXXXXXXXXX`). Each person enters the code WhatsApp sends them. These are your demo **farmers**.

### 7.3 Store secrets, switch to cloud mode, connect the webhook
1. Put the four `WA_*` values in `.env`, then `.\scripts\put_secrets.ps1`.
2. In `infra\samconfig.toml` set `WaMode=cloud` and run `.\make.ps1 deploy -Confirm yes`.
3. Meta → **WhatsApp → Configuration → Webhook → Edit**: Callback URL = **`WebhookUrl`** output; Verify token = your `WA_VERIFY_TOKEN` → **Verify and save** (it should say verified).
4. **Webhook fields → Manage → subscribe to `messages`**.
5. From a test phone, send `Namaste` to the test number. You get the clearsky greeting. Send the Gurpreet message: you get a booking.
6. Optional automated check: `python -m uv run python scripts\e2e.py --api-url <ApiUrl>` (from `backend`).

### 7.4 Permanent token (recommended before the demo)
The temporary token dies after 24 h.
1. <https://business.facebook.com> → **Business settings → Users → System users → Add** (Admin).
2. **Assign assets → Apps → clearsky → Full control**, and the WhatsApp account.
3. **Generate new token** → app clearsky → permissions `whatsapp_business_messaging`, `whatsapp_business_management` → copy.
4. Replace `WA_ACCESS_TOKEN` in `.env` → `.\scripts\put_secrets.ps1`.

### 7.4b Use our own WhatsApp number (instead of Meta's test number)
The test number only reaches ≤ 5 verified phones. To let any farmer message **our own number**, see the step-by-step list in `docs/issues/04-setup-aws-llm-whatsapp-end-to-end.md` §F:
1. Use a number that is not on the WhatsApp app.
2. Add it in WhatsApp Manager and register it for the Cloud API.
3. Add a payment method.
4. Get business verification.
5. Switch the app to Live.
6. Update `WA_PHONE_NUMBER_ID`.

### 7.5 Message templates (for reminders, alerts, "field cleared")
Submit the 4 templates in `docs/whatsapp_templates.md` exactly as written (**WhatsApp Manager → Message templates → Create**, category **Utility**, language **Hindi**). Until approved, these messages only reach farmers who wrote in the last 24 h.

---

## 8. NASA FIRMS key (fire-history map, and red risk)

The risk formula needs village fire history to mark bookable fields **red**. Without it the radar shows at most amber.
1. <https://firms.modaps.eosdis.nasa.gov/api/map_key/> → enter an email → the **MAP_KEY** arrives by email (free).
2. `.env`: `FIRMS_MAP_KEY=<key>`
3. Locally: `.\make.ps1 firms` (downloads Oct–Nov 2022–2025 fire points around Sangrur, writes `data/layers/firms_2022_2025.geojson`, and adds scores to `data/seed/villages.json`). Commit those two files.
4. Deployed (after step 4):
   ```powershell
   cd backend
   python -m uv run python scripts\fetch_firms.py --apply-db --upload
   ```
5. `.\scripts\put_secrets.ps1` stores the key in SSM too.

No key? Download CSVs at <https://firms.modaps.eosdis.nasa.gov/download/> (custom area `75.55, 29.75, 76.40, 30.50`, source VIIRS S-NPP, Oct 1 – Nov 30 of 2022–2025, CSV) into `data\raw\firms\` and run `.\make.ps1 firms`.

---

## 9. Confirm the village list and demo prices (Team)

**Villages** (31, coordinates approximate, `data/seed/villages.json`):

| Block | Places |
|---|---|
| Sangrur | Sangrur (town), Balian, Ghabdan, Ubhawal, Badrukhan, Mangwal, Mehlan |
| Bhawanigarh | Bhawanigarh (town), Balad Kalan, Gharachon, Phagguwala, Kakra, Nadampur, Jhaneri |
| Sunam | Sunam (town), Longowal (town), Cheema (town), Ugrahan, Sheron, Chhajli, Jakhepal |
| Dhuri | Dhuri (town), Benra, Ghanauri Kalan, Bhalwan |
| Dirba | Dirba (town), Rogla |
| Lehragaga | Lehragaga (town), Lehal Kalan |
| Moonak | Moonak (town), Khanauri (town) |

Reply "Villages OK" or the corrections.

**Demo prices** (labeled "demo" everywhere; not market prices): baling ₹600/acre · transport ₹8 per tonne-km · platform fee ₹50/tonne · buyers ₹1,500–1,900/tonne · 2.5 t/acre. Reply "Prices OK" or new numbers.

---

## 9b. Emission factors for "pollution avoided" (Team)

clearsky can show how much air pollution each cleared field avoided (on the public Impact page, in the admin drawer, for balers and buyers, and in the farmer's "field cleared" message). **It will not show any number until the team supplies emission factors from a published source.** We never make these up.

1. Pick a peer-reviewed source for **open burning of rice straw / crop residue** (a compilation paper or an Indian field study).
2. For each pollutant you want to show (PM2.5 first; optionally PM10, CO, CO₂, black carbon) note the **value in kg per tonne of straw burnt** (g/kg is the same number), the **citation** (author, year, journal, table or page) and a **link** (DOI).
3. Have a second teammate check each value against the paper.
4. Put them in `.env` as one line of JSON (and, when deployed, in the stack parameter `EmissionFactors`):
   ```
   EMISSION_FACTORS={"pm25":{"kg_per_tonne":<value>,"source":"<author, year, journal>","url":"<doi link>"}}
   ```
   Keys: `pm25`, `pm10`, `co`, `co2`, `bc`. A factor without `"source"` is ignored.
5. Record the same values in `README.md` §16 (the table is there, empty).
6. Bookings that were already done get their figures with `cd backend; python -m uv run python scripts\backfill_impact.py` (add `--dry-run` first to see what it would do).

If you would rather not claim that every unbooked field would have been burnt, set `BURN_FRACTION` below 1, with its own source; otherwise leave it at 1 and the page says "if burnt".

---

## 10. Video, blog, submission (Team)

- Rehearse `docs/demo_runbook.md` three times on the deployed stack, then record (≤ 3 min, 1080p).
- Blog on AWS Builder Center: problem → insight (fires moved to the evening) → what we built → AWS services → what fought back → results. Use only the sourced numbers in `README.md` §16.
- Submission: repo public, README with screenshots + deployed URL + video link, blog link, team verified on Builder Center.

---

## Reply template (copy, fill, paste into chat)

```
0. Local run works:                yes / problem: ______
1. LLM:                            provider ______, model ______, key in .env: yes / not yet
2. Voice (STT):                    transcribe / openai (model ______) / none
3. New AWS key + profile:          yes / not yet
4. Deploy approved / done:         approved / done / not yet   (ApiUrl: ______)
5. Cognito users created:          yes / not yet
6. Amplify URL:                    ______ / not yet
7. WhatsApp:                       test number connected / templates submitted / not yet
8. FIRMS key:                      yes / CSVs / not yet
9. Villages + prices:              OK / corrections: ______
9b. Emission factors:              pollutant ______ = ______ kg/t, source ______, link ______ / keep pollution figures off
```
