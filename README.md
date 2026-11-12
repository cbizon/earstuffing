# earstuffing

Turns research papers into narrated audio explanations and publishes them as a
private podcast feed, so papers can be listened to in the car. Voice notes
recorded while listening come back as text, filed under the paper they are
about, and are answered in writing.

This is a personal tool. It assumes macOS, Paperpile, Azure OpenAI, Cloudflare
R2 and Claude Code, and is not packaged for general use.

## How it works

1. **Papers.** Papers tagged with the Paperpile "Listen" label are auto-exported
   as BibTeX to Google Drive. Web pages saved to Paperpile work too.
2. **Scripts.** Claude Code reads each paper and writes a spoken-word script and
   a short summary, following [SCRIPT_GUIDE.md](SCRIPT_GUIDE.md).
3. **Audio.** The script is rendered with Azure OpenAI `gpt-4o-mini-tts` in
   chunks and joined with ffmpeg.
4. **Feed.** Audio is uploaded to a Cloudflare R2 bucket along with an RSS feed,
   under a random path prefix. Any podcast app can subscribe to it.
5. **Voice notes.** An Android Auto app ([android/](android/)) records short
   notes in the car and uploads them to a second, private R2 bucket. The CLI
   transcribes each note and files it under the paper that was playing, or the
   one named at the start of the note ("for paper twelve, ...").
6. **Discussion.** Claude Code answers each note in writing from the paper.
   Episodes, notes and discussions live in an Obsidian vault.

The Python CLI does the mechanical work. Claude Code does the reading and
writing, driven by the runbooks in [CLAUDE.md](CLAUDE.md).

## Commands

Run with `uv run earstuffing <command>`. Each prints JSON.

| Command | What it does |
| --- | --- |
| `pending` | List Listen papers without rendered audio, with status and PDF path |
| `prepare <bibkey>` | Create the episode record; for a website entry, also save the page |
| `prepare --pdf <file> --title <title>` | Create an episode for a PDF that is not in Paperpile |
| `page <slug>` | Save an existing episode's web page as `page.md` |
| `render <slug>` | Render the episode's `script.md` to audio |
| `publish` | Upload new audio and rewrite the feed |
| `notes` | Fetch, transcribe and file new voice notes |
| `hubs` | Regenerate every paper's Obsidian hub note |
| `inbox` | Show discussion replies and episodes added since the last review (`--mark` records them as reviewed) |

Every command first fetches `origin/main` and refuses to run if the checkout is
behind it, so stale code never runs against current data.

In Claude Code, `/paper N` opens a paper for discussion and `/inbox` reviews
what is new.

## Setup

Requires macOS (secrets are read from the keychain), [uv](https://docs.astral.sh/uv/),
ffmpeg and git.

1. `uv sync`
2. Create `earstuffing.local.toml` next to `earstuffing.toml`. It is gitignored
   and overrides the shared defaults. Set the values that are empty in
   `earstuffing.toml`:

   ```toml
   [paths]
   paperpile_dir = "~/Library/CloudStorage/GoogleDrive-<account>/My Drive/Paperpile"
   bib_file = "<path to the Listen label's BibTeX export>"

   [tts]
   endpoint = "https://<resource>.openai.azure.com/openai/v1"
   keychain_account = "<account name on the azure-openai keychain item>"

   [r2]
   account_id = "<Cloudflare account id>"
   public_url = "https://pub-xxxx.r2.dev"
   prefix = "<random string, so the feed URL is not guessable>"
   ```

3. Add the secrets to the macOS keychain:
   - `azure-openai`: the Azure OpenAI API key.
   - `earstuffing-r2`: account = R2 access key ID, password = R2 secret.
4. Make `data/` a directory or a symlink to a synced folder. It holds the
   episode records and is gitignored.

The Azure resource needs a `gpt-4o-mini-tts` deployment, and a
`gpt-4o-transcribe` deployment for voice notes. R2 needs a public bucket for the
feed (`earstuffing`) and a private one for notes (`earstuffing-notes`).

## Data layout

`data/` is an Obsidian vault. Audio is not kept in it: rendered files wait in a
local cache and are deleted once uploaded, and voice recordings are deleted from
the notes bucket once transcribed.

```
data/
  episodes/<slug>/
    meta.json         title, authors, number, duration, ...
    script.md         what the listener hears
    summary.txt       feed description
    page.md           saved page text, for website entries
    notes.md          transcribed voice notes
    discussion.md     replies and conclusions
    Paper N - <title>.md   generated hub note; do not edit
  topics/<Topic>.md   cross-paper ideas
  projects/<Name>.md  the user's own projects
  notes/unmatched.md  notes that could not be matched to a paper
```

## Android app

`android/` is a small Android Auto app that records a voice note, captures what
the podcast player is showing, and uploads both to the notes bucket using R2
credentials entered on the phone. Android Auto only shows apps installed from
Google Play, so it ships through a Play Console internal testing track; the
release steps are in [CLAUDE.md](CLAUDE.md). See also the
[privacy policy](android/PRIVACY.md).

## Tests

```
uv run pytest                  # unit tests
uv run pytest -m integration   # calls real Azure TTS
```

## What is not in this repository

By design, the repository holds code and documentation only:

- `data/` (episodes, scripts, notes, discussions) lives in Google Drive.
- `earstuffing.local.toml` (paths, endpoints, feed URL and prefix) is local.
- API keys and the Android upload key password are in the macOS keychain; the
  keystore itself is outside the repository.
- Audio lives only in R2.
