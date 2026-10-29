"""Paperpile BibTeX export, PDF lookup, and on-disk episode records."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import bibtexparser
import httpx
import trafilatura

META = "meta.json"
SCRIPT = "script.md"
SUMMARY = "summary.txt"
NOTES = "notes.md"
DISCUSSION = "discussion.md"
PAGE = "page.md"
# Characters Obsidian does not allow in note names.
UNSAFE_NAME = re.compile(r'[*"\\/<>:|?#^\[\]]')
# Paperpile puts a website's address in howpublished as \url{...}.
HOWPUBLISHED_URL = re.compile(r"\\url\{([^}]+)\}")


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
        howpublished = HOWPUBLISHED_URL.search(
            next((f.value for k, f in e.fields_dict.items() if k.lower() == "howpublished"), "")
        )
        entries.append(
            {
                "key": e.key,
                "slug": slugify(e.key),
                "type": e.entry_type.lower(),
                "title": fields.get("title", ""),
                "authors": _authors(e.fields_dict["author"].value) if "author" in fields else [],
                "year": fields.get("year", ""),
                "venue": fields.get("journal") or fields.get("booktitle") or "",
                "doi": fields.get("doi", ""),
                "url": fields.get("url") or (howpublished.group(1) if howpublished else ""),
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


def is_website(entry: dict) -> bool:
    """Paperpile exports its Website type as @MISC with the address in howpublished."""
    return entry["type"] == "misc" and bool(entry["url"])


def fetch_page(url: str) -> str:
    """Download a web page and return its main text as Markdown, headed by its source."""
    response = httpx.get(url, follow_redirects=True, timeout=30)
    response.raise_for_status()
    text = trafilatura.extract(response.text, url=url, output_format="markdown", include_tables=True)
    if not text:
        raise ValueError(f"No readable text extracted from {url}")
    retrieved = datetime.now(timezone.utc).date().isoformat()
    return f"Source: <{url}>\nRetrieved: {retrieved}\n\n{text.strip()}\n"


def save_page(data_dir: Path, slug: str, text: str) -> Path:
    path = episode_dir(data_dir, slug) / PAGE
    path.write_text(text)
    return path


def episode_dir(data_dir: Path, slug: str) -> Path:
    return data_dir / "episodes" / slug


def episode_status(data_dir: Path, slug: str) -> str:
    d = episode_dir(data_dir, slug)
    if not (d / META).exists():
        return "new"
    if not (d / SCRIPT).exists() or not (d / SUMMARY).exists():
        return "needs_script"
    if "rendered_at" not in read_meta(data_dir, slug):
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
    """Metadata for every rendered episode, newest first.

    Audio is transient: it lives in the cache only until it is uploaded, so whether an
    episode is rendered comes from meta.json, not from a local file.
    """
    metas = [m for m in all_metas(data_dir) if "rendered_at" in m]
    return sorted(metas, key=lambda m: m["rendered_at"], reverse=True)


def cached_audio(audio_cache: Path, slug: str) -> Path:
    """Where rendered audio waits until publish uploads it."""
    return audio_cache / f"{slug}.mp3"


def hub_name(meta: dict) -> str:
    title = UNSAFE_NAME.sub(" ", meta["title"])
    title = re.sub(r"\s+", " ", title).strip()
    if len(title) > 150:
        title = title[:150].rsplit(" ", 1)[0]
    return f"Paper {meta['number']} - {title}"


def write_hub(data_dir: Path, slug: str) -> Path:
    """Write the paper's Obsidian hub note, which embeds its script, notes and discussion.

    The hub is generated and overwritten; anything worth keeping goes in discussion.md.
    """
    meta = read_meta(data_dir, slug)
    d = episode_dir(data_dir, slug)
    name = hub_name(meta)
    for stale in d.glob(f"Paper {meta['number']} - *.md"):
        if stale.stem != name:
            stale.unlink()
    rel = f"episodes/{slug}"
    props = {
        "number": meta["number"],
        "title": meta["title"],
        "authors": meta.get("authors", []),
        "year": meta.get("year", ""),
        "venue": meta.get("venue", ""),
        "doi": meta.get("doi", ""),
        "url": meta.get("url", ""),
        "aliases": [f"Paper {meta['number']}"],
        "tags": ["paper"],
    }
    lines = ["---"]
    for key, value in props.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines += [f"  - {json.dumps(v)}" for v in value]
        else:
            lines.append(f"{key}: {json.dumps(value)}")
    lines += ["---", "%% Generated by earstuffing and overwritten; write in discussion.md. %%", ""]
    byline = ", ".join(meta.get("authors", []))
    lines += [f"# Paper {meta['number']}: {meta['title']}", "", byline, ""]
    if meta.get("pdf"):
        lines += [f"[PDF](<{Path(meta['pdf']).as_uri()}>)", ""]
    elif (d / PAGE).exists():
        lines += [f"[Web page](<{meta['url']}>) · [[{rel}/{PAGE}|Saved copy]]", ""]
    summary = meta.get("summary") or ((d / SUMMARY).read_text().strip() if (d / SUMMARY).exists() else "")
    if summary:
        lines += [summary, ""]
    if (d / SCRIPT).exists():
        lines += ["> [!quote]- Script", f"> ![[{rel}/{SCRIPT}]]", ""]
    for heading, filename in (("Voice notes", NOTES), ("Discussion", DISCUSSION)):
        if (d / filename).exists():
            lines += [f"## {heading}", "", f"![[{rel}/{filename}]]", ""]
    path = d / f"{name}.md"
    path.write_text("\n".join(lines))
    return path
