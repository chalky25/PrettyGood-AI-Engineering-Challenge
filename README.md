# Pretty Good AI — Patient Simulator

Automated voice bot for the [Pretty Good AI Engineering Challenge](https://pgai.us/athena). It calls **+1-805-439-8008** as a simulated patient, records conversations, transcribes both sides, and analyzes the agent for bugs.

## Stack

- **Twilio** — outbound calls + recording
- **Deepgram** — STT (Nova-2) + TTS (Aura)
- **Groq** — Llama 3.3 70B patient simulator (free tier)
- **FastAPI** — Media Streams webhook server

## Quick start

### 1. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in TWILIO_*, DEEPGRAM_API_KEY, GROQ_API_KEY, TWILIO_PHONE_NUMBER
```

### 2. Expose webhooks

```bash
ngrok http 8000
# Set PUBLIC_URL in .env to the ngrok HTTPS URL
```

### 3. Start server

```bash
python main.py serve
```

### 4. Test locally (no ngrok needed)

```bash
python main.py test
```

Verifies Twilio, Groq, Deepgram, patient simulator (text mode), and the local FastAPI server.

### 5. Place one test call (requires PUBLIC_URL)

```bash
python main.py call --scenario schedule_simple
```

### 6. Run a batch of calls

```bash
python scripts/run_batch.py --scenarios scenarios/ --count 10
```

Or run the curated bug-hunt sequence:

```bash
python scripts/run_bug_hunt.py
```

Artifacts land in `artifacts/recordings/`, `artifacts/transcripts/`, `artifacts/scenario_results/`, and `artifacts/bug_report.md`.

### 7. Regenerate bug report and flowcharts

```bash
python scripts/analyze_transcripts.py
python scripts/build_flowchart.py
```

## Scenarios

19 YAML scenarios in `scenarios/` covering scheduling, refills, info requests, and edge cases. Each defines persona, goal, constraints, and success criteria for post-call analysis.

## What we changed after early calls

- **Endpointing:** `ENDPOINTING_MS=900` — tuned so the patient waits for the agent to finish before speaking
- **Opening delay:** Patient waits ~4s for the agent greeting before the first utterance (`call_session.py`)
- **Reply length:** `MAX_REPLY_WORDS=25` keeps patient replies short and natural for voice
- **TTS voice:** `DEEPGRAM_TTS_VOICE=aura-asteria-en` for clear, conversational pacing

## Submission checklist

- [x] Working Python voice bot
- [x] README + [ARCHITECTURE.md](ARCHITECTURE.md)
- [x] `.env.example`
- [ ] 10+ mp3 recordings in `artifacts/recordings/`
- [ ] 10+ transcripts in `artifacts/transcripts/`
- [ ] Bug report finalized in `artifacts/bug_report.md`
- [ ] Loom walkthrough link (add below)
- [ ] AI debugging screen recording link (add below)
- [ ] Single Twilio number used (E.164) for all calls

**Loom walkthrough:** _add link_  
**AI debugging recording:** _add link_  
**Caller phone number (E.164):** _add your Twilio number_

## Project layout

```
main.py                 # serve | call | test
scripts/
  run_batch.py          # batch runner
  run_bug_hunt.py       # sequential bug-hunt scenarios
  analyze_transcripts.py
  build_flowchart.py
src/telephony/          # Twilio + WebSocket handler
src/conversation/       # Hybrid scenario + Groq patient sim
src/audio/              # Deepgram STT/TTS + mulaw
src/analysis/           # Post-call bug scoring
scenarios/              # 19 test scenarios
artifacts/              # recordings, transcripts, bug report, flowcharts
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for design rationale.

## Future work

A **regression golden suite** would re-run a pinned set of scenarios after each change, cache analysis results, and diff transcripts against a baseline so you can tell whether the simulator or the agent regressed — without manually replaying every call.
