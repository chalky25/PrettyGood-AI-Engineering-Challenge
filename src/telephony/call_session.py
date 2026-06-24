from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect
from twilio.rest import Client

from src.audio.deepgram_stt import DeepgramSTTStream
from src.audio.deepgram_tts import synthesize_speech
from src.audio.mulaw import chunk_audio, decode_twilio_payload, encode_twilio_payload
from src.config import settings
from src.conversation.patient_simulator import PatientSimulator

logger = logging.getLogger(__name__)

# Active and recently completed call sessions keyed by call_sid
active_sessions: dict[str, "CallSession"] = {}
completed_transcripts: dict[str, tuple[str, list[dict]]] = {}


class CallSession:
    def __init__(self, call_sid: str, simulator: PatientSimulator):
        self.call_sid = call_sid
        self.simulator = simulator
        self.stream_sid: Optional[str] = None
        self.ws: Optional[WebSocket] = None
        self.stt: Optional[DeepgramSTTStream] = None
        self._responding = False
        self._pending_agent_text = ""
        self._response_lock = asyncio.Lock()
        self._opened_sent = False
        self._greet_timeout_task: Optional[asyncio.Task] = None
        self._stt_language = "en"
        self._dtmf_sent = False

    def _stt_language_for_scenario(self) -> str:
        if self.simulator.scenario.primary_language == "es":
            return "multi"
        return "en"

    async def attach_websocket(self, ws: WebSocket) -> None:
        self.ws = ws
        self._stt_language = self._stt_language_for_scenario()
        self.stt = DeepgramSTTStream(
            on_transcript=self._schedule_transcript,
            language=self._stt_language,
        )
        await self.stt.connect()

    def _schedule_transcript(self, text: str, is_final: bool) -> None:
        asyncio.create_task(self._on_transcript(text, is_final))

    async def _on_transcript(self, text: str, is_final: bool) -> None:
        if not is_final:
            self._pending_agent_text = text
            return
        agent_text = text.strip()
        if not agent_text:
            return
        logger.info("Agent said: %s", agent_text)
        await self._handle_agent_utterance(agent_text)

    async def _handle_agent_utterance(self, agent_text: str) -> None:
        async with self._response_lock:
            if self._greet_timeout_task and not self._greet_timeout_task.done():
                self._greet_timeout_task.cancel()
            if self._responding:
                return
            self._responding = True
            try:
                if self.simulator.state.should_end():
                    await self._hangup()
                    return

                patient_reply = self.simulator.respond_to_agent(agent_text)
                logger.info("Patient says: %s", patient_reply)
                await self._speak(patient_reply)

                if self.simulator.state.should_end():
                    await asyncio.sleep(1.5)
                    await self._hangup()
            finally:
                self._responding = False

    async def _send_dtmf(self, digit: str) -> None:
        """Send keypad tone so the agent IVR can detect language selection."""
        if not self.ws or not self.stream_sid:
            return
        await self.ws.send_json(
            {
                "event": "dtmf",
                "streamSid": self.stream_sid,
                "dtmf": {"digit": digit},
            }
        )
        logger.info("Sent DTMF digit: %s", digit)
        await asyncio.sleep(0.8)

    async def _speak(self, text: str, skip_dtmf: bool = False) -> None:
        if not self.ws or not self.stream_sid:
            return

        language = self.simulator.speech_language(text)

        if not skip_dtmf and self.simulator.needs_dtmf(text) and not self._dtmf_sent:
            await self._send_dtmf(self.simulator.scenario.dtmf_digit)
            self._dtmf_sent = True

        mulaw = await synthesize_speech(text, language=language)
        for frame in chunk_audio(mulaw):
            payload = encode_twilio_payload(frame)
            await self.ws.send_json(
                {
                    "event": "media",
                    "streamSid": self.stream_sid,
                    "media": {"payload": payload},
                }
            )
            await asyncio.sleep(0.02)

    async def _greet_timeout(self) -> None:
        """If agent is silent, patient speaks first after brief wait."""
        await asyncio.sleep(4.0)
        async with self._response_lock:
            if self.simulator.state.patient_turn_count > 0:
                return
            opening = self.simulator.opening_line()
            logger.info("Patient says (timeout): %s", opening)
            await self._speak(opening)

    async def send_opening(self) -> None:
        if self._opened_sent:
            return
        self._opened_sent = True
        if self.simulator.scenario.primary_language == "es":
            self._greet_timeout_task = asyncio.create_task(self._spanish_opening_sequence())
            return
        self._greet_timeout_task = asyncio.create_task(self._greet_timeout())

    async def _spanish_opening_sequence(self) -> None:
        """Wait for IVR, press Spanish keypad option, then speak opening in Spanish."""
        await asyncio.sleep(5.0)
        async with self._response_lock:
            if self.simulator.state.patient_turn_count > 0:
                return
            digit = self.simulator.scenario.dtmf_digit
            await self._send_dtmf(digit)
            self._dtmf_sent = True
            await asyncio.sleep(1.2)
            opening = self.simulator.opening_line()
            logger.info("Patient says (Spanish opening): %s", opening)
            await self._speak(opening, skip_dtmf=True)

    async def handle_media(self, payload: str) -> None:
        if self.stt and self.stt._ws:
            audio = decode_twilio_payload(payload)
            await self.stt.send_audio(audio)

    async def _hangup(self) -> None:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        try:
            client.calls(self.call_sid).update(status="completed")
        except Exception as e:
            logger.warning("Failed to hang up call %s: %s", self.call_sid, e)

    async def cleanup(self) -> None:
        from pathlib import Path

        from src.analysis.post_call import save_transcript

        text = self.simulator.state.transcript_text()
        json_turns = self.simulator.state.transcript_json()
        if text.strip():
            completed_transcripts[self.call_sid] = (text, json_turns)
            save_transcript(
                f"call-{self.call_sid}",
                text,
                {
                    "call_sid": self.call_sid,
                    "scenario_id": self.simulator.scenario.id,
                    "turns": json_turns,
                },
            )
        if self.stt:
            await self.stt.close()


def create_outbound_call(scenario_id: str, callback_url: str) -> str:
    """Place outbound call; returns call_sid."""
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    twiml_url = f"{callback_url.rstrip('/')}/voice/outbound?scenario={scenario_id}"
    status_url = f"{callback_url.rstrip('/')}/voice/status"

    call = client.calls.create(
        to=settings.target_phone_number,
        from_=settings.twilio_phone_number,
        url=twiml_url,
        status_callback=status_url,
        status_callback_event=["completed"],
        record=True,
        recording_channels="dual",
        method="POST",
    )
    return call.sid


async def handle_twilio_stream(ws: WebSocket, call_sid: str) -> None:
    session = active_sessions.get(call_sid)
    if not session:
        await ws.close(code=1008)
        return

    await session.attach_websocket(ws)
    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            event = data.get("event")

            if event == "start":
                session.stream_sid = data["start"]["streamSid"]
                asyncio.create_task(session.send_opening())
            elif event == "media":
                payload = data["media"]["payload"]
                await session.handle_media(payload)
            elif event == "stop":
                break
    except WebSocketDisconnect:
        pass
    finally:
        await session.cleanup()
        active_sessions.pop(call_sid, None)
