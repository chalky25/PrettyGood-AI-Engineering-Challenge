#!/usr/bin/env python3
"""Run bug-hunt scenarios sequentially, waiting for each call to finish."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from twilio.rest import Client

from src.analysis.post_call import analyze_call, append_to_bug_report, save_scenario_result
from src.config import settings
from src.conversation.scenario import load_scenario
from src.telephony.app import place_call
from src.telephony.call_session import completed_transcripts

SCENARIOS = [
    "schedule_weekend_trap",
    "edge_barge_in",
    "edge_emergency_911",
    "edge_spanish",
    "edge_hipaa_probe",
    "edge_vague_request",
    "edge_correction",
    "edge_future_dob",
    "edge_police_reroute",
]


def wait_for_call(call_sid: str, timeout: int = 180) -> bool:
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    deadline = time.time() + timeout
    while time.time() < deadline:
        call = client.calls(call_sid).fetch()
        if call.status in ("completed", "busy", "failed", "no-answer", "canceled"):
            return call.status == "completed"
        time.sleep(3)
    return False


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    analyses = []
    call_num = 2  # call-01 schedule_simple already completed

    for scenario_id in SCENARIOS:
        scenario = load_scenario(root / "scenarios" / f"{scenario_id}.yaml")
        print(f"\n[{call_num}/{len(SCENARIOS)}] {scenario_id} -> {settings.target_phone_number}")

        try:
            call_sid = place_call(scenario_id)
        except Exception as e:
            print(f"  FAILED to place: {e}")
            continue

        print(f"  SID: {call_sid}")
        ok = wait_for_call(call_sid)
        print(f"  Completed: {ok}")
        time.sleep(8)  # recording download

        data = completed_transcripts.get(call_sid)
        if not data:
            txt_path = root / "artifacts" / "transcripts" / f"call-{call_sid}.txt"
            if txt_path.exists():
                data = (txt_path.read_text(), [])
        if data:
            text, _ = data
            if text.strip():
                analysis = analyze_call(scenario, text)
                save_scenario_result(f"call-{call_num:02d}", analysis)
                analyses.append(analysis)
                print(f"  Bugs: {len(analysis.bugs)}, quality: {analysis.conversation_quality}/5")
        else:
            print("  No transcript captured")

        call_num += 1
        if call_num <= len(SCENARIOS):
            print("  Waiting 45s...")
            time.sleep(45)

    if analyses:
        append_to_bug_report(analyses, root / "artifacts" / "bug_report.md")

    subprocess.run([sys.executable, "scripts/build_flowchart.py"], cwd=root)
    print("\nDone -> artifacts/agent_flowchart.md, artifacts/bug_report.md")


if __name__ == "__main__":
    main()
