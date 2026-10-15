"""Turn papers into narrated audio explanations published as a private podcast feed."""

import argparse
import json
import sys
from datetime import datetime, timezone

from earstuffing import library, tts
from earstuffing.config import PROJECT_ROOT, keychain_secret, load_config, require_current


def cmd_pending(config: dict, args) -> None:
    paths = config["paths"]
    entries = library.read_bib(paths["bib_file"])
    pdfs = library.index_pdfs(paths["paperpile_dir"])
    out = []
    for e in entries:
        status = library.episode_status(paths["data_dir"], e["slug"])
        if status == "rendered":
            continue
        pdf = library.find_pdf(e, paths["paperpile_dir"], pdfs)
        out.append({**e, "status": status, "pdf": str(pdf) if pdf else None})
    print(json.dumps(out, indent=2))


def cmd_prepare(config: dict, args) -> None:
    paths = config["paths"]
    if args.key:
        matches = [e for e in library.read_bib(paths["bib_file"]) if e["key"] == args.key]
        if not matches:
            sys.exit(f"No entry {args.key!r} in {paths['bib_file']}")
        entry = matches[0]
        pdf = library.find_pdf(entry, paths["paperpile_dir"], library.index_pdfs(paths["paperpile_dir"]))
        meta = {k: entry[k] for k in ("key", "slug", "title", "authors", "year", "venue", "doi", "url")}
    else:
        if not (args.pdf and args.title):
            sys.exit("Without a bib key, --pdf and --title are required")
        pdf = args.pdf
        meta = {
            "key": None,
            "slug": library.slugify(args.slug or f"{args.title[:60]}"),
            "title": args.title,
            "authors": [a.strip() for a in (args.authors or "").split(";") if a.strip()],
            "year": args.year or "",
            "venue": args.venue or "",
            "doi": args.doi or "",
            "url": args.url or "",
        }
    meta["pdf"] = str(pdf) if pdf else None
    d = library.create_episode(paths["data_dir"], meta)
    library.write_hub(paths["data_dir"], meta["slug"])
    print(json.dumps({"episode_dir": str(d), **meta}, indent=2))


def cmd_render(config: dict, args) -> None:
    data_dir, audio_cache = config["paths"]["data_dir"], config["paths"]["audio_cache"]
    d = library.episode_dir(data_dir, args.slug)
    script = (d / library.SCRIPT).read_text().strip()
    summary = (d / library.SUMMARY).read_text().strip()
    if not script or not summary:
        sys.exit(f"{d} has an empty script or summary")
    number = library.read_meta(data_dir, args.slug)["number"]
    spoken = f"Paper {number}.\n\n{script}\n\nThat was paper {number}."
    audio_cache.mkdir(parents=True, exist_ok=True)
    out = library.cached_audio(audio_cache, args.slug)
    api_key = keychain_secret(config["tts"]["keychain_service"], config["tts"]["keychain_account"])
    duration = tts.render(spoken, out, config["tts"], api_key)
    meta = library.update_meta(
        data_dir,
        args.slug,
        summary=summary,
        duration=duration,
        audio_bytes=out.stat().st_size,
        rendered_at=datetime.now(timezone.utc).isoformat(),
        script_words=len(script.split()),
    )
    library.write_hub(data_dir, args.slug)
    print(json.dumps({"audio": str(out), "minutes": round(duration / 60, 1), "words": meta["script_words"]}))


def cmd_publish(config: dict, args) -> None:
    from earstuffing.publish import publish

    uploaded, feed_url = publish(config)
    print(json.dumps({"uploaded": uploaded, "feed": feed_url}, indent=2))


def cmd_hubs(config: dict, args) -> None:
    data_dir = config["paths"]["data_dir"]
    print(json.dumps([str(library.write_hub(data_dir, m["slug"])) for m in library.all_metas(data_dir)], indent=2))


def cmd_notes(config: dict, args) -> None:
    from earstuffing.notes import fetch_and_file
    from earstuffing.publish import r2_client

    client = r2_client(config["r2"])
    api_key = keychain_secret(config["tts"]["keychain_service"], config["tts"]["keychain_account"])
    print(json.dumps(fetch_and_file(config, client, api_key), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="earstuffing")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("pending", help="List Listen-label papers without rendered audio")

    p = sub.add_parser("prepare", help="Create an episode record from a bib key or a PDF")
    p.add_argument("key", nargs="?", help="BibTeX key from the Paperpile export")
    p.add_argument("--pdf")
    p.add_argument("--title")
    p.add_argument("--authors", help="Semicolon-separated")
    p.add_argument("--year")
    p.add_argument("--venue")
    p.add_argument("--doi")
    p.add_argument("--url")
    p.add_argument("--slug")

    r = sub.add_parser("render", help="Render an episode's script.md to audio")
    r.add_argument("slug")

    sub.add_parser("publish", help="Upload new audio and rewrite the feed on R2")

    sub.add_parser("notes", help="Fetch, transcribe and file new voice notes")

    sub.add_parser("hubs", help="Regenerate every paper's Obsidian hub note")

    args = parser.parse_args()
    require_current(PROJECT_ROOT)
    config = load_config()
    {
        "pending": cmd_pending, "prepare": cmd_prepare, "render": cmd_render,
        "publish": cmd_publish, "notes": cmd_notes, "hubs": cmd_hubs,
    }[
        args.command
    ](config, args)
