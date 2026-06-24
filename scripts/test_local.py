#!/usr/bin/env python3
"""Local integration tests — no PUBLIC_URL / ngrok required."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow running as `python scripts/test_local.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from groq import Groq
from twilio.rest import Client

from src.analysis.post_call import analyze_call
from src.audio.deepgram_tts import synthesize_speech
from src.config import settings
from src.conversation.patient_simulator import PatientSimulator
from src.conversation.scenario import load_scenario, load_scenarios


def check(label: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    msg = f"  [{status}] {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return ok


def test_config() -> bool:
    print("\n=== Config ===")
    results = [
        check("TWILIO_ACCOUNT_SID", bool(settings.twilio_account_sid)),
        check("TWILIO_AUTH_TOKEN", bool(settings.twilio_auth_token)),
        check("TWILIO_PHONE_NUMBER", bool(settings.twilio_phone_number)),
        check("DEEPGRAM_API_KEY", bool(settings.deepgram_api_key)),
        check("GROQ_API_KEY", bool(settings.groq_api_key)),
        check("TARGET_PHONE_NUMBER", settings.target_phone_number == "+18054398008"),
    ]
    if settings.public_url:
        check("PUBLIC_URL", True, settings.public_url)
    else:
        check("PUBLIC_URL", True, "not set (OK for local tests; required for live calls)")
    return all(results)


def test_twilio() -> bool:
    print("\n=== Twilio API ===")
    try:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        account = client.api.accounts(settings.twilio_account_sid).fetch()
        ok_account = check("Account fetch", account.status == "active", account.friendly_name)

        numbers = client.incoming_phone_numbers.list(phone_number=settings.twilio_phone_number)
        ok_number = check(
            "Phone number owned",
            len(numbers) > 0,
            settings.twilio_phone_number,
        )
        return ok_account and ok_number
    except Exception as e:
        check("Twilio API", False, str(e))
        return False


def test_groq() -> bool:
    print("\n=== Groq API ===")
    try:
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": "Reply with exactly: ok"}],
            max_tokens=10,
        )
        text = (response.choices[0].message.content or "").strip()
        return check("Chat completion", "ok" in text.lower(), text[:50])
    except Exception as e:
        check("Groq API", False, str(e))
        return False


async def test_deepgram_tts() -> bool:
    print("\n=== Deepgram TTS ===")
    try:
        audio = await synthesize_speech("Hello, this is a test.")
        ok = len(audio) > 100
        return check("TTS synthesis", ok, f"{len(audio)} bytes mu-law audio")
    except Exception as e:
        check("Deepgram TTS", False, str(e))
        return False


def test_scenarios() -> bool:
    print("\n=== Scenarios ===")
    scenarios = load_scenarios(Path("scenarios"))
    ok = len(scenarios) >= 10
    check("Scenario count", ok, f"{len(scenarios)} loaded")
    for s in scenarios[:3]:
        check(f"  {s.id}", bool(s.goal and s.opening_line))
    return ok


def test_patient_simulator() -> bool:
    print("\n=== Patient simulator (text mode) ===")
    try:
        scenario = load_scenario(Path("scenarios/schedule_simple.yaml"))
        sim = PatientSimulator(scenario)

        agent_lines = [
            "Thank you for calling Pivot Point Orthopedics. How can I help you today?",
            "Sure, I can help with that. Can I get your full name and date of birth?",
            "And what's the reason for your visit?",
        ]

        opening = sim.opening_line()
        check("Opening line", len(opening) > 5, opening[:60])

        for line in agent_lines:
            reply = sim.respond_to_agent(line)
            check(f"Reply to agent", len(reply) > 2, reply[:70])

        transcript = sim.state.transcript_text()
        ok = "Patient:" in transcript and "Agent:" in transcript
        check("Transcript built", ok, f"{sim.state.patient_turn_count} patient turns")
        return ok
    except Exception as e:
        check("Patient simulator", False, str(e))
        return False


def test_post_call_analysis() -> bool:
    print("\n=== Post-call analysis ===")
    try:
        scenario = load_scenario(Path("scenarios/schedule_weekend_trap.yaml"))
        fake_transcript = """Patient: Can I come in Sunday at 10 am?
Agent: I've scheduled you for Sunday at 10 am. See you then!
Patient: Wait, are you open on Sundays?"""
        analysis = analyze_call(scenario, fake_transcript)
        ok = analysis.conversation_quality >= 1
        check("Rubric analysis", ok, f"quality={analysis.conversation_quality}, bugs={len(analysis.bugs)}")
        if analysis.bugs:
            check("Bug detected", True, analysis.bugs[0].title[:60])
        return ok
    except Exception as e:
        check("Post-call analysis", False, str(e))
        return False


async def test_local_server() -> bool:
    print("\n=== Local FastAPI server ===")
    import subprocess
    import time

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.telephony.app:app", "--host", "127.0.0.1", "--port", "8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        await asyncio.sleep(2)
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://127.0.0.1:8765/health", timeout=5.0)
            ok = resp.status_code == 200 and resp.json().get("status") == "ok"
            return check("GET /health", ok, str(resp.json()))
    except Exception as e:
        check("Local server", False, str(e))
        return False
    finally:
        proc.terminate()
        proc.wait(timeout=5)


async def run_all(skip_server: bool = False) -> int:
    print("Pretty Good AI — Local Test Suite")
    print("=" * 40)

    results = [
        test_config(),
        test_scenarios(),
        test_twilio(),
        test_groq(),
        await test_deepgram_tts(),
        test_patient_simulator(),
        test_post_call_analysis(),
    ]
    if not skip_server:
        results.append(await test_local_server())

    passed = sum(results)
    total = len(results)
    print(f"\n{'=' * 40}")
    print(f"Results: {passed}/{total} passed")

    if not settings.public_url:
        print("\nNote: Live Twilio calls need PUBLIC_URL (ngrok). Text-mode tests passed without it.")

    return 0 if passed == total else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-server", action="store_true")
    args = parser.parse_args()
    sys.exit(asyncio.run(run_all(skip_server=args.skip_server)))


if __name__ == "__main__":
    main()
