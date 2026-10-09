# WhatsApp message templates (submit in Meta Business Manager)

clearsky starts some conversations itself (reminders, officer alerts, "field cleared", and the booking confirmation once a baler accepts). WhatsApp only allows that **outside the 24-hour window** with an **approved template**. Inside the window the same text goes out as a normal or button message, so the farmer sees the same words either way.

The body text below must match `backend/src/clearsky/channels/templates.py` exactly. `{{1}}`, `{{2}}` are filled in by the code.

**Where:** <https://business.facebook.com> → WhatsApp Manager → **Message templates** → **Create template**.
**For every template:** Category **Utility** · Language **Hindi (hi)** (the text is Hinglish, Roman script; the code sends `language.code = WA_TEMPLATE_LANGUAGE`, default `hi`). Approval usually takes minutes to a few hours.

---

## 1. `pickup_reminder`
Sent at 18:00 IST the day before the farmer's harvest date.

- **Body**
  ```
  Namaste {{1}} ji 🌾 Kya kal ({{2}}) aapke dhaan ki katai hai? Katai ke baad baler aapka khet saaf karega. Kripya HAAN ya NAHI dabaiye.
  ```
  Sample values: `{{1}}` = `Gurpreet`, `{{2}}` = `24 Oct`
- **Buttons:** type **Quick reply**, two buttons, in this order:
  1. `HAAN`
  2. `NAHI`

## 2. `baler_tomorrow`
Sent at 18:00 IST the day before a confirmed pickup.

- **Body**
  ```
  Namaste {{1}} ji 🚜 Kal ({{2}}) baler aapke khet aayega. Parali na jalayein. Koi badlav ho to yahin likhein.
  ```
  Sample values: `Gurpreet`, `25 Oct`
- **Buttons:** none

## 3. `village_alert`
Sent when a district officer clicks **Alert village** on the Burn Risk Radar.

- **Body**
  ```
  Namaste ji 🌾 {{1}} mein baler khali hai. Parali jalane ki jagah muft mein khet saaf karwaiye. Booking ke liye HAAN dabaiye.
  ```
  Sample value: `Bhawanigarh`
- **Buttons:** **Quick reply**, one button: `HAAN, book karo`

> "muft" (free) is accurate only while clearance is free for the farmer in the demo pricing. If the team changes pricing so farmers pay, change this wording here **and** in `templates.py` before submitting.

## 4. `field_cleared`
Sent when a baler operator taps **Done** on the operator dashboard.

- **Body**
  ```
  ✅ {{1}} ji, aapka khet aaj saaf ho gaya. Parali na jalane ke liye dhanyavaad! 🙏
  ```
  Sample value: `Gurpreet`
- **Buttons:** none

## 5. `booking_confirmed`
Sent when a baler **accepts** the farmer's request on the baler dashboard. This is the first message that tells the farmer the pickup is certain.

- **Body**
  ```
  ✅ {{1}} ji, {{2}} ko baler {{3}} aapka khet saaf karne aayega. Parali na jalayein. 🙏
  ```
  Sample values: `{{1}}` = `Gurpreet`, `{{2}}` = `25 Oct`, `{{3}}` = `Manjit Singh`
- **Buttons:** none

## 6. `booking_changed`
Sent when the first baler declined (or did not answer) and the next baler can only come on a **different day**.

- **Body**
  ```
  📨 {{1}} ji, aapki pickup ki tareekh badal kar {{2}} ho gayi hai. Baler ke confirm karte hi batayenge.
  ```
  Sample values: `Gurpreet`, `26 Oct`
- **Buttons:** none

## 7. `booking_delayed`
Sent when no baler accepted (after `OFFER_MAX_ATTEMPTS` balers, or when nobody is left). The field appears on the officer's radar at the same time.

- **Body**
  ```
  {{1}} ji, abhi tak kisi baler ne aapki pickup confirm nahi ki. Officer ko bata diya hai, jaldi sampark hoga. Kripya parali na jalayein. 🙏
  ```
  Sample value: `Gurpreet`
- **Buttons:** none

> Templates 5–7 are new with the baler accept/decline flow and **need Meta approval** like the others. Until they are approved, these three messages reach a farmer only inside the 24-hour window (which is the usual case right after a booking).

---

## How button taps come back

Quick-reply buttons on templates return a **payload**; the code sets it to `<action>:<field_id>`:

| Button | Payload | What happens |
|---|---|---|
| HAAN (reminder) | `confirm:F-…` | harvest confirmed; a pickup request is sent to a baler if the field had none |
| NAHI (reminder) | `later:F-…` | bot asks for the new harvest date, then reschedules |
| HAAN, book karo (alert) | `alertbook:F-…` | a pickup request goes to the best baler at once and the radar pin turns green; the farmer gets `booking_confirmed` when the baler accepts |

Payloads for someone else's field are ignored (the field's phone must match the sender).
