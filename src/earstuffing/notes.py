"""Voice notes: fetch from R2, transcribe, and file them under the paper they discuss.

The phone app uploads `<prefix><id>.wav` followed by `<prefix><id>.json`, a sidecar
with what Pocket Casts was playing. The sidecar is written last, so its presence
marks a complete upload.
"""

import json
import re
from datetime import datetime
from pathlib import Path

import httpx

from earstuffing import library

ONES = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen"
).split()
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
SPOKEN_PAPER = re.compile(r"^\W*paper\s+(?:number\s+)?([a-z0-9]+(?:[\s-][a-z]+)?)", re.IGNORECASE)
TITLE_NUMBER = re.compile(r"^\s*(\d+)\s*·")


def words_to_number(text: str) -> int | None:
    """Parse '14', 'fourteen' or 'twenty-one' (up to 99). Trailing words are ignored."""
    words = re.split(r"[\s-]+", text.strip().lower())
    if words[0].isdigit():
        return int(words[0])
    if words[0] in ONES:
        return ONES.index(words[0])
    if words[0] in TENS:
        tens = TENS[words[0]]
        if len(words) > 1 and words[1] in ONES[1:10]:
            return tens + ONES.index(words[1])
        return tens
    return None


def spoken_number(transcript: str) -> int | None:
    m = SPOKEN_PAPER.match(transcript)
    return words_to_number(m.group(1)) if m else None


def match_episode(sidecar: dict, transcript: str, metas: list[dict]) -> tuple[dict | None, str]:
    """Find the episode a note is about. A spoken "paper N" overrides what was playing."""
    by_number = {m["number"]: m for m in metas}
    n = spoken_number(transcript)
    if n is not None:
        return by_number.get(n), f"spoken paper {n}"
    title = sidecar.get("media_title") or ""
    m = TITLE_NUMBER.match(title)
    if m and int(m.group(1)) in by_number:
        return by_number[int(m.group(1))], "playing in Pocket Casts"
    want = library.normalize_title(title)
    for meta in metas:
        if want and library.normalize_title(meta["title"]) in want:
            return meta, "playing in Pocket Casts"
    return None, "no paper number and nothing recognizable playing"


def vocabulary_prompt(metas: list[dict], limit: int = 800) -> str:
    """Recent paper titles as transcription hints for technical vocabulary."""
    recent = sorted(metas, key=lambda m: m["number"], reverse=True)
    prompt = "Notes on research papers, often starting with 'Paper N'."
    for m in recent:
        addition = f" {m['title']}."
        if len(prompt) + len(addition) > limit:
            break
        prompt += addition
    return prompt


def transcribe(audio: Path, cfg: dict, endpoint: str, api_key: str, prompt: str) -> str:
    root = endpoint.removesuffix("/").removesuffix("/v1")
    url = f"{root}/deployments/{cfg['deployment']}/audio/transcriptions"
    with audio.open("rb") as f:
        response = httpx.post(
            url,
            params={"api-version": cfg["api_version"]},
            headers={"api-key": api_key},
            files={"file": (audio.name, f)},
            data={"prompt": prompt},
            timeout=300,
        )
    if response.status_code != 200:
        raise RuntimeError(f"Transcription failed ({response.status_code}): {response.text[:500]}")
    return response.json()["text"].strip()


def _clock(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


def note_entry(sidecar: dict, transcript: str, how: str) -> str:
    when = datetime.fromisoformat(sidecar["recorded_at"]).astimezone().strftime("%Y-%m-%d %H:%M")
    context = f"Matched by {how}."
    if sidecar.get("media_title") and sidecar.get("position_ms") is not None:
        context += f" Recorded {_clock(sidecar['position_ms'])} into \"{sidecar['media_title']}\"."
    return f"## Note {sidecar['id']} ({when})\n\n_{context}_\n\n{transcript}\n\n"


def file_note(data_dir: Path, meta: dict | None, entry: str) -> Path:
    path = (
        library.episode_dir(data_dir, meta["slug"]) / library.NOTES
        if meta
        else data_dir / "notes" / "unmatched.md"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(entry)
    return path


def processed_ids(data_dir: Path) -> set[str]:
    path = data_dir / "notes" / "processed.txt"
    return set(path.read_text().split()) if path.exists() else set()


def mark_processed(data_dir: Path, note_id: str) -> None:
    path = data_dir / "notes" / "processed.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(note_id + "\n")


def fetch_and_file(config: dict, client, api_key: str) -> list[dict]:
    """Process every complete, unprocessed note in the bucket. Returns a summary per note."""
    notes_cfg, data_dir = config["notes"], config["paths"]["data_dir"]
    done = processed_ids(data_dir)
    metas = library.all_metas(data_dir)
    prompt = vocabulary_prompt(metas)
    audio_dir = data_dir / "notes" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=notes_cfg["bucket"], Prefix=notes_cfg["prefix"]):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".json"):
                continue
            sidecar = json.loads(client.get_object(Bucket=notes_cfg["bucket"], Key=key)["Body"].read())
            if sidecar["id"] in done:
                continue
            audio_key = key.removesuffix(".json") + Path(sidecar["audio"]).suffix
            audio = audio_dir / Path(audio_key).name
            client.download_file(notes_cfg["bucket"], audio_key, str(audio))
            transcript = transcribe(audio, config["transcribe"], config["tts"]["endpoint"], api_key, prompt)
            meta, how = match_episode(sidecar, transcript, metas)
            path = file_note(data_dir, meta, note_entry(sidecar, transcript, how))
            mark_processed(data_dir, sidecar["id"])
            summary.append(
                {"id": sidecar["id"], "paper": meta["number"] if meta else None,
                 "slug": meta["slug"] if meta else None, "matched_by": how,
                 "file": str(path), "transcript": transcript}
            )
    return summary
