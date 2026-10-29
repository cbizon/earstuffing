---
name: inbox
description: Show what's new in earstuffing since the last review (replies to voice notes, new episodes) and discuss those papers in one conversation.
---

Review what's new across earstuffing papers.

1. Run `uv run earstuffing inbox`. It returns, per paper, `new_discussion` (text appended to `discussion.md` since the last review), `new_episode`, and `discussion_edited` (the file was changed by hand, so the whole file is shown). If the list is empty, say there is nothing new and stop.
2. For each paper listed, read its `meta.json`, the PDF at its `pdf` path (Read in page ranges of at most 20 pages) or `page.md` for a website entry with no PDF, `script.md`, `notes.md` and `discussion.md`, so you can discuss it properly. Use the Read tool, not shell commands.
3. Present a short digest, newest-numbered paper last:
   - `Paper N: <title>` as a heading.
   - For new episodes, one sentence on the paper.
   - For new discussion, each note answered: a one-line summary of what the note said or asked (not its first sentence, which is often a preamble), then the reply in two or three sentences. Point to `discussion.md` for the full text rather than repeating it.
   - Flag anything a reply left open or asked the user about.
4. Run `uv run earstuffing inbox --mark` so these items are not shown again.
5. Then discuss as `/paper` does: as a colleague who has read the papers closely, answering from the papers, saying where they are silent, and pushing back where the user or a reply got something wrong. When a point is settled, append it to that paper's `discussion.md` under `## <date>: <topic>`, linking topics as `CLAUDE.md` describes, and say what you recorded.
