# ClearSky: Setup Guide (what the team must do before Phase 4)

Phases 0–3 are built and tested. To go further we need **8 things** from the team. This guide explains each one step by step, in plain words.

The AWS account belongs to a friend, so some steps must be done **by the friend (account owner)** and some **by you (the developer)**. Each step says who.

> ⚠️ **Never paste passwords, AWS secret keys or tokens into chat, WhatsApp groups, or any file that is committed to Git.** Secrets go only into `.env` (which Git ignores) or into `aws configure`.

---

## Quick checklist

| # | What | Who | Time | Send back to the developer / Claude |
|---|---|---|---|---|
| 1 | AWS access for you on the friend's account | Friend | 10 min | Nothing in chat (you run `aws configure` yourself) |
| 2 | Bedrock model chosen and working | Friend + you | 10 min | The model ID |
| 3 | Amazon Transcribe enabled | Friend | 5 min – 1 day | "Transcribe works" |
| 4 | Approve the deploy | Team | 15 min | "Deploy approved" |
| 5 | NASA FIRMS key | Anyone | 5 min | Nothing in chat (put it in `.env`) |
| 6 | Village list confirmed | Team | 15 min | "Villages OK" or the corrections |
| 7 | Demo prices confirmed | Team | 2 min | "Prices OK" or new numbers |
| 8 | Up to 5 demo farmer phone numbers | Team | 10 min | The numbers in `+91XXXXXXXXXX` format |
| 9 | GitHub repository URL | You | 5 min | The repo URL |

---

## 1. Get AWS access to your friend's account (Friend, then you)

Your laptop is already connected to AWS account **416121583611** as IAM user **Kamran_03** (checked on 2026-10-07). If that is your friend's account and that user is meant for this project, **skip to step 1.4** to just verify. Otherwise:

### 1.1 Friend: create an IAM user for you
1. Sign in to <https://console.aws.amazon.com> with the account owner login.
2. Top-right region selector → choose **Asia Pacific (Mumbai) ap-south-1**.
3. Search **IAM** → **Users** → **Create user**.
4. User name: `clearsky-dev`. Click **Next**.
5. **Attach policies directly** → tick **AdministratorAccess** → **Next** → **Create user**.
   *Why admin:* the deploy creates roles, Lambdas, tables, buckets and APIs. For a 4-day hackathon this is the simplest. **Delete this user after the hackathon.**
6. Open the new user → **Security credentials** tab → **Create access key** → choose **Command Line Interface (CLI)** → tick the confirmation → **Create**.
7. Share the **Access key ID** and **Secret access key** with you **privately** (in person, or a password manager share). Not in a group chat.

### 1.2 Friend: set a budget alarm (protects the friend's money)
1. Search **Billing and Cost Management** → **Budgets** → **Create budget**.
2. **Use a template** → **Monthly cost budget** → amount **$10** → enter the friend's email → **Create budget**.
3. Everything in ClearSky is serverless and should cost cents, but this alarm warns early if something goes wrong.

### 1.3 You: save the keys on your laptop
Open PowerShell and run:
```powershell
aws configure --profile clearsky
# AWS Access Key ID:     <paste>
# AWS Secret Access Key: <paste>
# Default region name:   ap-south-1
# Default output format: json
```
Then tell every command to use this profile (do this in each new PowerShell window, or add it to your PowerShell profile):
```powershell
$env:AWS_PROFILE = "clearsky"
```

### 1.4 You: check it works
```powershell
aws sts get-caller-identity
```
You should see the friend's 12-digit account number. Then:
```powershell
cd C:\Users\prema\Desktop\clearsky
.\make.ps1 check-aws
```
This prints a ✅/❌ table. It is read-only and free.

---

## 2. Choose a Bedrock model and make sure it works (Friend + you)

The farmer agent needs one Amazon Bedrock model that supports **tool use**. The team must pick it. Claude will not choose it for you.

### 2.1 Friend: enable model access
1. Console → region **ap-south-1 (Mumbai)** → search **Amazon Bedrock**.
2. Left menu → **Model catalog**. Click the model you want → if it shows **Request access** / **Enable**, click it.
   - For **Anthropic (Claude)** models AWS asks for a short **use-case form** the first time. Fill it in (company: the team name; use case: "hackathon chatbot that books farm services"). Approval is usually quick.
3. Wait until the model shows as **Access granted / Available**.

### 2.2 Pick the ID
On the model's page copy either:
- the **Model ID** (looks like `anthropic.…` or `amazon.…`), or
- an **Inference profile ID** (starts with `in.`, `apac.` or `global.`). `in.` profiles keep traffic inside India.

For reference, these IDs **appeared in this account's listing on 2026-10-07** (access not verified, and this is not a recommendation; the team decides on quality and cost):
`in.anthropic.claude-haiku-4-5-20251001-v1:0`, `in.anthropic.claude-sonnet-5`, `global.anthropic.claude-sonnet-4-6`, `apac.amazon.nova-pro-v1:0`, `apac.amazon.nova-lite-v1:0`.
Smaller models (Haiku, Nova Lite) are cheaper and faster; bigger ones follow instructions better.

### 2.3 You: put it in `.env` and test
```powershell
cd C:\Users\prema\Desktop\clearsky
copy .env.example .env      # only the first time
notepad .env                # set: BEDROCK_MODEL_ID=<the id you picked>
cd backend
.\.venv\Scripts\python.exe scripts\check_aws.py --invoke-bedrock
```
`--invoke-bedrock` sends one tiny test message (costs a fraction of a cent). You want ✅ on **Bedrock model exists** and **Bedrock invoke**.

### 2.4 You: talk to the agent
```powershell
cd C:\Users\prema\Desktop\clearsky
.\make.ps1 chat
```
Type: `Mera 8 acre dhaan 24 tareekh ko katega, Bhawanigarh. Naam Gurpreet.` You should get a booking for 25 Oct. Type `/quit` to exit.
Then tell Claude **"model ID is set"** and it will record the 5 sample conversations for `docs/agent_transcripts.md`.

---

## 3. Turn on Amazon Transcribe (Friend)

The check showed `SubscriptionRequiredException` for Transcribe. Voice notes (Phase 4) need it. This error usually means the account isn't fully activated for that service (often a new account, or a payment method that isn't verified yet).

1. Console → region **ap-south-1** → search **Amazon Transcribe**.
2. Click **Real-time transcription** (or **Create job**). If the page opens and works, it's enabled. Go to step 5.
3. If you see an error about subscription or activation:
   - Open **Billing and Cost Management → Payment methods** and make sure a valid card is added and **verified**.
   - Open **Account** and check there are no "account activation pending" messages. New accounts can take up to 24 hours to activate all services.
4. Still blocked? Open **Support → Create case → Account and billing → Service: Account → Category: Activation**. Write: *"Amazon Transcribe in ap-south-1 returns SubscriptionRequiredException for this account. Please enable it."*
5. You: run `.\make.ps1 check-aws` again. The **Transcribe** row should be ✅. Then tell Claude **"Transcribe works"**.

---

## 4. Approve and run the first deploy (Team decides, you run)

Deploying creates real resources in the friend's account: DynamoDB tables, 2 S3 buckets, 2 small Lambda functions, an HTTP API and a Lambda layer, all inside one CloudFormation stack named **`clearsky-dev`** in **ap-south-1**. With no traffic the cost is close to $0 (on-demand tables, pay-per-request Lambdas).

### 4.1 Get the friend's OK
The friend should know you're deploying into their account. Once they agree, tell Claude **"deploy approved"** in chat, or run it yourself:

### 4.2 Deploy
```powershell
cd C:\Users\prema\Desktop\clearsky
$env:AWS_PROFILE = "clearsky"          # if you made the profile in step 1.3
.\make.ps1 build
.\make.ps1 deploy -Confirm yes
```
- SAM shows a **change set** (the list of things it will create). Read it, type **y**, press Enter.
- It takes 2–5 minutes. At the end it prints **Outputs**.

### 4.3 Copy the outputs into `.env`
From the outputs, set in `.env`:
```
DATA_BUCKET=<DataBucketName value>
MEDIA_BUCKET=<MediaBucketName value>
TABLE_PREFIX=clearsky-dev-
```

### 4.4 Check it's alive
Open `<ApiUrl>/health` in a browser. You should see `{"ok": true, "service": "clearsky", ...}`.

### 4.5 Load the demo data into the real tables
```powershell
.\make.ps1 seed
```
This **deletes all items** in the `clearsky-dev-*` tables and reloads the demo data (fine now; nothing real is in them yet). Check:
```powershell
aws dynamodb scan --table-name clearsky-dev-Villages --select COUNT
```
`Count` should be **31**.

### 4.6 If you ever need to remove everything
```powershell
cd infra
python -m uv tool run --from aws-sam-cli sam delete --stack-name clearsky-dev
```
This deletes the stack and its tables. Only do it on purpose.

---

## 5. NASA FIRMS key for the fire-history map (Anyone)

1. Open <https://firms.modaps.eosdis.nasa.gov/api/map_key/>.
2. Enter an email address → **Submit**. The **MAP_KEY** arrives by email in a few minutes. It's free.
3. Put it in `.env`:
   ```
   FIRMS_MAP_KEY=<the key>
   ```
4. Build the layer:
   ```powershell
   cd C:\Users\prema\Desktop\clearsky
   .\make.ps1 firms
   ```
   This downloads Oct–Nov fire points for 2022–2025 around Sangrur, saves `data/layers/firms_2022_2025.geojson`, and writes a fire-history score into each village.
5. After the deploy (step 4), also push it to AWS:
   ```powershell
   cd backend
   .\.venv\Scripts\python.exe scripts\fetch_firms.py --apply-db --upload
   ```
6. For the deployed Lambdas, store the key in SSM (Git Bash): `./scripts/put_secrets.sh`.

**No key?** Download CSVs instead: <https://firms.modaps.eosdis.nasa.gov/download/> → **Create New Request** → area: custom box `75.55, 29.75, 76.40, 30.50` (W, S, E, N) → source **VIIRS S-NPP** → dates Oct 1 – Nov 30 for each year 2022–2025 → **CSV**. Put the downloaded `.csv` files in `data/raw/firms/` and run `.\make.ps1 firms`.

---

## 6. Confirm the village list (Team)

The demo uses **31 places in Sangrur district**. The names are real places, but the **coordinates are approximate** (marked `approx=true`). Please check the names and spellings with someone who knows the area.

| Block | Places |
|---|---|
| Sangrur | Sangrur (town), Balian, Ghabdan, Ubhawal, Badrukhan, Mangwal, Mehlan |
| Bhawanigarh | Bhawanigarh (town), Balad Kalan, Gharachon, Phagguwala, Kakra, Nadampur, Jhaneri |
| Sunam | Sunam (town), Longowal (town), Cheema (town), Ugrahan, Sheron, Chhajli, Jakhepal |
| Dhuri | Dhuri (town), Benra, Ghanauri Kalan, Bhalwan |
| Dirba | Dirba (town), Rogla |
| Lehragaga | Lehragaga (town), Lehal Kalan |
| Moonak | Moonak (town), Khanauri (town) |

Full details (Hindi and Punjabi spellings, aliases): `data/seed/villages.json`.

**Reply with one of:**
- "Villages OK", or
- the corrections (remove X, add Y in block Z, fix spelling of W).

**Real coordinates?** We can look them up with **Amazon Location Service** (a "Place Index"). It costs a few cents for 31 lookups and needs the deploy approval. Reply "use Amazon Location for coordinates" or "keep approximate".

---

## 7. Confirm the demo prices (Team)

These numbers are used only to show an estimated farmer payout in the demo. They are labeled "demo" everywhere and are **not real market prices**.

| Setting | Current demo value |
|---|---|
| Baling cost | ₹600 per acre |
| Transport cost | ₹8 per tonne per km |
| Platform fee | ₹50 per tonne |
| Buyer prices | Demo Pellet Plant ₹1,700/t · Demo CBG Plant ₹1,500/t · Demo Boiler Unit ₹1,900/t |
| Straw yield | 2.5 tonnes per acre |

Example: 8 acres → 20 t; a buyer 10 km away at ₹1,800/t gives an estimated payout of about ₹28,600.

**Reply:** "Prices OK", or the new numbers.

---

## 8. Up to 5 demo farmer phone numbers (Team)

These are the phones that will play **farmers** in the live demo. WhatsApp test numbers can only message **verified** recipients, max 5.

1. Each person who agrees to be a demo farmer shares their WhatsApp number in the format **`+91XXXXXXXXXX`** (country code, no spaces).
2. In Phase 4, someone with the Meta developer account adds them: <https://developers.facebook.com> → your app → **WhatsApp → API Setup** → **To** → **Manage phone number list** → add each number → each person enters the code they receive.
3. Send the list to Claude. The numbers go into `.env` / the seed only, never into public docs.

Operators, buyers and officers do **not** need WhatsApp numbers. They use the dashboard.

---

## 9. GitHub repository (You)

The code is already committed locally on branch `main`. To push it:

1. Go to <https://github.com/new>.
2. Repository name: `clearsky`. Choose **Private** or **Public** (the hackathon submission needs it public at the end).
3. **Don't** tick "Add a README", ".gitignore" or "license" (the repo already has them).
4. Click **Create repository** and copy the URL, e.g. `https://github.com/<your-username>/clearsky.git`.
5. Either send the URL to Claude, or push yourself:
   ```powershell
   cd C:\Users\prema\Desktop\clearsky
   git remote add origin https://github.com/<your-username>/clearsky.git
   git push -u origin main
   ```
   The first push opens a browser window to sign in to GitHub.
6. Add teammates: repo → **Settings → Collaborators → Add people**.

Teammates then run:
```powershell
git clone https://github.com/<your-username>/clearsky.git
cd clearsky
copy .env.example .env      # and fill it in
.\make.ps1 install          # macOS/Linux: make install
.\make.ps1 test
```
They (and their AI assistants) should read **`CONTEXT.md`** first.

---

## What to send back (copy, fill, paste into chat)

```
1. AWS profile set up:            yes / no
2. BEDROCK_MODEL_ID set in .env:  yes  (model: ______________)
3. Transcribe works:              yes / not yet
4. Deploy approved:               yes / no
5. FIRMS key in .env:             yes / CSVs in data/raw/firms / not yet
6. Villages:                      OK / corrections: ______ ; coordinates: Amazon Location / keep approximate
7. Prices:                        OK / new: ______
8. Demo farmer numbers:           +91__________, +91__________, ...
9. GitHub URL:                    https://github.com/______/clearsky.git
```
