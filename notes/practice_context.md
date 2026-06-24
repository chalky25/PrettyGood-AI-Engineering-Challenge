# Practice Context — Pivot Point Orthopedics

> Source: [pgai.us/athena](https://pgai.us/athena) demo signup + challenge materials.
> Test line for assessment: **+1-805-439-8008** (do NOT call the number on the Athena confirmation screen).

## Practice profile

- **Name:** Pivot Point Orthopedics
- **Domain:** Orthopedic care (appointments, likely follow-ups, refills, office info)
- **Patient flow (Athena demo):** Online booking flow collects **date of birth** as a key identifier

## Expected agent intake fields

Based on typical orthopedic front-desk AI agents and the challenge scenarios:

| Field | When asked | Notes |
|-------|------------|-------|
| Full name | Early in call | May need spelling confirmation |
| Date of birth | Identity verification | Demo emphasizes DOB |
| Reason for visit | Scheduling | e.g. knee pain, follow-up, post-op |
| Preferred date/time | Scheduling | Watch for weekend/hours validation |
| Insurance | New patients / billing questions | High hallucination risk |
| Pharmacy | Refills | Should verify patient on file |
| Phone / callback number | Confirmation | |

## Scheduling constraints to probe

- **Office hours:** Weekday-only is common for orthopedics — weekend trap is a known failure mode (see challenge example)
- **Appointment types:** New patient vs follow-up vs post-surgical
- **Locations:** Multi-site practices often confuse addresses
- **Availability:** Agent should check calendar, not confirm arbitrary times

## Failure modes to listen for

1. Confirms slot without checking hours or availability
2. Books/cancels without DOB or name verification
3. Loops on unclear requests ("the thing for my knee")
4. Ignores patient corrections ("Thursday, not Tuesday")
5. Gives confident wrong answers on insurance or hours
6. Poor barge-in / talk-over behavior
7. No human handoff when stuck

## Scenario ideas (14)

| ID | Intent | Bug class |
|----|--------|-----------|
| schedule_simple | New patient, knee pain, flexible timing | Missing intake |
| schedule_specific_time | Tuesday 2pm exactly | Date/time parsing |
| schedule_weekend_trap | Sunday 10am request | Business rules / hours |
| schedule_relative_date | "Tomorrow" vs "next week" | Relative date errors |
| reschedule_existing | Move Thursday appointment to Friday | Verification / wrong record |
| cancel_appointment | Cancel upcoming visit | Wrong appt / no recap |
| refill_standard | Ibuprofen 800mg refill | PHI / pharmacy gaps |
| refill_unknown_med | Obscure medication name | Hallucinated confirmation |
| info_hours_location | Hours + parking + address | Factual hallucination |
| info_insurance | "Do you take Blue Cross PPO?" | Overconfident coverage |
| edge_barge_in | Interrupt mid-sentence | Turn-taking |
| edge_vague_request | Unclear "read the thing" request | Clarification loop |
| edge_topic_switch | Schedule then switch to refill | Intent switching |
| edge_correction | Correct agent on wrong day | Error recovery |
| edge_future_dob | DOB June 25, 2026 (future/impossible) | Date validation |
| edge_police_reroute | Ask to connect to police (non-emergency) | Wrong escalation / outbound dial |
