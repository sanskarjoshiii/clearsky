# Blog posts for AWS Builder Center

Two posts about clearsky for the **Top 5 blogs** prize of WeMakeDevs × AWS Environmental Hacks. The hackathon page asks for one thing: *"Write up what you built: the problem, the stack, what fought back."* Publish on AWS Builder Center and link the post in the submission.

They cover the same project from two angles, so they do not read as copies of each other:

| File | Angle | Suggested author | Diagrams | Screenshots |
|---|---|---|---|---|
| `blog-1-the-fire-starts-at-5pm.md` | The product and the air: why fires moved to the evening, why it is a logistics problem, the offer flow, the four role apps, what each AWS service does for one voice note, how pollution drops | Kamran (dashboards and approvals) | 01, 02, 03, 04, 11, 05, 13 | `shot-radar-and-chat`, `shot-baler-request` |
| `blog-2-our-headline-feature-could-not-fire.md` | The engineering, service by service with code and settings: webhook + SQS, Transcribe and Polly, the Strands agent, DynamoDB transactions, Cognito, Scheduler, the radar and real fire data, deployment | A teammate who worked on the backend and deploy | 06, 10, 07, 08, 09, 12 | `shot-radar` |

Spare screenshots, not used in either post: `shot-bookings.png` (declined → offered → confirmed in the admin table) and `shot-baler-route.png`.

## The diagrams

Every diagram in `img/` exists twice, with the same name:

- **`.gif`**: animated (dashes flow along the arrows, a pulse travels the numbered path, each card lights up as the pulse reaches it). 1200 px wide, 170 to 470 KB each, loops forever. The posts link to these.
- **`.png`**: the same picture as a still, at 2× (2400 px wide).

If the Builder Center editor does not accept or does not animate a GIF, upload the `.png` with the same name instead; nothing else in the post changes.

| # | Name | Shows |
|---|---|---|
| 01 | `the-3pm-gap` | Satellite window at midday, fires after 3 pm |
| 02 | `logistics-gap` | Farmer, baler and buyer, before and with clearsky |
| 03 | `one-voice-note` | The six steps from message to cleared field, plus the radar |
| 04 | `offer-lifecycle` | OFFERED → CONFIRMED → DONE, decline, expiry, escalation |
| 05 | `how-the-air-gets-cleaner` | Burnt versus baled, and the impact arithmetic |
| 06 | `architecture` | The whole stack on AWS |
| 07 | `voice-pipeline` | S3 → Transcribe → agent → Polly → WhatsApp |
| 08 | `double-booking` | One DynamoDB transaction, one winner |
| 09 | `burn-risk-score` | Three signals, one score, three colours |
| 10 | `webhook-and-queue` | Signature, dedupe, SQS, dead-letter queue, alarm |
| 11 | `four-doors` | Role apps and the registration and approval flow |
| 12 | `deploy-pipeline` | GitHub Actions, OIDC, SAM, S3 + CloudFront |
| 13 | `aws-jobs` | What each AWS service does for one voice note |

## Posting on Builder Center

The form has five fields: title, description, body, cover image and tags (five at most). `builder-center/blog-2-body.md` is post 2's body ready to paste as it is: the title line is removed (it has its own field), the demo-video placeholder line is removed (add it back when the video exists), and every image is a public link to this folder on the `blog-assets` branch of the GitHub repo (`raw.githubusercontent.com/sanskarjoshiii/clearsky/blog-assets/docs/blog/img/…`). Do not delete that branch while the post is live, or its images break.

| Field | Post 2 |
|---|---|
| Title | Our headline feature could not fire. The maths made it impossible. |
| Description | Engineering notes from clearsky, a WhatsApp-first system that gets a baler to a paddy field before the farmer burns the stubble. Service by service on AWS, with the code we shipped: a webhook that answers before it thinks, Hindi voice notes with Amazon Transcribe and Polly, a Strands agent that cannot touch another farmer's data, DynamoDB transactions that stop double booking, and everything that fought back in four days. |
| Tags | `aws-lambda`, `amazon-dynamodb`, `amazon-transcribe`, `amazon-sqs`, `serverless` |
| Cover | `img/cover-2-our-headline-feature-could-not-fire.png` (or `img/cover-2-graphic-only.png`) |

## Before publishing

1. **Add the demo video link** in the "Try it" section of both posts (marked *add the video link here*).
2. **Check the first-person lines against who is posting.** Post 1 says "my part of the build was everything after the WhatsApp message". Post 2 is written as "we" throughout, with two "I" lines ("I will come back to that", "the one I trust most"). Change these if a different person posts.
3. **Upload the images** from `img/` into the Builder Center editor in the order they appear, and keep the alt text.
4. **Tags** (five at most). Post 1: `aws-lambda`, `amazon-transcribe`, `amazon-cognito`, `serverless`, `ai`. Post 2: see the table above.
5. **Cover image.** Builder Center asks for 1200 × 675, at most 2 MB, jpg/png/webp, and says text in images is not recommended. `img/cover-1-the-fire-starts-at-5pm.png` and `img/cover-2-our-headline-feature-could-not-fire.png` are exactly 1200 × 675 (a sharper `@2x` copy sits beside each). `img/cover-2-graphic-only.png` is post 2's cover with almost no text (just 68 against 70), for the case where the headline version is cropped or the title next to it makes the text redundant. The 30 dots on cover 1 are a unit chart of "over 90% after 3 pm" (28 of 30), not hourly data.
6. Do not add pollution or AQI figures. Neither post states one, on purpose: the project has no sourced emission factor yet (`README.md` §16).

## Where the facts come from

- Problem statistics: only the sourced figures in `README.md` §1 and §16 (iFOREST via The Tribune, Outlook Business, ICC).
- System facts (8 functions, 12 tables, timeouts, thresholds, SLA, test counts) and every code or YAML snippet: the repo at the time of writing, 2026-10-10 (`infra/template.yaml`, `backend/src/clearsky/config.py`, `channels/voice.py`, `handlers/webhook.py`, `repo/processed.py`, `agent/llm.py`, `domain/registration.py`). A few snippets are trimmed for length; none is rewritten.
- "What fought back" stories: `CONTEXT.md` changelog and `PROGRESS.md`.
- Screenshots: the local stack in simulator mode with the rules bot, on synthetic seed data. Farmer names are synthetic and prices are demo values.
- The names, times and acres in diagram 08 (two farmers, one baler-day) are an illustration of the race, not data.

## Regenerating the diagrams

The diagrams are generated SVG (cards, arrows and SMIL animation), rendered with Playwright's Chrome to PNG and, frame by frame, to GIF. The generator scripts were kept outside the repo; ask if they should be added under `docs/blog/tools/`.
