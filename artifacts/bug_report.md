# Bug Report

## Incorrect Date of Birth Handling

- **Severity:** Medium
- **Call:** schedule_simple (turn 3)
- **Details:** Your date of birth is July fourth two thousand for demo purposes.
- **Expected:** The agent should have asked for the patient's date of birth instead of providing a default value, and then updated the patient's profile with the correct date of birth provided by the patient.
- **Repro:** scenario id: schedule_simple, steps to reproduce: patient corrects the agent's incorrect date of birth assumption

## Failed to acknowledge language barrier and switch to English

- **Severity:** High
- **Call:** edge_french (turn 1)
- **Details:** This call may be recorded for quality and training purposes. Thanks for calling PivotPoint Orthopedics, part of Pretty Good ai. Am I speaking with Jordan?
- **Expected:** The agent should have acknowledged the language barrier and politely asked to continue in English, as the patient started speaking in French.
- **Repro:** edge_french scenario, patient starts speaking in French

## Lack of clear error recovery and poor handling of language switch

- **Severity:** High
- **Call:** edge_french (mid-call)
- **Details:** I'll need to confirm your information first. Would you like to use your phone number to look up your record? If so, please provide the number you have on file. If not, I can confirm your name and date of birth again. Which would you prefer?
- **Expected:** The agent should have clearly acknowledged the language switch and confirmed that they can proceed with the conversation in English, rather than repeating the same questions.
- **Repro:** edge_french scenario, patient switches to English

## Inability to proceed with appointment scheduling due to language issues

- **Severity:** High
- **Call:** edge_french (turn 10)
- **Details:** I can't proceed further right now, but I can make sure our clinic support team follows up with you. Would you like me to connect you to our patient support team?
- **Expected:** The agent should have been able to proceed with scheduling the appointment or provide a clear explanation for the transfer to the patient support team.
- **Repro:** edge_french scenario, patient requests appointment scheduling

## Failed to handle Spanish initially

- **Severity:** High
- **Call:** edge_spanish (`call-CA4fc535c43cc47918768c34547a00f5b9.txt`, turn 2)
- **Details:** Patient opened in Spanish (*"Hola, necesito hacer una cita por favor"*) and continued in Spanish (*"Sí, necesito ver a un doctor por dolor de rodilla"*). Agent responded only in English with *"I speaking with Jordan?"* — no language acknowledgment, no offer to continue in Spanish or switch to English.
- **Expected:** Agent should detect non-English input and either respond in Spanish or politely ask: *"I can help in English — would that be okay?"*
- **Repro:** `edge_spanish` scenario — patient speaks Spanish for first 2–3 turns

## Spanish intent misread as billing question

- **Severity:** Medium
- **Call:** edge_spanish (`call-CA4fc535c43cc47918768c34547a00f5b9.txt`, turn 5)
- **Details:** Patient asked in Spanish where to schedule a doctor appointment (*"dónde puedo hacer una cita con un doctor"*). Agent replied: *"are you looking to schedule an appointment with a doctor, or do you have a question about billing or payments?"* — patient had to switch to English manually.
- **Expected:** Agent should recognize scheduling intent from context and proceed with intake, not introduce an unrelated billing path.
- **Repro:** `edge_spanish` scenario — continue in Spanish after opening line

## Wrong caller assumption ("Jordan") during Spanish call

- **Severity:** Medium
- **Call:** edge_spanish (`call-CA4fc535c43cc47918768c34547a00f5b9.txt`, turn 3)
- **Details:** Agent asked *"I speaking with Jordan?"* despite patient never mentioning that name and speaking as Carmen Ruiz.
- **Expected:** Agent should ask for the caller's name or use a neutral greeting, not assume a demo profile name.
- **Repro:** Any call where patient does not identify as Jordan — also seen in `schedule_simple`, `schedule_weekend_trap`, `edge_french`

## Name collected after DOB without verification

- **Severity:** Medium
- **Call:** edge_spanish (`call-CA4fc535c43cc47918768c34547a00f5b9.txt`, turns 7–11)
- **Details:** Agent requested DOB first, said *"Thank you"*, then patient volunteered *"My name Carmen Ruiz"* — agent never asked for or confirmed full name before proceeding to book.
- **Expected:** Collect and confirm full name before or with DOB; spell-check if needed (same failure mode as English calls).
- **Repro:** `edge_spanish` scenario — observe intake order after language switch

## Hallucinated provider name during Spanish flow

- **Severity:** High
- **Call:** edge_spanish (`call-CA4fc535c43cc47918768c34547a00f5b9.txt`, turn 13)
- **Details:** Agent said *"appointment for knee pain with doctor Medulla when available"* — patient never requested or mentioned any provider named Medulla.
- **Expected:** Agent should offer real available providers or ask for preference without inventing names.
- **Repro:** `edge_spanish` scenario — reach scheduling confirmation after English switch

## Truncated booking confirmation mid-sentence

- **Severity:** Low
- **Call:** edge_spanish (`call-CA4fc535c43cc47918768c34547a00f5b9.txt`, turn 11)
- **Details:** Agent utterance cut off: *"To confirm you'd like to book an appoint"* — same talk-over/truncation pattern seen in English `schedule_simple` when patient mentions insurance.
- **Expected:** Agent should complete the confirmation sentence before waiting for patient response.
- **Repro:** `edge_spanish` scenario — patient provides name after DOB

## Failed to reject Sunday appointment and didn't offer alternative

- **Severity:** High
- **Call:** schedule_weekend_trap (mid-call)
- **Details:** Just schedule for Sunday at 10 am, please. (Agent didn't respond with office hours)
- **Expected:** The agent should have immediately responded with something like 'Our office is closed on Sundays. The next available appointment is...' to inform the patient about the office hours and offer an alternative.
- **Repro:** schedule_weekend_trap scenario: Patient requests a Sunday appointment, and the agent fails to reject it and offer a weekday alternative.

## Poor error recovery and verification

- **Severity:** High
- **Call:** schedule_weekend_trap (turn 5)
- **Details:** I have your name as Maria Lopts. Your date of birth as November third nineteen seventy eight.
- **Expected:** The agent should have properly verified the patient's information before proceeding and not introduced incorrect information (e.g., 'Lopts' instead of 'Lopez').
- **Repro:** schedule_weekend_trap scenario: Patient provides their name and date of birth, but the agent incorrectly records or verifies the information.

## Abrupt call termination

- **Severity:** High
- **Call:** edge_barge_in (end of call)
- **Details:** Goodbye.
- **Expected:** The agent should have continued to assist the patient or transferred the call to a live support agent as previously mentioned.
- **Repro:** edge_barge_in scenario, interrupt the agent mid-explanation and observe the call termination

## Poor error recovery and context loss

- **Severity:** High
- **Call:** edge_barge_in (after patient correction)
- **Details:** It looks like there's already an appointment booked in the system, but you mentioned you don't have one.
- **Expected:** The agent should have properly addressed the discrepancy, provided a clear explanation, and offered a solution without abruptly ending the call.
- **Repro:** edge_barge_in scenario, correct the agent when they mention an existing appointment and observe the error recovery

## Missing morning preference inquiry

- **Severity:** Medium
- **Call:** edge_barge_in (scheduling discussion)
- **Details:** You already have an appointment booked for this type of visit.
- **Expected:** The agent should have inquired about the patient's preference for a morning appointment as part of the scheduling process.
- **Repro:** edge_barge_in scenario, reach the scheduling discussion and observe if the agent inquires about morning preference
