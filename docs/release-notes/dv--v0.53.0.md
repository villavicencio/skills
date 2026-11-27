# dv — v0.53.0

Minor release. `dv:director-mode` now reads a finished worktree's latest saved `dv:closeout`
note, one that never reached the Director included, before it removes the worktree after the
worktree's session has ended, however the session ended. It removes the worktree, by the global
removal procedure as before, only when that note's Worktree line passes check 1's verdict rule
under "End a finished worktree session" (it starts `Worktree: safe to delete,`, or
`Worktree: safe once you accept losing:` with every listed loss covered by a standing yes of
David's) and "The closeout recheck" there, run against that note, passes. Otherwise
(`NOT safe to delete`, `not confirmed safe`, a loss no standing yes covers, no note it can read,
or a recheck that differs or can't run) it keeps the worktree and its branch and tells David the
note's path and its Worktree line word for word, or that there is no note, and what the recheck
found when it failed. No note keeps the worktree on every such path, "No session is live" and any
other removal under "Merge and clean up" included, and a note the lookup can't find (saved before
the branch was renamed or HEAD detached, or hidden by a newer copy for another worktree on the
branch) counts as none. The recheck also needs the worktree's `HANDOFF.md`, if there is one, to be
a regular file with a byte-identical copy in `handoffs/_done/`, since closeout's Step 1 leaves it
out. The one worktree removed with no note is a stale-PR repair's temporary worktree, identified
by the checks "No session is live" gives it (its exact path and full HEAD, the merged PR, one
detached worktree record). The note can only keep a worktree; it never permits a removal the global procedure's checks
refuse. `dv:closeout` and the README drop the known limit this fixes. The other fourteen skills
have no behaviour changes; their version moves to `0.53.0` only because the suite is released as
one plugin.

Numbering: 0.53.0 follows 0.52.0 (skills PR 132), which merged first.

Why: when a worktree session's closeout note read `not confirmed safe` (for example, its handoff
archive failed and left a `HANDOFF.md` that exists only in the gitignored worktree), check 1 kept
the Director from asking David to close or release that session. But when the session ended
another way, such as David closing it in Orca, "Take closeout notes" removed the worktree by the
global removal procedure alone ("the note is context, not permission"), and the `GONE` path under
"End a finished worktree session" skipped check 1. The global procedure (the global instructions'
"Remove a finished Orca worktree yourself" and dotfiles `docs/reference/orca-worktrees.md`) reads
no closeout note and names no check that refuses a worktree-only ignored file, so the note's
warning was never read and the file could be lost with the worktree (VIL-1209).

## Changed

- **`dv:director-mode`, "Take closeout notes", the bullet "Run the cleanup the note names".**
  After the session has ended, the Director first reads the worktree's latest closeout note and
  keeps the worktree unless its Worktree line passes check 1's verdict rule and "The closeout
  recheck", run against that note, passes (the worktree may have changed after the note was
  saved). The latest note is the newest copy saved for the worktree's branch under
  `<git-common-dir>/closeouts/`, named
  exactly `<branch slug>.<YYYYMMDDTHHMMSSZ>.txt` or `…-<n>.txt` on a clash: the latest timestamp,
  then the highest `<n>` compared as a number, not by `ls` or `sort` order (the slug is the branch
  name as closeout's Step 3 block writes it). A copy whose header names another worktree path
  counts as no note, and one whose first line is not a `CLOSEOUT NOTE` header as a note the
  Director can't read. A note the lookup can't find (saved before a branch rename or a detached
  HEAD, or hidden by a newer copy for another worktree) counts as no note, so the worktree is
  kept.
- **`dv:director-mode`, "End a finished worktree session", the `GONE` path.** A session found
  already ended skips the ask and that rule's checks, except that the Director applies check 1's
  verdict rule to the worktree's latest closeout note and then runs the closeout recheck against
  it, as "Take closeout notes" says: keep the worktree and tell David why when the note fails the
  rule, there is no note it can read, or the recheck differs or can't run; otherwise remove it by
  the global procedure with check 4 in its removal form.
- **`dv:director-mode`, "End a finished worktree session", "The closeout recheck".** One more
  condition, so every path that runs the recheck gets it: a worktree `HANDOFF.md` must be a
  regular file, not a symlink, and byte-identical (`cmp`) to a regular file closeout's Step 4
  archived for the branch in `handoffs/_done/` under the git common directory. A symlinked store,
  a check that fails, or no identical copy keeps the worktree. Step 1 leaves `HANDOFF.md` out of
  its inventory, so before this a handoff edited after a safe note passed the recheck.
- **`dv:director-mode`, "End a finished worktree session", "After I close it".** The removal
  after David closes the chat (or after a supervised release) now goes by "Take closeout notes"
  too, reading the latest note again, so a copy saved after the one checks 1 to 3 read can keep
  the worktree. Check 3's rerun there now includes the recheck's `HANDOFF.md` condition.
- **`dv:director-mode`, "Merge and clean up", "No session is live" after the merge.** A session
  that ended before the merge may have saved a note that never reached the Director. Before any
  step of the cleanup (`cleanup_merged_branch` included, since it removes a clean worktree
  itself), the Director reads the latest closeout note of the worktree that has the merged PR's
  branch checked out, and removes the worktree only as "Take closeout notes" says for a session
  that has ended. A note that fails, no note, or a latest copy or `closeouts/` it can't read keeps
  the worktree and its branch (`cleanup_merged_branch` is skipped for that branch), and David is
  told the folder and the note's Worktree line, or "no closeout note". A branch no worktree has
  checked out is cleaned up as before. The stale-PR repair's temporary worktree, identified by
  that text's checks (its exact path and full HEAD, the merged PR, one detached worktree record),
  is the one worktree removed with no note.
- **`dv:director-mode`, "Merge and clean up", the cleanup bullet.** Any other worktree removal
  there ("Any other worktree or branch removal, merged PR or not") first reads the worktree's
  latest closeout note and removes or keeps it the same way, keeping one with no note, except the
  stale-PR temporary worktree.
- **`dv:director-mode`, "Merge and clean up".** The bullet that leaves a worktree in place until
  its session has ended now says that, once its session has ended, that worktree's latest
  closeout note, or the lack of one, can keep it ("Take closeout notes", and "No session is live"
  after the merge); a note is still not permission to delete.
- **`dv:closeout`, Step 3 ("The note follows Step 4"), Step 5 ("The probe's peer has the note")
  and "When the probe's peer has the note, ask nothing", and the README's `dv:closeout` entry.**
  The known limit "if the session ends another way, the Director's later removal does not read
  the note" is replaced by what the Director now does. What still holds after a session ends
  another way: the Director's removal goes by the note's Worktree line and the recheck, so items
  under WAITING ON or REPLY NEEDED, and a message from David after the note, don't keep the
  worktree (known limit).

## Not in this release

- The stale-PR repair's temporary worktree under "Merge and clean up": an engineer makes it
  detached, with no session of its own, and once that text's checks identify it (its exact path
  and full HEAD, the merged PR, one detached worktree record), they still remove it with no
  closeout note.
- A note lookup that follows a branch rename or a detached HEAD: such a note counts as no note,
  which keeps the worktree.
- The "losses I accepted before the note" wording in the "Take closeout notes" bullet before this
  one (VIL-1263 owns it).
- A run of the `GONE` path with a real session: the lab run below gave the Director a `from`
  pid with no process behind it.

## Checked

In a disposable lab clone (its own bare origin, no GitHub remote, push disabled, read-only `gh`
and `orca` stand-ins), headless Opus sessions at high effort ran real `dv:closeout` closeouts in
plain git worktrees, and then a headless Director was told "I closed the session for <worktree>
in Orca":

- Latest note `not confirmed safe` (Step 4 printed `ARCHIVE INCOMPLETE`; an earlier copy for the
  same branch read `safe to delete`): kept, twice; the Director named the newer copy.
- Latest note `not confirmed safe` (a reflog-only commit waiting on David's yes): kept.
- Only note `safe to delete` (Step 4 archive confirmed): removed, and its branch deleted with
  `delete_leftover_branch`.

After review, the same lab ran this text with the closeout recheck in the gate (the wording
changes made after these runs don't touch these cases):

- Only note `safe to delete` (Step 4 archive confirmed), "I closed the session": the Director
  reran closeout's Step 1 as the recheck (same verdict, HEAD last moved before the note, no
  stash), then removed the worktree and deleted its branch.
- The `GONE` path, the note's `from` pid naming no process: latest copy `safe to delete`, an
  earlier copy `not confirmed safe` (the headless permission checker had refused Step 4). The
  `ps` check printed `GONE` and the recheck passed: removed.
- "No session is live" after a merge given to it as a stand-in, latest note `not confirmed safe`
  and never delivered (an earlier copy read `safe to delete`): kept, with the note's path and
  Worktree line word for word. The Director did not run `cleanup_merged_branch`, saying it
  would have removed the clean worktree and its worktree-only `HANDOFF.md`.

After the second review, on this text:

- Latest note `safe to delete` and `HANDOFF.md` byte-identical to its copy in `handoffs/_done/`,
  "I closed the session": removed after the recheck, which reported the match.
- The same, with `HANDOFF.md` edited after the note: kept; the recheck found no identical copy in
  `handoffs/_done/`, and the Director told David the note's path and Worktree line and the edit.
- "No session is live" after a merge given as a stand-in, for a worktree whose session never ran
  `dv:closeout`: kept, "no closeout note", with `cleanup_merged_branch` skipped.

With 0.51.0's text, the same Director kept both `not confirmed safe` worktrees it was given, by
its own caution (it read a worktree-only file and a reflog-only commit as blocking, though no
written check says so), so the lab did not reproduce the loss; this release makes the keep a rule
instead of a judgment.
