# Writing an earstuffing script

The script is read aloud by a text-to-speech voice and heard while driving. The
listener is a senior computational scientist (biomedical knowledge graphs, data
integration, AI/ML, AI agents in science, research software) who has not read
the paper and cannot see it. Write for the ear.

## Shape

Aim for 1,400–1,700 words (about 10 minutes). Short papers can be shorter; do
not pad. Long, dense papers can run to about 2,200 words. Spend the words on the
key idea, the results that matter and the assessment, not on routine detail.

1. **Opening.** One plain sentence naming the paper, the lead authors (first
   author, "and colleagues" if more than two), the venue and year. Then two or
   three sentences giving the main point: what they did and what they found.
2. **The problem.** Why this matters, what was missing before, and where the
   work sits relative to prior approaches. Brief.
3. **What they did.** Data, methods, system design, experimental setup. Explain
   the key idea well enough that the listener could describe it to someone else.
   Skip routine details.
4. **What they found.** The main results with the numbers that matter, given in
   context ("about twelve points better than the strongest baseline"), not
   lists of table cells. Describe what important figures show.
5. **Assessment.** Your own honest, specific judgement: what is convincing, what
   is weak or missing (baselines, evaluation design, data leakage, scale,
   reproducibility, overclaiming), and how much the result is likely to matter.
   Be fair and direct. Say so if the paper is solid; say so if it is not.
6. **Relevance.** A short closing section, introduced with "On relevance." Note
   concrete connections to either of two areas:
   - biomedical knowledge graphs, data integration and standardization, graph
     reasoning and ranking, or applied AI in research infrastructure;
   - agentic AI, especially agents doing science: how they plan, use tools,
     run and judge experiments, and where they fail or need human oversight.
     Biosciences first, but agents in other sciences count.

   Cover whichever areas have a real connection; don't force both. Keep it
   general and public-safe: no internal project names or unpublished work. If
   there is no real connection, say so in one sentence.
7. **Close.** One sentence restating the single thing worth remembering. No
   sign-off.

## Style for listening

- Plain prose paragraphs separated by blank lines. No markdown, headings,
  bullets, tables, URLs, citations in brackets or footnotes.
- Spoken signposts instead of headings: "Here's the setup." "Now the results."
- Short-to-medium sentences. One idea per sentence where possible.
- Spell out symbols and most abbreviations on first use. Say "about forty
  percent", not "~40%". Say "p less than point oh one" only if it matters.
- Never read equations. Describe what they compute in words.
- Explain jargon the first time unless it is standard in the listener's fields.
- No host persona, no "welcome", no jokes, no "in this episode", no hype words
  (groundbreaking, revolutionary, game-changing).
- Do not invent anything. If the paper is unclear about something, say it is
  unclear.

## Summary file

Also write `summary.txt`: two or three sentences for the podcast app's episode
notes. Plain text, what the paper does and the main finding.
