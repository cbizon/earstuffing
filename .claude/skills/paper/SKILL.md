---
name: paper
description: Open an earstuffing paper by episode number (e.g. /paper 14) to discuss it, with its PDF, script, voice notes and discussion so far loaded.
---

Open paper `$ARGUMENTS` for discussion.

1. Find the episode. `data/` is a gitignored symlink that exists only in the main checkout, not in worktrees, so resolve it through the main checkout: `DATA="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")/data"`, then `grep -lE '"number": $ARGUMENTS,?$' "$DATA"/episodes/*/meta.json`. Use that absolute episode path for every read and write below. If none matches, list the episodes (number and title from each `meta.json`) and ask which one.
2. Read, in full: `meta.json`, the PDF at its `pdf` path (Read in page ranges of at most 20 pages), or `page.md` in the episode folder for a website entry with no PDF, `script.md` (what the listener heard), and `notes.md` and `discussion.md` if they exist. Also read the topic notes in `$DATA/topics/` and project notes in `$DATA/projects/` that the discussion links.
3. Give a short orientation: the title, one sentence on the paper, and the open threads from the notes and discussion. Then wait for the user.
4. Discuss as a colleague who has read the paper closely: answer from the paper, say where it is silent or unclear, and push back where the user or the script got something wrong.
5. When the conversation reaches a conclusion worth keeping (an answer, a correction, a follow-up idea), append it to `discussion.md` under a `## <date>: <topic>` heading. Keep it brief, and only record what was actually discussed. Link the relevant topic notes with `[[Topic]]` and update each linked topic note's summary so it stays current; reuse existing topics, create new ones freely, and tell the user when you create one. Link the user's projects with `[[Project]]` too, as `CLAUDE.md` describes. If you created `discussion.md`, run `uv run earstuffing hubs`.
