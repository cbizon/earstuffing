# earstuffing

Turns research papers into narrated audio explanations published as a private
podcast feed on Cloudflare R2. Papers come from the Paperpile "Listen" label,
whose BibTeX auto-export syncs to Google Drive. Claude (this session, on the
user's subscription) reads each paper and writes the script; the Python CLI does
everything else.

- Config: `earstuffing.toml` holds shared defaults; machine-specific values
  (Drive paths, Azure endpoint, R2 account, public URL, feed prefix) go in the
  gitignored `earstuffing.local.toml`. Secrets are in the macOS keychain
  (`azure-openai`, `earstuffing-r2`), never in files. This repo is public: never
  commit the feed URL, prefix, or personal paths.
- Episode data: `data/episodes/<slug>/` (gitignored) holding `meta.json`,
  `script.txt`, `summary.txt`, `episode.mp3`.
- Tests: `uv run pytest` (unit), `uv run pytest -m integration` (real Azure TTS).

## Runbook: process new papers

1. `uv run earstuffing pending` lists Listen papers without audio, with each
   one's `status` and local `pdf` path.
2. For each entry:
   - `status: new` → `uv run earstuffing prepare <key>`.
   - If `pdf` is null, try to get an open-access copy (arXiv, bioRxiv, PMC, or
     the DOI landing page) into `data/episodes/<slug>/paper.pdf` and set `pdf` in
     `meta.json`. If none is available, skip it and report it.
   - `needs_script` → read the whole PDF, then write `script.txt` and
     `summary.txt` following `SCRIPT_GUIDE.md` exactly.
   - `uv run earstuffing render <slug>`.
3. `uv run earstuffing publish` uploads new audio and rewrites the feed.
4. Report: papers processed (title, minutes), papers skipped and why, and any
   errors. Do not hide failures; if a step fails, stop that paper and report the
   error verbatim.

Never process manuscripts under confidential peer review.
