#!/usr/bin/env python3
"""Run a single scenario call or start the webhook server."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import uvicorn

from src.config import settings
from src.conversation.scenario import load_scenario
from src.telephony.app import place_call


def validate_settings(for_call: bool = False) -> None:
    missing = []
    if not settings.twilio_account_sid:
        missing.append("TWILIO_ACCOUNT_SID")
    if not settings.twilio_auth_token:
        missing.append("TWILIO_AUTH_TOKEN")
    if not settings.twilio_phone_number:
        missing.append("TWILIO_PHONE_NUMBER")
    if not settings.deepgram_api_key:
        missing.append("DEEPGRAM_API_KEY")
    if not settings.groq_api_key:
        missing.append("GROQ_API_KEY")
    if for_call and not settings.public_url:
        missing.append("PUBLIC_URL")
    if missing:
        print("Missing required environment variables:", ", ".join(missing))
        print("Copy .env.example to .env and fill in values.")
        sys.exit(1)


def cmd_serve(args: argparse.Namespace) -> None:
    validate_settings()
    uvicorn.run(
        "src.telephony.app:app",
        host=settings.host,
        port=settings.port,
        reload=args.reload,
    )


def cmd_call(args: argparse.Namespace) -> None:
    validate_settings(for_call=True)
    scenario_path = Path("scenarios") / f"{args.scenario}.yaml"
    if not scenario_path.exists():
        print(f"Scenario not found: {scenario_path}")
        sys.exit(1)

    load_scenario(scenario_path)  # validate
    print(f"Placing outbound call for scenario: {args.scenario}")
    print(f"  From: {settings.twilio_phone_number}")
    print(f"  To:   {settings.target_phone_number}")
    call_sid = place_call(args.scenario)
    print(f"Call initiated. SID: {call_sid}")
    print("Monitor server logs for conversation. Recording saves on completion.")


def cmd_test(args: argparse.Namespace) -> None:
    import asyncio
    from scripts.test_local import run_all

    code = asyncio.run(run_all(skip_server=args.skip_server))
    sys.exit(code)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pretty Good AI patient simulator")
    sub = parser.add_subparsers(dest="command", required=True)

    serve_p = sub.add_parser("serve", help="Start FastAPI webhook server")
    serve_p.add_argument("--reload", action="store_true")
    serve_p.set_defaults(func=cmd_serve)

    call_p = sub.add_parser("call", help="Place one outbound test call")
    call_p.add_argument(
        "--scenario",
        default="schedule_simple",
        help="Scenario id (filename without .yaml)",
    )
    call_p.set_defaults(func=cmd_call)

    test_p = sub.add_parser("test", help="Run local integration tests (no PUBLIC_URL needed)")
    test_p.add_argument("--skip-server", action="store_true")
    test_p.set_defaults(func=cmd_test)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
