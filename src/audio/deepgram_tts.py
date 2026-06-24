from __future__ import annotations

import httpx

from src.audio.mulaw import linear_to_mulaw, resample_pcm
from src.config import settings


async def synthesize_speech(text: str, language: str = "en") -> bytes:
    """Return 8kHz mu-law audio suitable for Twilio Media Streams."""
    voice = settings.deepgram_tts_voice_es if language == "es" else settings.deepgram_tts_voice
    url = "https://api.deepgram.com/v1/speak"
    params = {
        "model": voice,
        "encoding": "linear16",
        "sample_rate": "8000",
        "container": "none",
    }
    headers = {
        "Authorization": f"Token {settings.deepgram_api_key}",
        "Content-Type": "application/json",
    }
    payload = {"text": text}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, params=params, headers=headers, json=payload)
        response.raise_for_status()
        pcm = response.content

    try:
        return linear_to_mulaw(pcm)
    except Exception:
        return linear_to_mulaw(resample_pcm(pcm, 24000, 8000))
