"""Paperpile BibTeX export, PDF lookup, and on-disk episode records."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import bibtexparser

META = "meta.json"
SCRIPT = "script.txt"
SUMMARY = "summary.txt"
AUDIO = "episode.mp3"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not slug:
        raise ValueError(f"Cannot make a slug from {text!r}")
    return slug


def normalize_title(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("{", "").replace("}", "")).strip()


def _authors(value: str) -> list[str]:
    names = []
    for name in re.split(r"\s+and\s+", _clean(value)):
        if "," in name:
            last, first = (part.strip() for part in name.split(",", 1))
            name = f"{first} {last}".strip()
        names.append(name)
    return names


def read_bib(bib_file: Path) -> list[dict]:
    """Parse the BibTeX export into simple entry dicts."""
    library = bibtexparser.parse_string(bib_file.read_text(encoding="utf-8"))
    if library.failed_blocks:
        raise ValueError(f"{len(library.failed_blocks)} unparseable blocks in {bib_file}")
    entries = []
    for e in library.entries:
        fields = {k.lower(): _clean(f.value) for k, f in e.fields_dict.items()}
        entries.append(
            {
                "key": e.key,
                "slug": slugify(e.key),
                "title": fields.get("title", ""),
                "authors": _authors(e.fields_dict["author"].value) if "author" in fields else [],
                "year": fields.get("year", ""),
                "venue": fields.get("journal") or fields.get("booktitle") or "",
                "doi": fields.get("doi", ""),
                "url": fields.get("url", ""),
                "eprint": fields.get("eprint", ""),
                "file": fields.get("file", ""),
            }
        )
    return entries


def index_pdfs(paperpile_dir: Path) -> list[Path]:
    return sorted((paperpile_dir / "All Papers").rglob("*.pdf"))


def find_pdf(entry: dict, paperpile_dir: Path, pdfs: list[Path]) -> Path | None:
    """Locate an entry's PDF, preferring the BibTeX file field over title matching."""
    for raw in filter(None, (p.strip() for p in entry["file"].split(";"))):
        raw = raw.strip(":").removesuffix(":application/pdf").removesuffix(":PDF")
        for base in (paperpile_dir, paperpile_dir.parent):
            candidate = base / raw
            if candidate.is_file():
                return candidate

    want = normalize_title(entry["title"])
    if not want:
        return None
    for pdf in pdfs:
        _, sep, file_title = pdf.stem.partition(" - ")
        if not sep:
            continue
        # Paperpile elides the middle of long titles: "start ... end".
        head, ellipsis, tail = file_title.partition(" ... ")
        if ellipsis:
            head, tail = normalize_title(head), normalize_title(tail)
            if len(head) + len(tail) >= 30 and want.startswith(head) and want.endswith(tail):
                return pdf
            continue
        have = normalize_title(file_title)
        if have == want or (len(have) >= 30 and want.startswith(have)):
            return pdf
    return None


def episode_dir(data_dir: Path, slug: str) -> Path:
    return data_dir / "episodes" / slug


def episode_status(data_dir: Path, slug: str) -> str:
    d = episode_dir(data_dir, slug)
    if not (d / META).exists():
        return "new"
    if not (d / SCRIPT).exists() or not (d / SUMMARY).exists():
        return "needs_script"
    if not (d / AUDIO).exists():
        return "needs_audio"
    return "rendered"


def all_metas(data_dir: Path) -> list[dict]:
    root = data_dir / "episodes"
    if not root.exists():
        return []
    return [json.loads((d / META).read_text()) for d in root.iterdir() if (d / META).exists()]


def next_number(data_dir: Path) -> int:
    """Episodes get short sequential numbers so voice notes can refer to them."""
    return max((m["number"] for m in all_metas(data_dir)), default=0) + 1


def create_episode(data_dir: Path, meta: dict) -> Path:
    """Write meta.json for a new episode and return its directory."""
    d = episode_dir(data_dir, meta["slug"])
    if (d / META).exists():
        raise FileExistsError(f"Episode {meta['slug']} already exists at {d}")
    number = next_number(data_dir)
    d.mkdir(parents=True)
    meta = {**meta, "number": number, "created_at": datetime.now(timezone.utc).isoformat()}
    (d / META).write_text(json.dumps(meta, indent=2, default=str) + "\n")
    return d


def read_meta(data_dir: Path, slug: str) -> dict:
    return json.loads((episode_dir(data_dir, slug) / META).read_text())


def update_meta(data_dir: Path, slug: str, **fields) -> dict:
    meta = read_meta(data_dir, slug) | fields
    (episode_dir(data_dir, slug) / META).write_text(json.dumps(meta, indent=2, default=str) + "\n")
    return meta


def rendered_episodes(data_dir: Path) -> list[dict]:
    """Metadata for every episode with audio, newest first."""
    metas = [m for m in all_metas(data_dir) if (episode_dir(data_dir, m["slug"]) / AUDIO).exists()]
    for m in metas:
        if "rendered_at" not in m:
            raise ValueError(f"Episode {m['slug']} has audio but no rendered_at; re-render it")
    return sorted(metas, key=lambda m: m["rendered_at"], reverse=True)
