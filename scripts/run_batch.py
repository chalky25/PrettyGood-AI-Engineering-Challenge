#!/usr/bin/env python3
"""Run multiple scenario calls sequentially with artifact capture."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from src.analysis.post_call import (
    analyze_call,
    append_to_bug_report,
    save_scenario_result,
    save_transcript,
)
from twilio.rest import Client

from src.config import settings
from src.conversation.scenario import Scenario, load_scenarios
from src.telephony.app import place_call


def wait_for_call_complete(call_sid: str, timeout: int = 300) -> bool:
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    deadline = time.time() + timeout
    while time.time() < deadline:
        call = client.calls(call_sid).fetch()
        if call.status in ("completed", "busy", "failed", "no-answer", "canceled"):
            return call.status == "completed"
        time.sleep(3)
    return False


def fetch_transcript_from_session(call_sid: str) -> tuple[str, list[dict]] | None:
    """Pull transcript from active or recently completed session."""
    from src.telephony.call_session import active_sessions, completed_transcripts

    session = active_sessions.get(call_sid)
    if session:
        return session.simulator.state.transcript_text(), session.simulator.state.transcript_json()
    return completed_transcripts.get(call_sid)


def run_batch(
    scenarios: list[Scenario],
    count: int,
    spacing_sec: int,
    analyze: bool,
) -> None:
    artifacts = Path(settings.artifacts_dir)
    (artifacts / "recordings").mkdir(parents=True, exist_ok=True)
    (artifacts / "transcripts").mkdir(parents=True, exist_ok=True)
    (artifacts / "scenario_results").mkdir(parents=True, exist_ok=True)

    selected = scenarios[:count]
    analyses = []
    call_index = 1

    for scenario in selected:
        call_id = f"call-{call_index:02d}"
        print(f"\n[{call_index}/{len(selected)}] Running scenario: {scenario.id}")

        try:
            call_sid = place_call(scenario.id)
        except Exception as e:
            print(f"  Failed to place call: {e}")
            continue

        print(f"  Call SID: {call_sid} — waiting for completion...")
        completed = wait_for_call_complete(call_sid)
        if not completed:
            print("  Call did not complete successfully.")
        else:
            print("  Call completed.")

        # Allow recording download webhook to finish
        time.sleep(5)

        transcript_data = fetch_transcript_from_session(call_sid)
        if transcript_data:
            text, json_turns = transcript_data
            meta = {
                "call_id": call_id,
                "call_sid": call_sid,
                "scenario_id": scenario.id,
                "turns": json_turns,
            }
            save_transcript(call_id, text, meta)
            print(f"  Transcript saved: artifacts/transcripts/{call_id}.txt")

            if analyze and text.strip():
                print("  Running post-call analysis...")
                analysis = analyze_call(scenario, text)
                save_scenario_result(call_id, analysis)
                analyses.append(analysis)
                print(
                    f"  Quality: {analysis.conversation_quality}/5, "
                    f"bugs: {len(analysis.bugs)}"
                )
        else:
            print("  No transcript in memory (server may have restarted).")

        call_index += 1
        if call_index <= len(selected):
            print(f"  Waiting {spacing_sec}s before next call...")
            time.sleep(spacing_sec)

    if analyses:
        append_to_bug_report(analyses, artifacts / "bug_report.md")
        print(f"\nBug report updated: {artifacts / 'bug_report.md'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=Path("scenarios"),
        help="Directory containing scenario YAML files",
    )
    parser.add_argument("--count", type=int, default=10, help="Number of calls to run")
    parser.add_argument(
        "--spacing",
        type=int,
        default=45,
        help="Seconds between calls",
    )
    parser.add_argument(
        "--no-analyze",
        action="store_true",
        help="Skip post-call Groq analysis",
    )
    args = parser.parse_args()

    if not settings.public_url:
        print("PUBLIC_URL must be set. Start ngrok and the server first.")
        sys.exit(1)

    scenarios = load_scenarios(args.scenarios)
    if not scenarios:
        print(f"No scenarios found in {args.scenarios}")
        sys.exit(1)

    run_batch(scenarios, args.count, args.spacing, analyze=not args.no_analyze)


if __name__ == "__main__":
    main()
