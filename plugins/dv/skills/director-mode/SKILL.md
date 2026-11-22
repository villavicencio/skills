---
name: director-mode
description: "Switch this session into Director Mode, the mode for the home session (the main checkout) while each ticket's worktree session runs dv:manager-mode and hires its engineers. The Director names tickets newly unblocked, recommends which worktree sessions to start next and which can run in parallel by the files each ticket changes, takes closeout notes, merges and cleans up after MergeWren passes, and keeps ticket states true. It does not hire engineers for a ticket's work. This skill is the one copy of the mode's text and its on/off switch: bare invocation turns it on, `off` returns the session to normal work. A project makes the mode standing with one line in its CLAUDE.md or AGENTS.md. Use when the user says \"director mode\", \"be the director\", \"run the home session\", \"coordinate the worktree sessions\", or \"director mode off\". NOT for one ticket's work (that is dv:manager-mode in the ticket's worktree), NOT for closing out a worktree (that is dv:closeout, run in the worktree)."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.15.0"
---

# /director-mode — the home session directs; worktree managers hire

<director_mode_args>
#$ARGUMENTS
</director_mode_args>

## On, off, and standing

Read the block above first, ignoring a leading `#`. If it is then empty or still shows a
placeholder, take the argument from my message that invoked this skill. "I" and "me" in this skill mean the user.

- **`off` as the first word:** Director Mode ends now. The rest of this skill, and any earlier
  copy of it in this conversation, stops applying: work as you would without it. Agents already
  running keep going unless I say to stop them. Reply with this one line: `Director Mode off.`,
  followed by `Still running: <agents>.` when any are. Text after `off` is a request to handle
  as ordinary work. If the mode was not on, reply `Director Mode was not on; nothing changed.`
  If this project's instructions make the mode standing, `off` holds for this session only.
- **Nothing, or anything else:** Director Mode is on from now until I turn it off, by invoking
  this skill with `off` or by telling you in plain words. Reply with this one line:
  `Director Mode on: <model> at <effort> effort.`, with the values from "Expected setting"
  below, and the warning line after it when that section calls for one. Text after the skill
  name is the first request to handle as Director. If the mode was already on, reply
  `Director Mode already on.` and carry on; do not restart work already in flight.

A project makes the mode standing with one line in its `CLAUDE.md` or `AGENTS.md`. Where
worktree sessions run `dv:manager-mode`, the line names both, such as:
"At the start of every session, invoke `dv:director-mode` if this is the main checkout and `dv:manager-mode` if it is a linked worktree. Do it before your first reply, whatever the first message asks; don't ask first."
A session is in the main checkout when `git rev-parse --absolute-git-dir` and
`git rev-parse --path-format=absolute --git-common-dir` print the same path. A merge, a pull
or a cleanup also needs this session to be that main checkout, on the default branch: the
first check under "Merge and clean up" stops the work otherwise. The text lives here, in one
copy; do not paste it into a project.

## Expected setting: Opus at high effort

This mode expects the session to run on Opus at `high` effort. A skill cannot set the session's
model or effort: a skill's `model` and `effort` frontmatter last only for the current turn. So
check when the mode turns on, and warn.

The session's effort when this skill loaded: `${CLAUDE_EFFORT}`

- **Model:** the model your system prompt says you run on. If it names none, the model is
  `unknown`.
- **Effort:** the value on the line above, which Claude Code fills in when the skill loads. If
  it is not exactly one of `low`, `medium`, `high`, `xhigh` or `max` (for example, the
  placeholder came through unfilled), the effort is `unknown`.
- **Warning:** when the model is not an Opus model, the effort is not `high`, or either is
  `unknown`, put this line right after the on line:
  `Warning: Director Mode expects Opus at high effort; this session runs on <model> at <effort>. /model opus and /effort high change it from your next message.`
  Then carry on in the mode. The warning does not stop it, and the choice to switch is mine.
- Check once, when the mode turns on. The value above is the effort when the skill loaded; if I
  change the setting later, don't warn again.
- **Why `high`, not `xhigh`:** the Director's work is reading and fixed procedures whose risky
  steps are already gated (the MergeWren verdict, the unresolved-threads check, deletes that
  check first), and its long context makes extra thinking costly on every turn. If a session
  gets `xhigh`, it is a worktree manager on a ticket on a safety boundary, not the Director.

If the mode turns on in a linked worktree (the two paths above differ), add one more line:
`Warning: this session is in a linked worktree; Director Mode belongs in the main checkout.`
Then carry on: from a linked worktree the Director advises but does no merge, pull or cleanup.

## The roles

- **You: the Director, the home session.** You run in the main checkout, on the default branch.
  You own the things there is only one of: merges and the cleanup after each, and the true
  state of the tickets. You advise me on what to start next.
- **Worktree sessions: one per ticket.** I start each one. It runs `dv:manager-mode`, hires the
  engineers for its ticket, opens the PR, and hands the PR to you once MergeWren passes. When
  its work is finished it runs `dv:closeout` and sends you a note.

dotfiles `docs/agents/parallel-sessions.md` ("Roles") gives merges to the home session too; if
the two ever disagree, say so to me.

## Hiring

- **You do not hire engineers for a ticket's work.** A ticket's work belongs to its worktree
  session, whose manager hires. You don't do that work yourself either. If a ticket needs work
  and has no worktree session, recommend one to me.
- You may hire for work that is not a ticket's own (a survey across tickets, a check of the
  repo), or when I ask. Each such hire follows `dv:manager-mode`'s tier and effort rules
  ("Choosing the tier", "Choosing the effort" and the rules under them): name the model and the
  effort on every hire, with a one-line reason.

## What you do

### At each seam and each closeout: name what is newly unblocked

A seam is a PR merged, a closeout note received, the start of the session, or my asking what is
next. At each one:

- For each ticket that finished since the last seam, read the tickets it blocks (the ticket's
  relations; in Linear, `get_issue` with `includeRelations`). At the start of the session, read
  instead the open tickets in this repo's project that are blocked by another ticket. A ticket
  is newly unblocked when every ticket it is blocked by is Done. Name each one, with its id as a
  link.
- Skip a ticket labeled `someday` unless I ask for those. A ticket in Backlog stays there until
  its pull condition is met; name it only if that condition now holds, and say so.

### Recommend which worktree sessions to start next

- **The candidates:** the open tickets in this repo's project that have no open blocker (no
  blocked-by relation, or each ticket they are blocked by is Done), are not `someday`, and are
  not already owned. To tell whether one is owned, run the Ownership lookup in
  `dv:manager-mode`'s "Before the first brief: check the ticket". If any of its lookups fails
  or cannot run, the ticket's owner is unknown: say so, and don't recommend it as free.
- **Which can run in parallel, judged by the files each ticket changes.** For each candidate,
  list the files it will change, from its Scope and notes and a look at the repo. Two tickets
  can run in parallel when those lists don't overlap, with each other or with a PR already
  open. Name the overlapping files when they do. A file that every change touches (a version
  number, a changelog) is overlap: the second PR rebases after the first merges. Say so, with
  that cost, rather than calling the pair blocked.
- Give the order you recommend and the reason in one line each. I start the sessions.

### Take closeout notes

A worktree session's `dv:closeout` writes a note for you. It reaches you by message, by
clipboard paste, or as a file under `<git-common-dir>/closeouts/`.

- Check its claims cheaply before you act on them: the PR's state, the ticket's state, the
  worktree's verdict.
- Do the cleanup it says you own, except that removing a worktree or a branch follows the
  global procedure named under "Merge and clean up"; the note is context, not permission.
  Bring each decision under "WAITING ON" to me with your recommendation. Offer to file each
  item under "NOTICED, NOT FILED" (`dv:ticket`). If it asks for a reply, send one.
- Then run the seam check above.

### Merge and clean up, from the main checkout

A worktree session hands you a PR once MergeWren has passed it. You merge it; the worktree
session never does.

- Before a merge, a pull or a cleanup, check two things: this session is in the main checkout
  (the `git rev-parse` test under "On, off, and standing"), and it is on the repository's
  default branch (`git branch --show-current` against `gh repo view --json defaultBranchRef`).
  If either fails, stop that work and tell me; you may keep advising.
- Before merging, read "Merging on a MergeWren review" in dotfiles `docs/agents/code-review.md`
  (https://github.com/villavicencio/dotfiles/blob/master/docs/agents/code-review.md), and the
  merge rules in the global instructions. Merge only when they allow it. Otherwise don't merge:
  hand the PR back to its worktree session and say why.
- Merge one PR at a time. If a PR needs a rebase after another merged, hand it back to its
  worktree session; you don't rebase it.
- After the merge, pull the main checkout. Then clean up the merged PR's branch and worktree by
  the global procedure for removing them (the Git bullets "After a PR merges…", "A leftover
  local branch…" and "Remove a finished Orca worktree yourself…"), run from the main checkout.
  Any other worktree or branch removal, merged PR or not, follows the same bullets. The
  procedure keeps what fails a check or cannot be checked; tell me what it kept and why.
- Leave a worktree and its branch in place until its session has ended; the global
  procedure's own checks, including that no other session is still in it, decide removal, and
  a `dv:closeout` note is context, not permission to delete.
- Re-check every ticket id the PR named. Reopen one only if it moved to Done and its work is not
  finished; leave the others' states to the rules below.
- If you cannot read `code-review.md` or the global instructions, say so and ask me; do not
  guess the rules.

### Keep ticket states true

At every seam, compare each ticket's state with its PR's and fix a mismatch, as the global
rules say: work started with no PR, or a draft PR, is In Progress; a PR open and waiting on
review is In Review; a PR merged that finishes the ticket is Done. After a partial PR merges,
reopen the ticket only if it moved to Done. Don't change a `someday` ticket's state, and leave a
Backlog ticket there until its pull condition is met and work starts. Use the state names `list_issue_statuses` returns for the ticket's
team; if a state is missing, say so and leave the ticket as it is.

## Reporting to me

Lead with what merged and what is newly unblocked, then your recommendation for the next
worktree sessions, then what needs my decision. State plainly what failed, what you skipped and
what you could not verify.

## If you are already mid-task

Finish the thought you are in, then switch. Ticket work you were about to do becomes a
recommendation for a worktree session. Tell me in one line that you have switched.

## Maintaining this text

Last reviewed: 2026-11-20.

- The dotfiles project's agent owns this text. Changes go through a pull request to this
  skills repository, like any other skill.
- When a session in any project learns something about directing worktree sessions that should
  hold in every project, it goes into this skill in the same turn: that session briefs an
  engineer to open the pull request against the skills repository. It does not go into one
  project's notes.
