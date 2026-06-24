from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx
from dotenv import dotenv_values
from fastapi import FastAPI, Form, Query, Request, WebSocket
from fastapi.responses import PlainTextResponse, Response
from twilio.twiml.voice_response import Connect, VoiceResponse

from src.config import settings
from src.conversation.patient_simulator import PatientSimulator
from src.conversation.scenario import load_scenario
from src.telephony.call_session import (
    CallSession,
    active_sessions,
    create_outbound_call,
    handle_twilio_stream,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Pretty Good AI Patient Simulator")


def public_url() -> str:
    """Read PUBLIC_URL from .env so tunnel restarts don't require server restart."""
    vals = dotenv_values(Path(".env"))
    return (vals.get("PUBLIC_URL") or settings.public_url or "").rstrip("/")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/voice/outbound")
async def voice_outbound(
    request: Request,
    scenario: str = Query(default="schedule_simple"),
    CallSid: str = Form(default=""),
):
    """TwiML for outbound calls — connect bidirectional Media Stream."""
    scenarios_dir = Path("scenarios")
    scenario_path = scenarios_dir / f"{scenario}.yaml"
    if not scenario_path.exists():
        scenario_path = scenarios_dir / "schedule_simple.yaml"

    sc = load_scenario(scenario_path)
    simulator = PatientSimulator(sc)
    if CallSid:
        active_sessions[CallSid] = CallSession(CallSid, simulator)

    public = public_url()
    ws_url = public.replace("https://", "wss://").replace("http://", "ws://")

    response = VoiceResponse()
    connect = Connect()
    connect.stream(url=f"{ws_url}/ws/{CallSid}")
    response.append(connect)
    return Response(content=str(response), media_type="application/xml")


@app.websocket("/ws/{call_sid}")
async def websocket_endpoint(ws: WebSocket, call_sid: str):
    await ws.accept()
    await handle_twilio_stream(ws, call_sid)


@app.post("/voice/status")
async def voice_status(
    CallSid: str = Form(default=""),
    CallStatus: str = Form(default=""),
    RecordingUrl: str = Form(default=""),
):
    logger.info("Call %s status: %s", CallSid, CallStatus)
    if CallStatus == "completed" and RecordingUrl:
        session = active_sessions.get(CallSid)
        if session:
            session.simulator.mark_complete()
        asyncio.create_task(download_recording(CallSid, RecordingUrl))
    return PlainTextResponse("OK")


async def download_recording(call_sid: str, recording_url: str) -> None:
    """Download Twilio recording to artifacts/recordings/."""
    import asyncio

    out_dir = Path(settings.artifacts_dir) / "recordings"
    out_dir.mkdir(parents=True, exist_ok=True)

    mp3_url = recording_url + ".mp3"
    auth = (settings.twilio_account_sid, settings.twilio_auth_token)
    path = out_dir / f"call-{call_sid}.mp3"

    for attempt in range(5):
        try:
            await asyncio.sleep(3 * attempt)
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(mp3_url, auth=auth, follow_redirects=True)
                resp.raise_for_status()
                path.write_bytes(resp.content)
                logger.info("Saved recording to %s", path)
                return
        except Exception as e:
            logger.warning("Recording download attempt %d failed: %s", attempt + 1, e)


def place_call(scenario_id: str) -> str:
    url = public_url()
    if not url:
        raise ValueError("PUBLIC_URL must be set (ngrok or deployed URL)")
    return create_outbound_call(scenario_id, url)
