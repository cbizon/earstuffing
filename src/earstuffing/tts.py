"""Text-to-speech through Azure OpenAI, stitched together with ffmpeg."""

import re
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 4


def chunk_text(text: str, max_chars: int) -> list[str]:
    """Pack paragraphs into chunks under max_chars, splitting long paragraphs by sentence."""
    pieces = []
    for para in (p.strip() for p in re.split(r"\n\s*\n", text)):
        if not para:
            continue
        if len(para) <= max_chars:
            pieces.append(para)
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", para):
            if len(sentence) > max_chars:
                raise ValueError(f"Sentence longer than {max_chars} chars: {sentence[:80]}...")
            pieces.append(sentence)

    chunks, current = [], ""
    for piece in pieces:
        joined = f"{current}\n\n{piece}" if current else piece
        if len(joined) <= max_chars:
            current = joined
        else:
            chunks.append(current)
            current = piece
    if current:
        chunks.append(current)
    return chunks


def synthesize_chunk(client: httpx.Client, tts: dict, text: str) -> bytes:
    payload = {
        "model": tts["deployment"],
        "voice": tts["voice"],
        "input": text,
        "instructions": tts["instructions"],
        "response_format": "mp3",
    }
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = client.post(f"{tts['endpoint']}/audio/speech", json=payload)
        if response.status_code not in RETRY_STATUSES or attempt == MAX_ATTEMPTS:
            break
        time.sleep(int(response.headers.get("retry-after", 2**attempt)))
    if response.status_code != 200:
        raise RuntimeError(f"TTS failed ({response.status_code}): {response.text[:500]}")
    return response.content


def concat_mp3(parts: list[Path], out: Path, bitrate: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for p in parts:
            f.write(f"file '{p}'\n")
        listing = f.name
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
             "-i", listing, "-ac", "1", "-b:a", bitrate, str(out)],
            check=True,
        )
    finally:
        Path(listing).unlink()


def duration_seconds(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def render(text: str, out: Path, tts: dict, api_key: str, workers: int = 4) -> float:
    """Render text to an MP3 at out. Returns the duration in seconds."""
    chunks = chunk_text(text, tts["max_chunk_chars"])
    with httpx.Client(headers={"api-key": api_key}, timeout=300) as client:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            audio = list(pool.map(lambda c: synthesize_chunk(client, tts, c), chunks))
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for i, data in enumerate(audio):
            part = Path(tmp) / f"{i:03d}.mp3"
            part.write_bytes(data)
            parts.append(part)
        concat_mp3(parts, out, tts["bitrate"])
    return duration_seconds(out)
