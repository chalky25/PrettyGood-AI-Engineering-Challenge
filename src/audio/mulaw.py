import audioop
import base64
from typing import Iterator


def mulaw_to_linear(mulaw_bytes: bytes) -> bytes:
    """Convert 8-bit mu-law to 16-bit linear PCM."""
    return audioop.ulaw2lin(mulaw_bytes, 2)


def linear_to_mulaw(pcm_bytes: bytes) -> bytes:
    """Convert 16-bit linear PCM to 8-bit mu-law."""
    return audioop.lin2ulaw(pcm_bytes, 2)


def chunk_audio(data: bytes, frame_size: int = 160) -> Iterator[bytes]:
    """Split audio into telephony frames (160 bytes = 20ms at 8kHz mu-law)."""
    for i in range(0, len(data), frame_size):
        chunk = data[i : i + frame_size]
        if chunk:
            yield chunk


def encode_twilio_payload(mulaw_bytes: bytes) -> str:
    return base64.b64encode(mulaw_bytes).decode("ascii")


def decode_twilio_payload(payload: str) -> bytes:
    return base64.b64decode(payload)


def resample_pcm(pcm_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
    if from_rate == to_rate:
        return pcm_bytes
    converted, _ = audioop.ratecv(pcm_bytes, 2, 1, from_rate, to_rate, None)
    return converted
