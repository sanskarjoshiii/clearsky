---
title: "Production setup end to end: AWS deploy, LLM key, WhatsApp on our own number, then remove the farmer simulator"
assignee: akkki007
labels: [setup, infra, whatsapp, release]
---

## Why

The code for Phases 0–7 and 9 is done and passes locally: 177 backend tests, Vitest and Playwright. Nothing is live yet. You hold the **AWS account** and the **LLM API key**, so this issue takes clearsky from "works on a laptop with the simulator" to "a farmer messages our WhatsApp number from their own phone and everything happens on AWS". After that we remove the dashboard's sample farmer chat (the simulator).

Primary guide: **`SETUP_GUIDE.md`** (step numbers below refer to it). This issue adds the order, the checks, and the parts the guide doesn't cover yet (our own number, removing the simulator).

## Order of work and checks

### A. Local sanity (30 min) · SETUP_GUIDE §0
- [ ] `git pull`, `.\make.ps1 install`, `.\make.ps1 test` (177 pass), `.\make.ps1 e2e` (3 pass).
- [ ] Book once through the simulator, mark Done as the operator, see the buyer's delivery.

### B. LLM key · §1
- [ ] `.env`: `LLM_PROVIDER` (`openai` | `anthropic` | `gemini`), `LLM_MODEL_ID` (a model **with tool calling**), `LLM_API_KEY`, and `LLM_BASE_URL` only for OpenAI-compatible providers.
- [ ] `python -m uv run python scripts\check_aws.py --invoke-llm` → "LLM provider ✅" and "LLM invoke ✅".
- [ ] `.\make.ps1 chat`: the Gurpreet message books within ≤ 3 turns; an off-topic message gets a polite redirect (Phase 3 DoD).
- [ ] Record 5 transcripts into `docs/agent_transcripts.md` (Hindi, Hinglish, Punjabi, English, off-topic): `scripts\chat_cli.py --local --transcript ..\docs\agent_transcripts.md --title "Hindi" -m "…"`.

### C. Voice · §2
- [ ] Choose `STT_PROVIDER`: `transcribe` (enable Transcribe on the account first, §2.1) or `openai` + `STT_MODEL_ID` (a speech-to-text model from the provider).
- [ ] Polly voice replies need nothing extra once deployed.

### D. AWS access + deploy · §3–§4
- [ ] New IAM user + access key; `aws configure --profile clearsky`; `aws sts get-caller-identity` works. (The old `Kamran_03` key returns `InvalidClientTokenId`.)
- [ ] $10 budget alarm.
- [ ] `infra\samconfig.toml` `parameter_overrides`: `LlmProvider`, `LlmModelId`, `SttProvider` (+ `SttModelId`), `WaMode=simulator` for the first deploy, optional `AlarmEmail`.
- [ ] `.\make.ps1 build` → `.\make.ps1 deploy -Confirm yes` → save the Outputs.
- [ ] `.env`: `TABLE_PREFIX`, `DATA_BUCKET`, `MEDIA_BUCKET` → `.\scripts\put_secrets.ps1` → deploy again so Lambdas read the secrets.
- [ ] `.\make.ps1 seed` → `aws dynamodb scan --table-name clearsky-dev-Villages --select COUNT` = 31 → `<ApiUrl>/health` OK.
- [ ] FIRMS (§8): key → `.\make.ps1 firms` (commit the layer + updated `villages.json`) → `fetch_firms.py --apply-db --upload`. **Without this the radar can't show red.**

### E. Dashboard live · §5–§6
- [ ] `create_demo_users.py` for the officer, one buyer and two operators.
- [ ] Amplify app (monorepo root `dashboard`), five `VITE_*` variables, SPA rewrite rule. Put the Amplify URL in `CorsOrigins` and redeploy.
- [ ] Sign in as each role on the Amplify URL (desktop and phone).

### F. WhatsApp on **our own number** (new: not fully in SETUP_GUIDE yet)

Meta gives every app a **test number** (§7.1). It is fine for development but can only message the ≤ 5 phones you verify. To have farmers message **a specific number we own**:

1. **Pick the number.** A SIM/landline that can receive an SMS or voice call. It must **not be active on the regular WhatsApp or WhatsApp Business app** (remove it there first; Meta's docs explain the current migration options). Keep the SIM: re-verification may need it.
2. **Business portfolio.** <https://business.facebook.com> → the portfolio that owns the clearsky app. Add business details. **Business verification** (Security Centre) raises messaging limits and is needed for more than test use. Start it early; it can take days.
3. **Add the number.** WhatsApp Manager → **Phone numbers → Add phone number** → display name (e.g. "clearsky", which Meta reviews against the business name) → category → verify with the SMS/voice code.
4. **Register it for the Cloud API.** In the app's **WhatsApp → API Setup**, select the new number in the "From" dropdown and copy its **Phone number ID**. If the number shows as not registered, register it once with a 6-digit two-step PIN you choose (Meta documents this as `POST /{phone-number-id}/register` with `messaging_product=whatsapp` and `pin`). Store the PIN safely.
5. **Payment method.** WhatsApp Manager → **Payment settings**: add a card. Conversations beyond the free allowance are billed by Meta, separately from AWS.
6. **Permanent token** (§7.4: system user with `whatsapp_business_messaging` + `whatsapp_business_management`, assigned to the app **and** the WhatsApp account).
7. **App mode.** Switch the Meta app from Development to **Live** (App settings → Basic needs a privacy policy URL; a simple page on the Amplify site or GitHub Pages is enough). In Development mode it only talks to test recipients.
8. **Update secrets.** `.env`: `WA_PHONE_NUMBER_ID=<new id>`, `WA_ACCESS_TOKEN=<permanent token>`, `WA_APP_SECRET`, `WA_VERIFY_TOKEN` (+ `WA_API_VERSION` if the dashboard shows a different version) → `.\scripts\put_secrets.ps1`.
9. **Cloud mode.** `samconfig.toml` → `WaMode=cloud` → deploy.
10. **Webhook.** App → WhatsApp → **Configuration**: Callback URL = `WebhookUrl` output, Verify token = `WA_VERIFY_TOKEN` → Verify and save → subscribe the **`messages`** field. If messages to the new number don't arrive, check that the app is subscribed to the WhatsApp Business Account. Meta's "subscribed apps" setting for the WABA is usually set automatically; confirm it in the docs or Graph API Explorer.
11. **Templates.** Submit the four in `docs/whatsapp_templates.md` (Utility, Hindi), plus the two new ones from the accept/reject issue if that ships first. Wait for **Approved**.
12. **Smoke test from a real phone** (not a test recipient, once Live):
    - [ ] "Namaste" → greeting; the Gurpreet message → booking with the date and baler.
    - [ ] Hindi **voice note** → "🎙️ Sun raha hoon…" → booking reply **and** a voice reply.
    - [ ] Operator taps Done on the dashboard → the phone gets "khet saaf ho gaya ✅".
    - [ ] Officer alerts that farmer's village → the phone gets the offer → tap **HAAN, book karo** → booked; the radar pin turns into a solid dot within 10 s.
    - [ ] Demo clock to the day before harvest → **Send tomorrow's reminders** → the phone gets the HAAN/NAHI reminder.
    - [ ] `scripts\e2e.py --api-url <ApiUrl>` passes; the SQS DLQ is empty; CloudWatch shows no processor errors.

> Seeded demo farmers have placeholder numbers and are marked `synthetic`. clearsky **never** messages them, even in cloud mode. Real farmers appear as soon as they message the number.

### G. Remove the sample farmer chat from the super admin
Once F passes, the simulator is no longer needed in the deployed admin:
- In `WaMode=cloud` it is **already hidden**: the rail button only shows when `config.wa_mode === "simulator"` (`dashboard/src/components/Shell.tsx`), and `/api/sim/*` return 404 (`handlers/api.py` `_sim_guard`).
- To delete it entirely (team decision):
  - Remove `dashboard/src/components/Simulator.tsx`, the rail and bottom-nav buttons, the `sim=1` URL flag and the `SAMPLES` prompts.
  - Remove the `useConversation`/`useSimSend`/`useSimInbox`/`useSimReset` hooks and `/api/sim/*` from `handlers/api.py` plus their tests (`tests/test_api.py::test_simulator_*`).
  - Rewrite `docs/demo_runbook.md` for the real phone, and update the Playwright test `farmer books in the WhatsApp simulator` to call `/webhook/whatsapp` with a signed payload (see `backend/scripts/e2e.py`) instead.
  - **Keep** `WA_MODE=simulator` as the backend default for local development, and `make chat` for testing the agent without WhatsApp.

## Acceptance criteria (definition of done)
- [ ] Stack `clearsky-dev` deployed with the real LLM, the chosen STT, `WaMode=cloud` and FIRMS data loaded.
- [ ] Dashboard live on Amplify; officer, buyer and operator can sign in.
- [ ] Farmers use **our own WhatsApp number** from their own phones; every check in F.12 passes.
- [ ] Templates approved; permanent token in SSM; no secrets in Git (`git log -p | Select-String WA_ACCESS` returns nothing).
- [ ] The simulator is not visible in the deployed admin (and removed from code if the team agreed).
- [ ] `SETUP_GUIDE.md` updated with anything that differed in practice (Meta UI changes, limits you hit), `CONTEXT.md` changelog + state updated, `PROGRESS.md` Phases 4–7 marked ✅ with the dates.
