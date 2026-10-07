# dv — v0.5.0

Minor release. `dv:handoff` and `dv:pickup` now support **several Claude Code sessions on one repo at
once**, one git worktree and branch each. The release also ships a new skill, `dv:mnemosyne-ops`. The
other nine skills have no behaviour changes; their version moves to `0.5.0` only because the suite is
released as one plugin.

## What's new

### Parallel sessions: one handoff per branch (`dv:handoff` + `dv:pickup`), PR #43

Before this release, both skills assumed one session per project:
- In a single checkout, a second session's `HANDOFF.md` replaced the first.
- In repos that commit it, every branch's copy conflicted at merge.
- `pickup` couldn't see sessions running in other worktrees.

**What changes:**
- **`/handoff` also copies the handoff into a per-branch store,** at
  `<git-common-dir>/handoffs/<branch>.md`.
  - That location is shared by every worktree of the clone, isn't tracked by git (so it never conflicts
    at merge), and survives `git worktree remove`.
  - Branch names are percent-encoded (`%` → `%25`, `/` → `%2F`), so no two branches share a file. A
    detached HEAD is keyed by its full sha.
  - `HANDOFF.md` stays where it is as a plain copy. It isn't a symlink, because symlinks break on Windows
    and WSL.
  - New frontmatter field: `worktree`.
- **`/pickup` reads this branch's handoff,** from the store first, then `HANDOFF.md`.
  - Identity is checked before recency. A handoff recorded for *this* worktree wins on mtime. A newer one
    from another branch never displaces this branch's own copy. Reading another branch's handoff (or one
    left on a detached HEAD) produces a warning.
- **`/pickup` adds an "Other sessions in flight" block.** It lists:
  - every other branch's handoff, with commits since that handoff and its focus;
  - every worktree with no handoff yet, including detached ones.
- **Merged work gets archived.** A handoff whose PR has merged moves to
  `handoffs/_done/<key>.<UTC timestamp>.md`. It's never deleted and never overwrites an earlier archive.
  It's archived only when the merged PR's head is the branch tip, or the branch is gone; a reused branch
  gets a note instead.
- **Every block in both skills is self-contained.** Claude Code's Bash tool keeps no shell state between
  calls, so a block that depended on another block's variables would silently produce an empty anchor
  and an empty session list.

### New skill: `dv:mnemosyne-ops`, PR #42 (VIL-143)

It enables, health-checks and maintains the Mnemosyne memory provider on a Hermes profile:
- a gated enable script with integrity hashes before and after;
- a read-only drift check;
- a check that proves the tools configuration controls the schema.

The PR has the details.

## Behaviour changes to know about

- **`HANDOFF.md` is now committed only from the default branch,** taken from `origin/HEAD`, else a local
  `main`, else `master`. On a feature branch the store holds the handoff. **If the default branch can't be
  determined, nothing is committed.** This fails closed, because committing on a feature branch is
  exactly the case the rule exists to prevent.
- **Repos with no handoff store behave exactly as 0.4.0.** `HANDOFF.md` in the working directory is the
  handoff.

## Measured facts this design relies on (Claude Code 2.1.278, 2026-10-06)

A session started in a git worktree **shares the main checkout's memory directory**, but writes its
transcripts to a **separate** project folder keyed by the worktree's path. That's why the store, not
transcripts, carries state between sessions. It's also why `claude --continue` in a worktree resumes that
worktree's own session.

## Verification

- **Every fenced block was extracted from the shipped `SKILL.md` files** and run as its own shell process
  in sandbox repos with worktrees, a path containing a space, and a `gh` stand-in. Run under `zsh -f`,
  GNU bash 5.3 and macOS `/bin/bash` 3.2.
- **Each of the seven review findings** across three rounds was reproduced on the earlier commit first, then
  shown fixed.
- **`agentskills validate`** passes on all 11 skills, and `tooling/evals/test_assertions.py` and `test_trigger_parsing.py` pass.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The update applies on the next session restart.
