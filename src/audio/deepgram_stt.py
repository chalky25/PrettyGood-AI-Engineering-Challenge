from __future__ import annotations

import asyncio
import json
import ssl
from typing import Callable, Optional

import certifi
import websockets
from websockets.asyncio.client import connect

from src.config import settings


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


class DeepgramSTTStream:
    """Real-time speech-to-text for Twilio inbound (agent) audio."""

    def __init__(
        self,
        on_transcript: Callable[[str, bool], None],
        language: str = "en",
    ):
        self.on_transcript = on_transcript
        self.language = language
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._task: Optional[asyncio.Task] = None
        self._buffer = ""

    def _model_for_language(self) -> str:
        if self.language == "es":
            return settings.deepgram_stt_model_es
        return settings.deepgram_stt_model

    async def connect(self) -> None:
        url = (
            "wss://api.deepgram.com/v1/listen"
            f"?model={self._model_for_language()}"
            f"&language={self.language}"
            "&encoding=mulaw"
            "&sample_rate=8000"
            "&channels=1"
            "&punctuate=true"
            "&interim_results=true"
            "&endpointing=300"
            f"&endpointing_ms={settings.endpointing_ms}"
        )
        self._ws = await connect(
            url,
            additional_headers={"Authorization": f"Token {settings.deepgram_api_key}"},
            ssl=_ssl_context(),
        )
        self._task = asyncio.create_task(self._receive_loop())

    async def _receive_loop(self) -> None:
        assert self._ws is not None
        try:
            async for message in self._ws:
                data = json.loads(message)
                channel = data.get("channel", {})
                alternatives = channel.get("alternatives", [])
                if not alternatives:
                    continue
                transcript = alternatives[0].get("transcript", "").strip()
                if not transcript:
                    continue
                is_final = data.get("is_final", False)
                speech_final = data.get("speech_final", False)
                if is_final:
                    self._buffer = (self._buffer + " " + transcript).strip()
                if speech_final and self._buffer:
                    final_text = self._buffer
                    self._buffer = ""
                    self.on_transcript(final_text, True)
                elif is_final and transcript:
                    self.on_transcript(transcript, False)
        except websockets.exceptions.ConnectionClosed:
            pass

    async def send_audio(self, mulaw_chunk: bytes) -> None:
        ws = self._ws
        if not ws:
            return
        try:
            await ws.send(mulaw_chunk)
        except Exception:
            pass

    async def close(self) -> None:
        if self._ws:
            try:
                await self._ws.send(json.dumps({"type": "CloseStream"}))
            except Exception:
                pass
            await self._ws.close()
            self._ws = None
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._buffer = ""

    async def set_language(self, language: str) -> None:
        """Reconnect with a different Deepgram language model."""
        if language == self.language and self._ws is not None:
            return
        self.language = language
        await self.close()
        await self.connect()
