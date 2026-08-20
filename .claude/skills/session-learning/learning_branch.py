#!/usr/bin/env python3
"""
learning_branch.py — deterministic git plumbing for the session-learning skill.

This script never decides *whether* to merge, discard, or keep a learning
branch — that's a judgment call the skill makes (usually after asking the
user). It only performs the mechanical git operations reliably, so the
model doesn't have to hand-run a sequence of git commands and risk getting
one wrong (wrong branch checked out, wrong files staged, forgetting to
clean up state, etc).

State lives at <repo>/.git/learning_state.json — inside .git/, so it is
never tracked, never shows up in `git status` on any branch, and survives
branch switches and even across unrelated Claude sessions as long as the
same repo/checkout is used.

Subcommands:
  status   Show all pending (unresolved) learning sessions.
  start    Create or resume a learning/<slug> branch and record it as pending.
  finalize Resolve a pending session: merge, discard, or keep.

Examples:
  python3 learning_branch.py status --repo ~/brain
  python3 learning_branch.py start --repo ~/brain --slug retry-logic --topic "Retry logic for the webhook"
  python3 learning_branch.py finalize --repo ~/brain --branch learning/retry-logic --action merge --files knowledge/retry-logic.md
  python3 learning_branch.py finalize --repo ~/brain --branch learning/retry-logic --action discard
  python3 learning_branch.py finalize --repo ~/brain --branch learning/retry-logic --action keep
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(repo, args, check=True):
    result = subprocess.run(
        ["git", "-C", str(repo)] + args,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}"
        )
    return result.stdout.strip()


def state_path(repo):
    return Path(repo) / ".git" / "learning_state.json"


def load_state(repo):
    p = state_path(repo)
    if not p.exists():
        return {"sessions": []}
    return json.loads(p.read_text())


def save_state(repo, state):
    state_path(repo).write_text(json.dumps(state, indent=2) + "\n")


def detect_base_branch(repo):
    """Best-effort default branch: prefer main, then master, then whatever
    branch we're currently on (covers a brand-new repo with a single branch
    under any name)."""
    branches = run(repo, ["branch", "--format=%(refname:short)"]).splitlines()
    for candidate in ("main", "master"):
        if candidate in branches:
            return candidate
    return run(repo, ["symbolic-ref", "--short", "HEAD"])


def cmd_status(args):
    state = load_state(args.repo)
    pending = [s for s in state["sessions"] if s["status"] == "pending"]
    print(json.dumps(pending, indent=2))


def cmd_start(args):
    repo = args.repo
    branch = f"learning/{args.slug}"
    state = load_state(repo)
    existing = next((s for s in state["sessions"] if s["branch"] == branch), None)

    branches = run(repo, ["branch", "--format=%(refname:short)"]).splitlines()
    if branch in branches:
        run(repo, ["checkout", branch])
        action = "resumed"
    else:
        base = detect_base_branch(repo)
        run(repo, ["checkout", base])
        run(repo, ["checkout", "-b", branch])
        action = "created"

    if existing:
        existing["status"] = "pending"
        existing["topic"] = args.topic or existing.get("topic", "")
    else:
        state["sessions"].append(
            {
                "branch": branch,
                "slug": args.slug,
                "topic": args.topic or "",
                "status": "pending",
            }
        )
    save_state(repo, state)
    print(json.dumps({"action": action, "branch": branch}, indent=2))


def cmd_finalize(args):
    repo = args.repo
    state = load_state(repo)
    entry = next((s for s in state["sessions"] if s["branch"] == args.branch), None)
    if entry is None:
        raise RuntimeError(
            f"No pending session recorded for branch {args.branch!r}. "
            f"Run `status` to see known sessions."
        )

    if args.action == "merge":
        if not args.files:
            raise RuntimeError("merge requires --files (comma-separated paths)")
        base = detect_base_branch(repo)
        run(repo, ["checkout", base])
        files = [f.strip() for f in args.files.split(",") if f.strip()]
        run(repo, ["checkout", args.branch, "--"] + files)
        run(repo, ["add"] + files)
        message = args.message or f"knowledge: {entry.get('topic') or entry['slug']} (from {args.branch})"
        run(repo, ["commit", "-m", message])
        run(repo, ["branch", "-D", args.branch])
        state["sessions"] = [s for s in state["sessions"] if s["branch"] != args.branch]
        save_state(repo, state)
        print(json.dumps({"action": "merged", "base": base, "files": files}, indent=2))

    elif args.action == "discard":
        base = detect_base_branch(repo)
        current = run(repo, ["symbolic-ref", "--short", "HEAD"])
        if current == args.branch:
            run(repo, ["checkout", base])
        run(repo, ["branch", "-D", args.branch])
        state["sessions"] = [s for s in state["sessions"] if s["branch"] != args.branch]
        save_state(repo, state)
        print(json.dumps({"action": "discarded", "branch": args.branch}, indent=2))

    elif args.action == "keep":
        entry["status"] = "pending"
        save_state(repo, state)
        print(json.dumps({"action": "kept", "branch": args.branch}, indent=2))

    else:
        raise RuntimeError(f"Unknown action {args.action!r}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="Path to the git repository")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="List pending learning sessions")

    p_start = sub.add_parser("start", help="Create or resume a learning branch")
    p_start.add_argument("--slug", required=True)
    p_start.add_argument("--topic", default="")

    p_fin = sub.add_parser("finalize", help="Resolve a pending learning session")
    p_fin.add_argument("--branch", required=True)
    p_fin.add_argument("--action", required=True, choices=["merge", "discard", "keep"])
    p_fin.add_argument("--files", help="Comma-separated paths to merge (merge action only)")
    p_fin.add_argument("--message", help="Override commit message (merge action only)")

    args = parser.parse_args()
    args.repo = str(Path(args.repo).expanduser())

    try:
        {"status": cmd_status, "start": cmd_start, "finalize": cmd_finalize}[args.command](args)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
