# Architecture

The patient simulator places outbound Twilio calls to the Pretty Good AI test line and participates in live voice conversations using a **hybrid scenario engine**: YAML files define *what* to test (persona, goal, constraints, success criteria), while **Groq Llama 3.3 70B** generates *how* the patient speaks each turn based on the agent's replies. This keeps calls reproducible for bug hunting while sounding like a real patient rather than a rigid script.

Audio flows through Twilio Media Streams as 8 kHz mu-law. Inbound audio (the agent's voice) streams to **Deepgram Nova-2** for speech-to-text with utterance-end detection (~900 ms silence) so the patient does not talk over the agent. The transcript is sent to Groq, the reply is synthesized via **Deepgram Aura** TTS, and audio frames stream back to Twilio. Calls are recorded by Twilio; on completion, recordings download to `artifacts/recordings/` and transcripts save to `artifacts/transcripts/`. A post-call **Groq rubric** compares each transcript against the scenario's success criteria and appends findings to `artifacts/bug_report.md`.

We chose Twilio + Deepgram + Groq because all three have free or low-cost tiers suitable for 10+ test calls under $20, Groq's inference latency (~200 ms) keeps turn-taking natural, and the pipeline separates concerns cleanly without over-engineering. The main tuning levers are endpointing delay, patient reply length, and scenario constraints—not infrastructure.

## Future work

**Regression golden suite.** Pin a fixed set of high-signal scenarios (e.g. `schedule_weekend_trap`, `edge_barge_in`, `edge_spanish`) and re-run them after each simulator change. Cache post-call analysis results and diff new transcripts against a baseline — flag when a previously reproducible bug stops appearing (agent may have improved) or when call quality regresses (e.g. shorter transcripts, missing recordings). This would turn the current manual call-and-review loop into a repeatable smoke test for both the patient bot and the agent under test.
