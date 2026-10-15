"""What changed since the user last reviewed: new discussion replies and new episodes.

discussion.md files are append-only in normal use, so "seen" is stored as the byte
length of each file at the last review. A file that shrank was edited by hand and is
shown in full.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from earstuffing import library

STATE = "inbox.json"


def _state_path(data_dir: Path) -> Path:
    return data_dir / STATE


def load_state(data_dir: Path) -> dict:
    path = _state_path(data_dir)
    return json.loads(path.read_text()) if path.exists() else {"reviewed_at": None, "seen_bytes": {}}


def collect(data_dir: Path) -> list[dict]:
    """Papers with discussion added or an episode published since the last review."""
    state = load_state(data_dir)
    reviewed_at, seen = state["reviewed_at"], state["seen_bytes"]
    items = []
    for meta in sorted(library.all_metas(data_dir), key=lambda m: m["number"]):
        slug = meta["slug"]
        discussion = library.episode_dir(data_dir, slug) / library.DISCUSSION
        new_text, edited = "", False
        if discussion.exists():
            data = discussion.read_bytes()
            offset = seen.get(slug, 0)
            if len(data) < offset:
                offset, edited = 0, True
            new_text = data[offset:].decode("utf-8").strip()
        rendered = meta.get("rendered_at")
        new_episode = bool(rendered) and (reviewed_at is None or rendered > reviewed_at)
        if new_text or new_episode:
            items.append({
                "number": meta["number"],
                "slug": slug,
                "title": meta["title"],
                "new_episode": new_episode,
                "discussion_edited": edited,
                "new_discussion": new_text,
                "discussion_file": str(discussion) if discussion.exists() else None,
            })
    return items


def mark_reviewed(data_dir: Path) -> dict:
    """Record everything as seen now."""
    seen = {}
    for meta in library.all_metas(data_dir):
        discussion = library.episode_dir(data_dir, meta["slug"]) / library.DISCUSSION
        if discussion.exists():
            seen[meta["slug"]] = discussion.stat().st_size
    state = {"reviewed_at": datetime.now(timezone.utc).isoformat(), "seen_bytes": seen}
    _state_path(data_dir).write_text(json.dumps(state, indent=2) + "\n")
    return state
