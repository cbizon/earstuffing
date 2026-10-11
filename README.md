# earstuffing

Turns research papers into narrated audio explanations and publishes them as a
private podcast feed.

- Papers: Paperpile "Listen" label, exported as BibTeX to Google Drive.
- Scripts: written by Claude Code following `SCRIPT_GUIDE.md` (runbook in `CLAUDE.md`).
- Audio: Azure OpenAI `gpt-4o-mini-tts`, joined with ffmpeg.
- Hosting: Cloudflare R2, served as an RSS feed.

```
uv run earstuffing pending
uv run earstuffing prepare <bibkey>
uv run earstuffing render <slug>
uv run earstuffing publish
```
