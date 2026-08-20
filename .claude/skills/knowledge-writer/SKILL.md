---
name: knowledge-writer
description: >-
  Consolidates raw learnings, scratch notes, conversation excerpts,
  decisions, and discoveries about a topic into a single clean,
  well-structured Markdown knowledge document under a knowledge/ directory
  (one file per topic) in the current git repo. Use this skill whenever another skill, workflow, or
  the user needs to turn messy session notes into a polished, de-duplicated
  knowledge artifact — especially right before merging a learning branch,
  when asked to "write up what we learned", "consolidate notes into
  knowledge", "document this decision", or "create/update the knowledge doc
  for X". Idempotent — re-running it for the same topic updates the existing
  document instead of duplicating it. Does not touch git branches or
  commits; that stays the caller's job.
---

# Knowledge Writer

Turns raw material — notes, transcript fragments, decisions, dead ends, discoveries — into one clean knowledge document. This skill is a pure writer: it reads and writes exactly one file in the working tree and never touches git (no branch, no commit, no push). Whatever invokes this skill owns version control.

## When you're given raw material

You will typically receive, inline in the prompt or as pasted text:

- a **topic** (a short phrase or working title) — if none is given, infer one from the content
- a pile of **raw observations**: notes, quotes, decisions made, things that turned out to be true, things that turned out to be false or were abandoned, links, commit hashes, file paths

Your job is editorial, not transcription. Read everything before writing anything.

1. **Decide the topic and slug.** The slug is the filename: lowercase, ASCII, words joined with hyphens (e.g. "Retry logic for the Stripe webhook" → `retry-logic-stripe-webhook`). Keep slugs short but unambiguous — this is a key other invocations will look up later.

2. **Filter before you write.** Drop: exploratory dead ends that led nowhere, duplicated statements, hedges that were later resolved ("I think X" followed later by a confirmed "actually Y"), anything that's just narration of the process ("then I searched for...") rather than a durable fact or decision. Keep: what's actually true now, decisions and their rationale, gotchas and constraints, anything a future reader would need to avoid re-learning it the hard way.

3. **Organize by meaning, not by chronology.** The raw notes usually arrive in the order they were discovered; the knowledge document should instead be organized by the topic's natural structure (e.g. "how it works", "constraints", "gotchas", "open questions") — use sections only where they earn their keep. A short topic can be a few paragraphs with no headers at all; don't force structure that isn't there.

## Where the document lives

`knowledge/<slug>.md`, relative to the repository root (create the `knowledge/` directory if it doesn't exist yet). Never write outside this directory or guess a different location, even if the caller's prompt suggests one — consistent placement is what makes documents findable later.

## Document format

Always use this exact shape:

```markdown
---
title: <short human-readable title>
tags: [<lowercase>, <topic-words>]
created_at: <ISO 8601 date, YYYY-MM-DD>
updated_at: <ISO 8601 date, YYYY-MM-DD>
source_branch: <branch name, if the caller told you one; omit the field otherwise>
---

<1-3 sentence summary of what this document tells the reader>

## <Section title, only if the topic needs sections>

<prose body>

## References

- <link, file path, or commit hash, one per line — omit this whole section if there's nothing to cite>
```

Write the body in prose paragraphs, not bullet-point dumps — bullets are fine for genuinely list-shaped content (a set of gotchas, a list of references) but the explanatory parts should read like something a colleague wrote, not a raw notes dump.

Because you don't know today's date from your own knowledge, get it from the caller's context (session date) or from the file's own existing `created_at` when updating; if truly unavailable, ask rather than guess.

## Creating vs. updating (idempotency)

Before writing, check whether `knowledge/<slug>.md` already exists.

- **Doesn't exist:** write a new file per the format above. Set `created_at` and `updated_at` to today.
- **Already exists:** read it first. Merge the new material into the existing document rather than appending or overwriting wholesale — update stale statements the new notes contradict, fold in genuinely new information into the right section (or a new one), and leave what's still accurate alone. Bump `updated_at` to today; leave `created_at` untouched. If the caller passed a `source_branch` different from the one on file, you can keep the original `source_branch` (it recorded where the document originated) unless the caller asks you to change it.

Never create a second file for a topic that already has one — if you're unsure whether an existing document covers the same topic, prefer reusing/updating it over creating a near-duplicate; only create a new file when the topic is genuinely distinct.

## When you're done

Report back, in your own final text, the path you wrote or updated (`knowledge/<slug>.md`) and one line on whether it was a create or an update — the caller needs this to know what to commit.
