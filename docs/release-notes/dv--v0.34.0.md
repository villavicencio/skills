# dv — v0.34.0

Minor release. `dv:director-mode` ends a finished worktree session itself, with one SIGTERM to
the session's Orca wrapper, when four checks hold. One of them scans every process of the user
whose working directory or an open file is in the worktree, whatever its command name. The other
fifteen skills have no behaviour changes; their version moves to `0.34.0` only because the suite
is released as one plugin.

Numbering: 0.34.0 follows 0.33.0, which made `dv:groom` in `forks-only` mode record a routine
call only when it changes the ticket.

Why: after a worktree session runs `dv:closeout`, it stays open until David closes it in Orca by
hand, and the worktree waits for that. On 2026-11-22 he approved letting the Director end it. The
rule was taken out of 0.23.0 because its one-session check counted only `claude` processes whose
directory was the worktree root, so a second process in a subdirectory or under another command
name was missed, and because it skipped the global removal procedure's "no other session" check
before the signal (VIL-930).

## Changed

- **`dv:director-mode`, "Take closeout notes".** The Director replies to a SendMessage note with
  `notify_when_idle: true`, then ends the session under the new rule below. The highlight that
  the session "is ready to close in Orca" and "You never signal or stop a session's process
  yourself" are gone. When the rule stops nothing, the Director tells David which check failed
  and why, and that the session is still open in Orca for him to close; the worktree waits for
  the session to end, as before. Apart from the rule's one SIGTERM it never signals or stops a
  session's process.
- **New: "End a finished worktree session".** Once the idle notice arrives, the Director runs
  four checks:
  1. The note's header names this worktree, and its verdict is `safe to delete`, or
     `safe once you accept losing: …` with every loss covered by a standing yes.
  2. A `[Cross-session idle notice]` for the session arrives after the note's timestamp (same
     machine only; a note with no `from` address stops nothing).
  3. Nothing changed since the note: `dv:closeout`'s Step 1 block, rerun in the worktree from a
     subshell, gives the same verdict under Step 2, the note's branch, HEAD unmoved since the
     note and no stash on the branch; and the session's transcript holds no message from David
     after the note.
  4. One session: ListAgents lists the session that sent the note and no other peer named for
     the worktree, and the worktree process scan passes (below).

  Then it runs the global removal procedure's step 2 checks (inspection only), whose "no other
  session still in it" is check 4. The stop is one SIGTERM to the session's wrapper: the parent
  of the session's `claude` process (the one the note's `from` address names), whose command
  line is `orca-provider-exec … session stdin-end-and-sigterm -- … claude …` with the same
  `--session-id=` or `--resume=` value. The second `orca-provider-exec` with that value, a child
  of `claude`, is left alone. Right before the signal it confirms ListAgents shows the session
  idle, reruns checks 3 and 4, and rereads the wrapper's command line. No SIGKILL, `pkill` or
  `killall`. After the signal, a `ps` check must show the wrapper and `claude` gone (it says it
  can't run if `ps` fails), and check 4 must pass with no session allowed: ListAgents lists
  neither the session nor any other peer named for the worktree, and the scan finds no process
  of the user in the worktree. Otherwise nothing is removed and David is told what is still
  running. Then the worktree is removed by the global procedure.
- **"Merge and clean up".** For a removal by the global removal procedure, its "no other
  session still in it" is check 4 with no session allowed: ListAgents lists no live session for
  the worktree, and the worktree process scan finds no process of the user with its directory
  or an open file in the worktree. Before the signal, check 4 allows only the session being
  stopped.
- **"The roles"**, the frontmatter description, the plugin description and the README entry
  describe the new behaviour; the README entry drops "It never signals or stops a session's
  process."

## What the one-session check covers

The check has two parts: ListAgents (no peer named for the worktree other than the session being
stopped; for a removal, none at all) and the worktree process scan, a fenced block in the skill run from the main checkout.
The scan reads the process table with `ps` before and after one `lsof` pass over every process
whose effective user id is the Director's user. A process counts as in the worktree when its
working directory, or any file it has open, is the worktree or anything below it, compared
without regard to case and through the worktree's real path. The command name plays no part.
Before the signal the scan passes only when every such process is the session's `claude`
process or one of its descendants, the `claude` process is among them, and `lsof` read every
process of the user (zombies aside) that ran through the whole scan. For a removal it allows no
session, so it passes only when no such process exists. If either `ps` call or `lsof` exits
non-zero or prints nothing, the scan prints `RESULT: cannot run` and the check fails. An Orca
terminal left open in the worktree, such as the Setup terminal that runs a repo's setup script,
is another process, so it fails the check.

## Known limits

- The scan looks only at the user's own processes (`lsof` can't read another user's without
  root), so another user's processes, root's included, aren't seen.
- A session that works in the worktree from a directory outside it, by absolute paths or an
  added directory, with no file open there at the time of the scan, isn't seen. The ListAgents
  part catches a peer only when its name follows the worktree folder's name.
- A process that starts during or after the last scan before the signal may not be seen by
  that scan. The scan after the signal finds it, if it is still in the worktree, before anything
  is removed, but the session has been stopped by then.
- A process the session itself started (a descendant of its `claude` process) counts as part of
  the session before the signal. If it outlives the stop and is still in the worktree, the scan
  after the signal finds it and nothing is removed.
- The closeout recheck compares counts, not contents: a file edited in place with every count
  unchanged is not caught (VIL-868).
- `notify_when_idle` reaches only a session on the same machine, so a session on another host
  is never stopped by the Director.
- The transcript check knows the record kinds Claude Code writes today: a `user` record with
  text content, or a queued-command attachment, not marked as from a peer or a task
  notification. When the transcript is missing or has nothing newer than the note, the check
  can't run and nothing is stopped.

## Tested

On hal, 2026-11-24, with the scan block and the after-the-signal `ps` check taken verbatim from
the skill and their placeholders filled, run from `/` (outside the worktree), in a scratch
detached worktree:

- A stand-in session (a `bash` process in the worktree root with a child `sleep`) alone:
  `SESSION` for both, `RESULT: pass`.
- A second process started with `(cd <worktree>/plugins/dv/skills && sleep 600 &)`:
  `OTHER <pid> <worktree>/plugins/dv/skills`, `RESULT: fail`, so the worktree is kept.
- A stub `lsof` that exits 1, or a stub `ps` that exits 1, first on `PATH`: the scan printed
  `RESULT: cannot run`; with the stub `ps`, the `ps` check printed `CANNOT RUN`.
- After that `sleep` was stopped: `RESULT: pass` again. After a SIGTERM to the stand-in's top
  process only, the `ps` check printed `GONE` for it, and its orphaned child made the scan with
  no session print `OTHER` and `RESULT: fail`; once the child was stopped, `RESULT: pass`.

On this ticket's own worktree, the scan run with the live session's `claude` pid printed
`SESSION` for that process and `OTHER` for the login shell of the worktree's Orca Setup
terminal, so the check would keep that worktree. No Orca session was signalled while writing
this change: the first real stop happens on the first ticket closed out after the merge.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
