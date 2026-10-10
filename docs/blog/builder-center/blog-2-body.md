*Engineering notes from clearsky: a WhatsApp agent, eight Lambda functions and twelve DynamoDB tables that get a baler to a paddy field before the farmer burns it. Built in four days for the Air track of WeMakeDevs × AWS Environmental Hacks. This post goes service by service, with the code and the settings we actually shipped.*

---

**The feature was called the Burn Risk Radar, and its whole job was to turn a field red.**

Red meant: this field is harvested, nobody has booked a pickup, and it is likely to be burnt soon. A district officer sees red, taps **Alert village**, every farmer there gets a one-tap WhatsApp booking, and the pin turns green. That was the money shot of our demo.

We set the red threshold at 70 out of 100. It looked sensible. Then we wrote the test for the demo, and it could not pass.

A field has to be bookable for the alert to do anything, and a field is only bookable if there are at least three days left before wheat sowing. At three days left, with the worst possible fire history, the score comes to 68. Not 70.

No field that could still be saved could ever be red. We had built an alarm that only rang after the house was gone.

We lowered the threshold to 60, wrote down why, and moved on. A day later the same feature broke again, for a better reason. I will come back to that.

## The problem, in four sentences

Paddy farmers in Punjab and Haryana have 20 to 25 days between harvesting rice and sowing wheat, and the leftover straw is in the way. Burning it is free; collecting it costs more than it earns. Monitoring satellites pass between about 10:30 am and 1:30 pm, and iFOREST found that over 90% of large farm fires in Punjab in 2024-25 were lit after 3 pm (it was 3% in 2021), so the fires are simply timed around the count. The balers exist and the straw buyers exist; what is missing is the scheduling between them.

clearsky is that scheduling. A farmer sends a WhatsApp voice note. An agent books the nearest free baler before the sowing deadline and routes the straw to a paying buyer. Balers, buyers and the district officer use a web dashboard.

## The stack on one page

![clearsky on AWS: the path of one farmer message, the dashboard and the scheduled jobs](https://raw.githubusercontent.com/sanskarjoshiii/clearsky/blog-assets/docs/blog/img/06-architecture.gif)

Every box in that picture is serverless. Between two farmers' messages nothing is running.

| Piece | What it does for us | The setting that matters |
|---|---|---|
| **API Gateway (HTTP API)** | The WhatsApp webhook and the dashboard's REST API | A Cognito JWT authorizer is the default on every route; the webhook opts out |
| **AWS Lambda** (8 functions) | Webhook, processor, API, risk job, reminders, offers job, fire-data ingest, health | Python 3.12 on arm64; 30 s by default, 120 s for the processor |
| **Amazon SQS** + dead-letter queue | Sits between the webhook and the slow work | Visibility timeout 720 s, three receives, then the dead-letter queue |
| **Amazon DynamoDB** (12 tables) | Farmers, fields, balers, buyers, bookings, the capacity ledger | On-demand billing; a condition on every write that matters |
| **Amazon Transcribe** | Hindi voice note to text | Batch job, `MediaFormat="ogg"`, `LanguageCode="hi-IN"` |
| **Amazon Polly** | The reply, as a Hindi voice note | Voice Kajal, neural engine, mp3 |
| **Amazon Cognito** | Sign-up, three role groups, JWTs | Role attributes are not writable by the client |
| **EventBridge Scheduler** | Hourly risk scoring, 6 pm reminders, a 15-minute sweep for unanswered offers | `ScheduleExpressionTimezone: Asia/Kolkata` |
| **Amazon S3 + CloudFront** | Voice media, the fire-history layer, the dashboard | Media expires after 7 days; presigned links use the regional endpoint |
| **SSM Parameter Store, CloudWatch, SNS** | Secrets; alarms on the dead-letter queue | SecureString parameters under `/clearsky/{stage}/` |

On the open-source side: the **Strands Agents SDK** runs the farmer agent, **AWS SAM** describes the whole stack in one template, and **Powertools for AWS Lambda** gives us structured logs and the HTTP resolver.

The rest of this post takes those rows one at a time.

## 1. API Gateway, Lambda and SQS: the webhook answers before it thinks

WhatsApp's Cloud API delivers a message to your webhook and expects a fast 200. If it does not get one, it sends the message again. Our real work (transcribing audio, running an agent, writing a booking) takes seconds, sometimes a minute.

![The webhook Lambda checks, dedupes and queues; the processor Lambda does the slow work](https://raw.githubusercontent.com/sanskarjoshiii/clearsky/blog-assets/docs/blog/img/10-webhook-and-queue.gif)

So the webhook Lambda has a ten-second timeout and does three cheap things.

**It checks that the message really came from Meta.** Meta signs the raw request body with our app secret. We recompute the HMAC and compare in constant time:

```python
def verify_signature(raw_body: bytes, header: str | None, app_secret: str) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(header.removeprefix("sha256="), expected)
```

One detail to get right: API Gateway may hand the body to Lambda base64-encoded. The signature is over the original bytes, so the handler decodes first and only then verifies.

**It makes sure the message is new.** A retry from Meta carries the same message id. One conditional write to DynamoDB turns "have we seen this?" into a single atomic step, with no read first:

```python
self.t.put_item(
    Item={"wa_message_id": wa_message_id, "status": "processing",
          "ttl": int(time.time()) + TTL_SECONDS},
    ConditionExpression="attribute_not_exists(wa_message_id)",
)
```

If the condition fails, this is a duplicate and we drop it. The row deletes itself after two days through DynamoDB's TTL, so the table never needs cleaning.

**It puts the message on SQS and returns 200.**

The queue is four lines of SAM that do a lot of work:

```yaml
InboundQueue:
  Type: AWS::SQS::Queue
  Properties:
    VisibilityTimeout: 720  # 6 × the processor timeout
    SqsManagedSseEnabled: true
    RedrivePolicy:
      deadLetterTargetArn: !GetAtt InboundDLQ.Arn
      maxReceiveCount: 3
```

The processor Lambda reads with `BatchSize: 1` and `ReportBatchItemFailures`, so one bad message never drags a good one back onto the queue. The visibility timeout is six times the processor's 120 seconds, so a slow voice note is not handed out a second time while the first attempt is still working. After three failed receives the message lands in the dead-letter queue, where it is kept for fourteen days, and a CloudWatch alarm on that queue's depth sends an email through SNS.

The result: a farmer's message is never silently lost, and never processed twice.

## 2. Amazon Transcribe and Amazon Polly: a farmer speaks, the system answers in the same voice

Farmers speak; they do not type. Voice is not a nice extra here, it is the main input.

![The voice pipeline: S3, Amazon Transcribe, the agent, Amazon Polly, and back to WhatsApp](https://raw.githubusercontent.com/sanskarjoshiii/clearsky/blog-assets/docs/blog/img/07-voice-pipeline.gif)

### Voice in: Amazon Transcribe

The whole of our Transcribe integration is one function. If you want to do the same, these are the steps.

**Step 1: get the audio into S3.** A WhatsApp audio message carries a media id, not the audio. The processor downloads the file from Meta and writes it to a private bucket. Transcribe batch jobs read their input from S3.

**Step 2: start the job.** WhatsApp voice notes are Ogg files, and we pass them through unchanged: no ffmpeg, no conversion layer.

```python
s3.put_object(Bucket=s.media_bucket, Key=key, Body=data, ContentType="audio/ogg")
tr = boto3.client("transcribe", region_name=s.aws_region)
name = _job_name(msg_id)
out_key = f"transcripts/{name}.json"
tr.start_transcription_job(
    TranscriptionJobName=name,
    Media={"MediaFileUri": f"s3://{s.media_bucket}/{key}"},
    MediaFormat="ogg",
    LanguageCode=s.transcribe_language,  # "hi-IN"
    OutputBucketName=s.media_bucket,
    OutputKey=out_key,
)
```

Job names must be unique and only allow a limited set of characters, while WhatsApp message ids contain others. So `_job_name` replaces anything outside `[0-9a-zA-Z._-]` and adds six random hex characters, which also keeps an SQS retry from colliding with its own first attempt.

**Step 3: wait for it.** We poll `get_transcription_job` every 1.5 seconds until the status is `COMPLETED` or `FAILED`, up to a deadline.

**Step 4: read the transcript.** Because we set `OutputBucketName` and `OutputKey`, the result is a JSON file in our own bucket:

```python
body = s3.get_object(Bucket=s.media_bucket, Key=out_key)["Body"].read()
transcripts = json.loads(body)["results"]["transcripts"]
return " ".join(t["transcript"] for t in transcripts).strip()
```

**The permissions** are two Transcribe actions, plus read and write on the bucket the audio lives in:

```yaml
- Effect: Allow
  Action: [transcribe:StartTranscriptionJob, transcribe:GetTranscriptionJob, polly:SynthesizeSpeech]
  Resource: "*"
- Effect: Allow
  Action: [s3:GetObject, s3:PutObject, s3:HeadObject]
  Resource: !Sub "${MediaBucket.Arn}/*"
```

The bucket blocks all public access, is encrypted, and has a lifecycle rule that deletes voice media after seven days. A farmer's voice is not ours to keep.

**What fought back, part one: 1.6 seconds.** We tested with a real Hindi voice note. The job took 61.6 seconds. Our code gave up waiting at 60. The farmer would have received "the audio was not clear, please try again" for a transcription that succeeded 1.6 seconds later. The wait is now a setting, `TRANSCRIBE_TIMEOUT_S`, with a default of 90 seconds, inside the processor's 120-second Lambda timeout, inside the queue's 720-second visibility timeout. Those three numbers have to nest, and now they do.

**Part two: a silent chat feels broken.** A batch job is not instant. So the very first thing the processor does with a voice note is reply *"🎙️ Sun raha hoon…"* (I am listening), before any transcription starts.

**Part three: do not pay for audio you will refuse.** We cap voice notes at 60 seconds. Instead of finding that out from Transcribe, we read it from the file itself. The last page of an Ogg file holds the total sample count, and Opus always counts at 48 kHz (trimmed from our code):

```python
idx = data.rfind(b"OggS")
granule = struct.unpack_from("<q", data, idx + 6)[0]
return round(granule / 48000, 2)
```

A long note is refused in microseconds, with a polite "please send one under a minute", and never reaches S3 or Transcribe.

**Part four: the service was not switched on.** On our first AWS account Transcribe was not enabled at all. So speech-to-text became a setting, `STT_PROVIDER`: `transcribe`, any OpenAI-compatible endpoint, or `none` (the farmer is asked to type). When Transcribe came up on the second account, switching to it was one parameter.

### Voice out: Amazon Polly

If the farmer sent a voice note, the answer goes back as text and as audio. Polly is a single synchronous call:

```python
audio = polly.synthesize_speech(
    Text=speech[:2900],
    VoiceId=s.polly_voice,      # "Kajal"
    Engine=s.polly_engine,      # "neural"
    LanguageCode="hi-IN",
    OutputFormat="mp3",
)["AudioStream"].read()
key = f"media/out/{msg_id}.mp3"
s3.put_object(Bucket=s.media_bucket, Key=key, Body=audio, ContentType="audio/mpeg")
return presigned_get_url(s.media_bucket, key, 3600)
```

Three small things made the difference between "works" and "sounds right":

- **Strip the emoji first.** The text reply has ✅ and 📨 in it. Nobody wants those read aloud, so they are removed before synthesis.
- **Cap the text.** We cut at 2,900 characters so a long reply can never exceed what one request accepts.
- **WhatsApp fetches the audio itself.** We do not upload the mp3 to Meta. We give WhatsApp a presigned S3 link that is valid for one hour, and it downloads the file. That link caused one of our deployment bugs, described below.

The text always goes first, and a failure in Polly is caught and logged. A farmer can lose the voice reply. They can never lose the booking because of it.

## 3. The Strands Agents SDK: an agent that cannot touch someone else's field

The farmer agent has nine tools: `get_my_profile`, `resolve_village`, `register_farmer`, `register_field`, `book_pickup`, `get_my_bookings`, `confirm_harvest`, `reschedule` and `cancel_booking`. The dangerous question with any tool-using model is whose data it can reach.

Our answer is that the phone number is never something the model gets to say. The tools are built per message, and each one closes over the sender's number, which comes from the signature-verified webhook:

```python
def build_tools(phone: str, ctx: TurnContext) -> list[Any]:
    """The agent's tools, bound to `phone`. The phone number is never an LLM-visible argument."""

    @tool
    def book_pickup(field_id: str) -> dict[str, Any]:
        return ctx.record("book_pickup", {"field_id": field_id}, impl.book_pickup(phone, field_id))
    ...
```

A model that is confused, or talked into something, can still only act as the person who sent the message. Validation (acres between 0.5 and 100, dates inside the season, a village that exists) lives in the tools too, not in the prompt. The agent runs at a low temperature with a short reply limit, keeps the last ten turns of the conversation (stored in DynamoDB with a seven-day TTL), and each phone number is limited to twenty turns an hour.

**What fought back:** the plan said Amazon Bedrock. On the AWS account we had, Bedrock model access was not usable, and we found that out early. Strands made the recovery easy, because the agent does not care which model sits behind it. Tools, prompt and memory are the same for every provider; only the model object changes:

```python
if p == "bedrock":
    return BedrockModel(model_id=s.bedrock_model_id, temperature=s.agent_temperature,
                        max_tokens=s.agent_max_tokens, region_name=s.aws_region)
if p == "openai":
    return OpenAIModel(client_args=client_args, model_id=s.llm_model_id,
                       params={"temperature": s.agent_temperature, "max_tokens": s.agent_max_tokens})
```

The deployed stack runs an OpenAI model through that same Strands agent, and moving to Bedrock is one parameter, `LLM_PROVIDER=bedrock`, on an account where it is enabled.

We also wrote something we had not planned: a **deterministic rules bot** that fills the same four slots (name, village, acres, harvest date) from Hindi, Punjabi, Hinglish or English, with no model at all. It became the default for local development and the fallback in production. If the LLM call fails or is throttled, the same message is answered by the rules bot, and the farmer still gets a booking.

## 4. Amazon DynamoDB: two farmers, one free slot

Harvest comes in waves. Many farmers in one village will message in the same evening, and they are all competing for the same few baler-days.

![Two bookings race for one baler-day; one transaction wins](https://raw.githubusercontent.com/sanskarjoshiii/clearsky/blog-assets/docs/blog/img/08-double-booking.gif)

Each booking is one DynamoDB transaction with four writes: the baler's capacity ledger for that day, the booking itself, the field's status, and the buyer's reserved tonnes. Each write carries a condition. If two requests race, exactly one transaction commits; the other is cancelled as a whole, and the matcher tries its next-best slot.

**What fought back:** DynamoDB condition expressions cannot do arithmetic. You cannot write "booked + 10 <= capacity". So the code computes `capacity - acres` first and the condition compares against that:

```python
capacity_cond = "attribute_not_exists(booked_acres) OR booked_acres <= :cap_minus_a"
```

The same pattern guards the step that came later. A booking is now an *offer* that a baler must accept, because a baler who never saw the job is a silent no-show, and a silent no-show is a burnt field. Accepting an offer, the 15-minute job that expires unanswered ones, and a farmer cancelling can all hit the same row at the same moment. Each write names the state it expects:

```python
condition="#s = :offered AND (attribute_not_exists(expires_at) OR expires_at > :now)"
```

so exactly one of them wins.

We tested this by faking the race: two requests read the ledger, then both try to commit on stale data. One booking exists afterwards. That test is the one I trust most in the repo.

All twelve tables are on-demand (`PAY_PER_REQUEST`), which is the right default for a workload that is silent for hours and then busy for one evening.

## 5. Amazon Cognito: sign-up is open, roles are not

Balers and buyers register themselves, so the user pool allows self sign-up with an email and a password. The risk with open sign-up is obvious: what stops someone from making themselves an admin?

Two things. First, a role is a Cognito **group** (`officer`, `operator`, `buyer`), and a new user is in none of them. The API reads the group from the verified token and treats a user with no group as `pending`: they can use the registration endpoints and nothing else. Second, the attributes that tie an account to a baler or a buyer are readable by the dashboard but not writable by it:

```yaml
ReadAttributes: [email, custom:district, custom:buyer_id, custom:baler_id]
WriteAttributes: [email]
```

API Gateway does the token checking for us. The JWT authorizer is the default for the whole HTTP API, and a route has to opt out explicitly:

```yaml
Auth:
  DefaultAuthorizer: CognitoJwt
  Authorizers:
    CognitoJwt:
      IdentitySource: $request.header.Authorization
      JwtConfiguration:
        issuer: !Sub "https://cognito-idp.${AWS::Region}.amazonaws.com/${UserPool}"
        audience: [!Ref UserPoolClient]
```

By the time a request reaches our Lambda the signature and expiry have already been verified, and the code only reads claims.

When the district officer approves an application, the API Lambda makes two admin calls:

```python
client.admin_update_user_attributes(
    UserPoolId=pool, Username=username,
    UserAttributes=[{"Name": ATTRIBUTE_FOR[app.role], "Value": entity_id}],
)
client.admin_add_user_to_group(UserPoolId=pool, Username=username, GroupName=GROUP_FOR[app.role])
```

Both are safe to repeat. If the second one fails, the application stays pending with its progress saved, and pressing Approve again finishes the job instead of creating a second baler.

## 6. EventBridge Scheduler: three clocks

Three things happen without anyone asking, and each is a Lambda with a schedule attached in the same template:

```yaml
Events:
  Daily:
    Type: ScheduleV2
    Properties:
      ScheduleExpression: cron(0 18 * * ? *)
      ScheduleExpressionTimezone: Asia/Kolkata
```

- **Every hour**, the risk job re-scores every field and every village.
- **Every 15 minutes**, the offers job finds offers that no baler answered within two hours, releases the reserved capacity and offers the field to the next-best baler.
- **At 6 pm India time**, the reminders job messages farmers whose harvest is tomorrow ("Kal katai?", with yes and no buttons) and farmers whose baler comes tomorrow.

The time zone line is the reason we used Scheduler. Writing "6 pm in India" as 12:30 UTC works until someone forgets the half hour.

## 7. The radar, and the day real data arrived

![How the burn-risk score is built from three signals](https://raw.githubusercontent.com/sanskarjoshiii/clearsky/blog-assets/docs/blog/img/09-burn-risk-score.gif)

Back to the feature that could not fire.

After the threshold fix, the radar worked on our demo data. Then we loaded real fire history: **19,926 VIIRS fire detections** from NASA FIRMS, for October and November of 2022 through 2025. The file sits in S3, a Lambda turns it into a fire-history score for every village, and the dashboard draws the same layer on the map.

Every red field on the map turned amber.

Our demo data had scattered its "at risk" fields across random villages. With invented fire history that was fine. With real fire history, only a handful of villages had burnt often enough for a field there to reach 60. Reality did not match our seed file, and reality was right.

We did not touch the formula. We changed the demo data so its at-risk fields sit in villages where the real record says fires happen.

![The Burn Risk Radar on demo data: ten red fields in the villages with real fire history](https://raw.githubusercontent.com/sanskarjoshiii/clearsky/blog-assets/docs/blog/img/shot-radar.png)

It is a small thing, but it is the moment the radar stopped being a drawing and started being a model: the red pins are now where the last four seasons say they should be.

## 8. Secrets and alarms

Nothing secret is in the repository or in a Lambda environment variable. The WhatsApp token, the app secret, the LLM key and the FIRMS key are SecureString parameters under `/clearsky/{stage}/` in SSM Parameter Store. The code loads them on first use and caches them for five minutes, so a rotated key reaches warm Lambdas without a redeploy.

Three CloudWatch alarms watch the stack: any message in the dead-letter queue, any error in the processor, and more than five errors in the API. Give the template an email address and all three notify it through one SNS topic. For a four-day project that is a small amount of YAML, and it is the difference between "a farmer's message failed" and "a farmer's message failed and somebody knows".

## 9. Deployment fought back hardest

![From git push to a live stack: test, OIDC, build, sam deploy, dashboard, smoke test](https://raw.githubusercontent.com/sanskarjoshiii/clearsky/blog-assets/docs/blog/img/12-deploy-pipeline.gif)

We deploy from `main` with GitHub Actions. The job trades GitHub's OIDC token for short-lived AWS credentials, builds the dependency layer, runs `sam deploy`, builds the dashboard, syncs it to S3, invalidates CloudFront and finishes with two smoke tests. There are no long-lived AWS keys anywhere.

Getting there was a short, honest list. None of these appear in a unit test.

- **`pywin32` in a Linux Lambda.** We develop on Windows. SAM's Python builder pulled a Windows-only package into the function bundle. Dependencies now go into a Lambda layer built with `uv pip install --python-platform aarch64-manylinux_2_28`, and the function zip holds only our own code.
- **A presigned URL that redirected.** The fire layer loaded locally and failed in the browser once deployed. Presigned S3 URLs on the global endpoint answered with a 307 redirect to the regional one, which broke both CORS and the signature. Signing against the regional endpoint (`https://s3.{region}.amazonaws.com`) fixed the map, and also fixed the Polly voice-reply links, which had the same problem and had not been noticed yet.
- **A certificate blocked by someone else's DNS.** The ACM certificate for our domain failed validation. The domain's DNS host published CAA records that did not allow Amazon to issue for it. One added CAA record later, it passed.
- **A 401 on a request that carries no credentials.** Browsers send a CORS preflight `OPTIONS` without the Authorization header. Our JWT authorizer rejected it. The preflight needed its own route with no authorizer.
- **The pipeline that could not assume its own role.** The first run failed, because the role's trust policy and the token's subject did not match. Adding a GitHub `environment` to the job would have changed that subject again, so the workflow carries a comment saying not to.
- **The account itself.** Our first AWS account's access key stopped working mid-hackathon. We moved accounts. Because the entire stack is one SAM template, "move accounts" was a deploy, not a rebuild.

## Does it clean the air?

This is the Air track, so the question deserves a straight answer.

The mechanism is direct: a field that is baled before the sowing deadline is a field nobody needs to burn, and open burning of rice straw is what puts the smoke there in the first place. Every pickup clearsky completes is straw that leaves as bales and becomes pellets, biogas or boiler fuel.

The app calculates pollution avoided for each cleared field as *straw tonnes × a published emission factor*, and freezes that figure on the booking when the baler taps Done, so history never changes if a factor is later revised.

But there is no emission factor in the repository. The setting is empty, a factor without a citation is ignored by the code, and the impact page shows no pollution number until the team configures a sourced one. We would rather show nothing than show a number we made up.

What we can state: the loop works end to end on a deployed stack, with real WhatsApp messages. What we cannot state: a measured change in air quality. That needs a harvest season, a real district and patience.

## What we learned

**First: write the test for the demo before you tune the feature.** The red threshold bug was invisible until a test tried to do exactly what the demo promised.

**Second: put the hard rule in the database, not in the code's good intentions.** "Never double-book" is a condition on a write. "Never act as another farmer" is a closure. "Never promote yourself" is an attribute the client cannot write. "Never invent a number" is a setting that refuses unsourced values. Rules that live in a comment get broken at 3 am.

**Third: make your timeouts nest.** Transcribe wait, Lambda timeout, queue visibility timeout: 90, 120, 720. Get the order wrong and a slow success looks like a failure, or one message is processed twice.

**Fourth: deploy early.** Six of our worst problems only existed on AWS. We met them on day three, with a day to spare. Meeting them on day four would have been a different blog post.

**Fifth: build the boring fallback.** The rules bot was meant to be a stopgap for a missing model. It is why a farmer still gets a reply when the model does not answer.

## By the numbers

- 4 days, 1 repository, 1 SAM template
- 8 Lambda functions, 12 DynamoDB tables, 1 queue and its dead-letter queue
- 9 agent tools, 5 possible brains (rules, OpenAI, Anthropic, Gemini, Bedrock), 1 setting to choose
- Over 220 backend tests, 13 end-to-end browser tests
- 19,926 real fire detections behind the radar
- 0 emission factors we invented

---

**Try it**

- Live: https://clearsky.akkki.tech
- Code: https://github.com/sanskarjoshiii/clearsky

Built by Team Atherion (Sanskar, Kamran, Akshay and Anushka) for the WeMakeDevs × AWS Environmental Hacks, Air track, 8-11 October 2026.

**Sources**

- iFOREST findings on fire timing, as reported by The Tribune: https://www.tribuneindia.com/news/delhi/satellites-miss-majority-of-stubble-fires-delhi-air-pollution-underestimated-report
- Outlook Business, the evening detection gap: https://www.outlookbusiness.com/news/punjab-haryana-evening-stubble-burning-detection-gap-delhi-pollution
- Fire history: NASA FIRMS (VIIRS), October-November 2022 to 2025.

The screenshot shows synthetic demo fields. No real farmer data appears in this post.
