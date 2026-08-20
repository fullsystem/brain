---
name: session-learning
description: >-
  Turns the current session's observations into durable knowledge inside a
  local, remote-less git knowledge-base repo (e.g. ~/brain), by doing all the
  learning work on an isolated per-topic learning branch and only ever
  merging the final, consolidated knowledge document — never the raw
  scratch work — into main. Use this skill whenever the user asks to "learn from this
  session", "catalog what we found", "turn this into knowledge", "add this
  to the brain/knowledge base", or after a session that produced findings,
  decisions, or discoveries worth remembering for next time. Also trigger it
  at the start of any session that touches the knowledge-base repo, to check
  for and offer to resolve a learning branch left pending from a previous,
  unfinished session.
---

# Session Learning

This skill is the disciplined container for "observe, catalog, learn" — it
makes sure exploratory, messy learning work never lands on `main` directly.
Everything happens on a throwaway `learning/<slug>` branch; only a clean,
reviewed knowledge document ever gets merged, and only after the user says
so explicitly.

It never operates on the raw git history by hand — all branch creation,
merging, and cleanup goes through `scripts/learning_branch.py`, so the
sequence of git commands is always correct and the pending-session state
(`<repo>/.git/learning_state.json`) never drifts out of sync with what's
actually on disk. Read the script's docstring if you want the exact
mechanics; you only need to call its subcommands.

## 0. Figure out the repo and check for unfinished business

The knowledge-base repo is a local git repo with no remote — default to
`~/brain` unless the user names a different one or you're clearly already
inside one (check with `git rev-parse --is-inside-work-tree`).

Before starting anything new, always run:

```bash
python3 <skill_dir>/scripts/learning_branch.py --repo <repo> status
```

If this returns one or more pending sessions, tell the user what's sitting
unresolved (branch name, topic) and ask — one question, plain language —
whether they want to resume it, decide its fate right now (go straight to
step 3 for that branch), or leave it alone and start something new. Don't
silently bury a pending branch by starting a new one without mentioning it;
that's exactly the kind of loose end this skill exists to prevent.

## 1. Decide the topic and the model

Pick a short topic and derive a slug from it the same way `knowledge-writer`
does (lowercase, hyphenated, e.g. `retry-logic-stripe-webhook`).

This skill can be told which model should actually perform the learning
work — pass it as a `model:` argument when invoking the skill (e.g. `model:
claude-opus-4` alongside the topic), or the user may simply say "use
<model> for this". When a model is given, you MUST honor it for the
learning work in step 2 by passing it as the `model` option on the `Agent`
tool call. When no model is given, don't set the option at all — per the
`Agent` tool's own guidance, omitting it inherits the session's model,
which is the right default. Never guess or default to a specific model
name yourself.

## 2. Open the branch and do the learning there

```bash
python3 <skill_dir>/scripts/learning_branch.py --repo <repo> start --slug <slug> --topic "<topic>"
```

This checks out (creating if needed) `learning/<slug>` off the repo's
default branch, and records the session as pending. From this point on,
treat that checkout as the sandbox: any exploration, drafts, scratch notes,
or intermediate files belong there, committed normally with `git -C <repo>
commit`, so the work is recoverable even if the session ends mid-way.

Do the actual observing/researching/cataloging by spawning a subagent with
the `Agent` tool (passing `model` per step 1 when one was given), pointed at
the checked-out branch, with instructions to investigate the topic and
report back its raw findings — decisions made, things confirmed true,
things ruled out, gotchas, open questions. You are the one who commits
whatever scratch artifacts are worth keeping on the branch; the subagent's
job is to produce the findings, not to manage git.

## 3. Consolidate with knowledge-writer

Once the learning work feels complete, hand the accumulated raw findings to
the `knowledge-writer` skill (invoke it via the `Skill` tool), passing it
the topic and the raw material. It writes or updates
`knowledge/<slug>.md` in the working tree — it does not commit or touch
branches, so commit that file yourself on the `learning/<slug>` branch
(e.g. `git -C <repo> add knowledge/<slug>.md && git -C <repo> commit -m
"consolidate: <topic>"`) before moving on.

## 4. Ask what to do with it

Ask the user directly — a single, plain yes/no question — whether this
knowledge should go into the main knowledge base now. Use the `AskUserQuestion`
tool when it's available and the session is interactive; a plain-text
question is fine when it isn't.

Then act on the answer:

- **Yes** — merge only the consolidated file, nothing else, and clean up
  the branch:
  ```bash
  python3 <skill_dir>/scripts/learning_branch.py --repo <repo> finalize \
    --branch learning/<slug> --action merge --files knowledge/<slug>.md
  ```
  This lands a single commit on the default branch containing just the
  knowledge document — none of the scratch work, dead ends, or intermediate
  commits from the branch make it into `main` — and deletes the learning
  branch. Confirm to the user what got merged.

- **No** — discard the whole attempt:
  ```bash
  python3 <skill_dir>/scripts/learning_branch.py --repo <repo> finalize \
    --branch learning/<slug> --action discard
  ```
  This deletes `learning/<slug>` entirely, findings and all. Confirm to the
  user that it was discarded and nothing was kept.

- **No answer, or an answer that doesn't actually address the question**
  (off-topic reply, the user changes subject, the session ends before they
  respond) — do NOT guess and do NOT re-ask insistently. Leave the branch
  exactly as it is:
  ```bash
  python3 <skill_dir>/scripts/learning_branch.py --repo <repo> finalize \
    --branch learning/<slug> --action keep
  ```
  This just confirms the session stays recorded as pending; it changes
  nothing else. Tell the user plainly, in your own words, that you left it
  unresolved, name the branch (`learning/<slug>`), and say how to get back
  to it — `git -C <repo> checkout learning/<slug>` to look at it directly,
  or simply invoking this skill again next time, which will surface it
  automatically in step 0.

## Why this shape

The branch isolation means an interrupted or abandoned learning attempt
never leaves partial, unreviewed material on `main`. The merge step only
ever copies the single consolidated file — never the branch's full
history — so `main` accumulates clean knowledge documents, not a messy
trail of scratch commits. And the persistent pending-state file means a
learning attempt that's neither confirmed nor rejected is never silently
lost; it just waits for a real decision.
