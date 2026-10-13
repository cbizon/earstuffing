---
name: paper
description: Open an earstuffing paper by episode number (e.g. /paper 14) to discuss it, with its PDF, script, voice notes and discussion so far loaded.
---

Open paper `$ARGUMENTS` for discussion.

1. Find the episode: `grep -l '"number": $ARGUMENTS,' data/episodes/*/meta.json`. If none matches, list the episodes (number and title from each `meta.json`) and ask which one.
2. Read, in full: `meta.json`, the PDF at its `pdf` path (Read in page ranges of at most 20 pages), `script.txt` (what the listener heard), and `notes.md` and `discussion.md` if they exist.
3. Give a short orientation: the title, one sentence on the paper, and the open threads from the notes and discussion. Then wait for the user.
4. Discuss as a colleague who has read the paper closely: answer from the paper, say where it is silent or unclear, and push back where the user or the script got something wrong.
5. When the conversation reaches a conclusion worth keeping (an answer, a correction, a follow-up idea), append it to `discussion.md` under a `## <date>: <topic>` heading. Keep it brief, and only record what was actually discussed.
