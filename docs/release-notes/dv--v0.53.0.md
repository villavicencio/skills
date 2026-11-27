# dv — v0.53.0

Minor release. `dv:director-mode` now reads a finished worktree's latest `dv:closeout` note
before it removes the worktree after the worktree's session has ended, however the session
ended. It removes the worktree, by the global removal procedure as before, only when that note's
Worktree line passes check 1's verdict rule under "End a finished worktree session" (it starts
`Worktree: safe to delete,`, or `Worktree: safe once you accept losing:` with every listed loss
covered by a standing yes of David's). Otherwise (`NOT safe to delete`, `not confirmed safe`, a loss no standing yes
covers, or no note it can read) it keeps the worktree and its branch and tells David the note's
path and its Worktree line word for word, or that there is no note. The note can only keep a
worktree; it never permits a removal the global procedure's checks refuse. `dv:closeout` and the
README drop the known limit this fixes. The other fourteen skills have no behaviour changes; their
version moves to `0.53.0` only because the suite is released as one plugin.

Numbering: 0.53.0 follows 0.52.0, which skills PR 132 holds and which merges first; the version is
picked again at the merge if that changes.

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
  keeps the worktree unless its Worktree line passes check 1's verdict rule. The latest note is
  the newest copy saved for the worktree's branch under `<git-common-dir>/closeouts/`, named
  exactly `<branch slug>.<YYYYMMDDTHHMMSSZ>.txt` or `…-<n>.txt` on a clash: the latest timestamp,
  then the highest `<n>` compared as a number, not by `ls` or `sort` order (the slug is the branch
  name as closeout's Step 3 block writes it). A copy whose header names another worktree path
  counts as no note.
- **`dv:director-mode`, "End a finished worktree session", the `GONE` path.** A session found
  already ended skips the ask and that rule's checks, except that the Director applies check 1's
  verdict rule to the worktree's latest closeout note, as "Take closeout notes" says: keep the
  worktree and tell David why when the note fails the rule or there is no note it can read;
  otherwise remove it by the global procedure with check 4 in its removal form.
- **`dv:director-mode`, "Merge and clean up".** The bullet that leaves a worktree in place until
  its session has ended now says that, once a session whose closeout note reached the Director
  has ended, that worktree's latest note can keep it; a note is still not permission to delete.
- **`dv:closeout`, Step 3 ("The note follows Step 4") and Step 5 ("The probe's peer has the
  note"), and the README's `dv:closeout` entry.** The known limit "if the session ends another
  way, the Director's later removal does not read the note" is replaced by what the Director now
  does.

## Not in this release

- The stale-PR repair's temporary worktree and the "No session is live" cleanup under "Merge and
  clean up": neither has a worktree session's closeout note, and their removal is unchanged.
- The "losses I accepted before the note" wording in the "Take closeout notes" bullet before this
  one (VIL-1263 owns it).
- A live run of the `GONE` path: the lab run (skills PR for VIL-1209) covers the "closed by me"
  path; the `GONE` path is checked by reading only.
