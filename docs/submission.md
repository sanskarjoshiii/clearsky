# Hackathon submission answers (Team Atherion · clearsky)

Short form, in the style of the earlier submission. Checked against `infra/*.yaml`, `infra/samconfig.toml` and `CONTEXT.md`.

## Project title

clearsky - AI on WhatsApp that turns paddy straw into income, not smoke

## Tracks

Air (main) + Waste & Energy. Line to use for Waste & Energy: "Paddy straw is crop waste: clearsky collects it and routes it to pellet plants, biomass boilers and biogas plants as fuel, instead of it being burnt in the field."

## Demo video description

clearsky stops stubble burning in Punjab: a farmer sends one WhatsApp voice note in Hindi, and an AI agent books the nearest baler and sells the straw to industry instead of it being burnt. Watch the live demo of the WhatsApp agent and the officer, baler and buyer dashboards, built serverless on AWS by Team Atherion for AWS Environmental Hacks 2026.

## What does your project do?

clearsky stops stubble burning in Punjab. After the paddy harvest, farmers have only a few weeks to clear the field before sowing wheat; finding a baler is hard, so many burn the straw and the smoke reaches cities like Delhi. Meanwhile balers sit idle and industries buy straw as fuel. With clearsky, a farmer sends one WhatsApp message or voice note in Hindi, Punjabi or English; an AI agent books the nearest free baler and the best-paying buyer and tells the farmer the payout. Balers, buyers and district officers each get a dashboard, and officers see a Burn Risk Radar that flags fields likely to burn so they can alert a village before it happens. Built for farmers, baler operators, straw-buying industries and district officers.

## How did you use AWS in your project?

AWS open source: AWS SAM (whole stack as one template, deployed from GitHub Actions), Strands Agents SDK (the WhatsApp farmer agent with booking tools), Powertools for AWS Lambda (API routing and structured logs), boto3, and the Amplify JS library (Cognito sign-in in the dashboard).

AWS services: Lambda — 8 serverless functions (webhook, AI message processor, dashboard API, hourly risk scorer, reminders, offer expiry, satellite fire ingest). API Gateway (HTTP API) — WhatsApp webhook and REST API with a Cognito JWT authorizer. SQS + DLQ — WhatsApp gets an instant reply while the AI and voice work runs from the queue. DynamoDB — 12 tables; every booking is one transaction, so a baler or buyer can never be double-booked. Cognito — officer, baler and buyer roles with self sign-up and approval. Transcribe — Hindi voice notes to text. Polly — Hindi voice replies. S3 — voice files, satellite fire data and the dashboard. CloudFront + ACM — dashboard on our own domain over HTTPS. EventBridge Scheduler — hourly risk scoring and 6 pm IST reminders. Systems Manager Parameter Store — secrets. CloudWatch + SNS — logs and alarms. IAM — OIDC role for keyless deploys. Live: clearsky.akkki.tech

## Team leader's contributions (Sanskar)

Built the core of clearsky: the WhatsApp farmer agent that understands text and voice in Hindi, Punjabi and English, the message pipeline (webhook, SQS, Transcribe, Polly) and the booking engine that picks the nearest free baler and best buyer in one DynamoDB transaction. Also handled the deployment on AWS with SAM, the live WhatsApp number and the CI/CD pipeline.

## Second team member's contributions (Kamran)

Built the three role dashboards: the officer's Burn Risk Radar with village alerts, the phone-first baler app (accept, route, Done) and the buyer app (deliveries, demand and price), plus the home and impact pages. Also built the AWS backend behind them: the REST API on Lambda and API Gateway, the DynamoDB data model and the scheduled jobs.

## Third team member's contributions (Akshay)

Worked on the AI model behind the farmer agent: chose and set up the LLM, tuned the prompts so it replies in the farmer's language and never invents prices, and tested it end to end on the live WhatsApp number. Also built the pollution-impact view that shows straw saved and pollution avoided per field and per village.

## Fourth team member's contributions (Anushka)

Worked on the emission-factor method: pollution avoided is calculated from the tonnes of straw not burnt and a published emission factor, and a number is only shown when its source is cited. Also built the approvals flow for every role: balers and buyers register, the officer approves or rejects them, and each role gets its own sign-in.

## Help us evaluate you: your feedback on the AWS services you used

Service access on a new account is confusing: Transcribe returned a bare "SubscriptionRequired" and Bedrock model access was unavailable, with no message saying why or how to enable it, so we had to run the agent on an external model. S3 presigned URLs signed against the global endpoint got a 307 redirect for our ap-south-1 bucket, which broke CORS and the signature in the browser until we forced the regional endpoint. API Gateway HTTP API says it handles CORS, but with a Cognito JWT authorizer on a proxy route the browser's OPTIONS preflight got a 401, and we had to add a separate OPTIONS route. The CloudFront certificate must be in us-east-1, which is easy to miss, and our first one failed because of CAA records in DNS. Our first GitHub OIDC deploy failed with only "not authorized to perform sts:AssumeRoleWithWebIdentity" because GitHub's subject format had changed. Transcribe batch jobs took about a minute for a few seconds of audio, which is slow for a chat.

## What did you like about the AWS services you used?

DynamoDB transactions were the standout: one TransactWriteItems reserves the baler's day, writes the booking and reserves the buyer's tonnes, and CancellationReasons tells us exactly which check failed, so double-booking cannot happen. SQS with a dead-letter queue made the WhatsApp webhook simple: reply fast, process later, never lose a message. Cognito groups with the HTTP API JWT authorizer gave us role-based access with almost no auth code. EventBridge Scheduler's timezone support let us schedule 6 pm IST directly. Polly's Hindi voice made the bot usable for farmers who prefer listening to reading. SAM let us deploy the whole serverless stack from one template through GitHub Actions with no AWS keys.
