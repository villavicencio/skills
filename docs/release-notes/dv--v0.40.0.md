# dv — v0.40.0

Minor release. The Director releases a finished worktree session's chat itself when it started
that session as a supervised Orca worker, so David no longer closes those chats in Orca. Only
`dv:director-mode` and `dv:manager-mode` change. The other fourteen skills have no behaviour
changes; their version moves to `0.40.0` only because the suite is released as one plugin.

Numbering: 0.40.0 follows 0.39.3 and carries everything released through it. It is built on
0.39.0, which routes escalations to a department's Head; where the two meet, the Head routing
wins: a session with anything still pending with the Head is not released. 0.39.1 to 0.39.3
(`dv:groom`, `dv:ticket` and `dv:closeout` fixes) are unchanged here.

Why: Orca 1.4.277 has no command to close an ordinary chat, but `orca orchestration
worker-release` closes a settled chat that one of its own dispatches owns. On hal on 2026-11-26 it
closed exactly that chat and left the other chat in the worktree, the workspace instance and HEAD
as they were (VIL-1156, VIL-1190).

## Changed

- **`dv:director-mode`, "Open a worktree on request", step 2.** When the Director runs in Orca,
  the session starts with `orca orchestration worker-start --worktree new-child --keep-open` (2a)
  instead of `orca worktree create --surface chat` (2b, kept as the fallback). The receipt must
  say `mode: structured` and `keptOpen: true`. `orca worktree set --linear-issue` links the
  ticket, and a record block writes `<git-common-dir>/orca-supervised/<dispatch id>.json` with the
  dispatch, the chat's Orca session id, its agent terminal and the workspace's id, instance,
  path, branch and HEAD, all read from Orca. Without `--keep-open`, Orca would close the chat
  about 2 minutes after the session's `worker_done`. Orca's mail about the worker is information,
  and none of it is the Head's answer.
- **`dv:director-mode`, kickoff prompt.** A supervised start adds one line: the worker preamble
  is Orca's default, the task asks for Manager Mode as written (its hires, and its questions
  routed to the Director, through it to the Head, and to David only where Manager Mode says so),
  and `worker_done` comes last, with nothing waiting on anyone, the Head included.
- **`dv:director-mode`, "End a finished worktree session".** A supervised session is released,
  not asked about: after checks 1 to 3, "Release a supervised Manager chat" runs in place of
  check 4 and the ask. Check 4 and the global removal checks still run in their removal form
  before anything is removed. When check 1, 2 or 3 fails, nothing is released, asked or removed,
  as for any session; a decision still with the Head fails check 1. A newer closeout note from
  the same session replaces the earlier one for the checks and the release.
- **`dv:director-mode`, new "Release a supervised Manager chat".** One block checks, in order:
  exactly one record for this worktree's path and live workspace instance; the closeout note's
  sender carries the record's chat id and agent terminal in the environment Orca set for its
  `claude` process (`ps -E`, three values printed, nothing else); `worker-show` names that
  dispatch, a structured chat, that chat, terminal and workspace, a terminal the dispatch owns,
  and a worker that succeeded after the note's timestamp (earlier is early settlement, refused);
  and `orca agent list` lists the chat once as `done`. Then it runs `worker-release` once and
  proves the chat absent from `orca agent list` and `orca agent show`, every other agent there
  still listed, and the workspace instance, directory and HEAD unchanged. Exit 3 (refused), 4
  (not released) and 5 (released but a check after it failed) each fall back to David.
- **`dv:director-mode`, "The Head and the CEO's 1%".** Closing a chat stays David's only for an
  ordinary chat, or a supervised one the release doesn't close.
- **`dv:manager-mode`, new "A supervised session".** Send `worker_done` once, as the last act,
  only after the PR merged, closeout's note was sent and replied, nothing waits on David, the
  Director or the Head (a question pending with the Head, or written on the ticket as an open
  decision, still waits) and no hired agent runs. `dv:closeout`'s own offer to remove the worktree
  doesn't count as waiting, since the Director removes it. Work that ends any other way sends no
  `worker_done`, and David closes the chat; if what waited settles while the chat is open, the
  session reruns `dv:closeout`, and the new note can lead to `worker_done`. A session that works
  again after `worker_done` tells the Director, which then asks David instead of releasing.
  `orca orchestration` is for `worker_done` and, with a Head, his mail.
- **README.** The version, a paragraph on supervised worktree sessions, and the `dv:director-mode`
  entry's start command and manual close scoped to ordinary sessions.

## Tested

On hal, 2026-11-26, Orca 1.4.277, both runs started from a session that was itself an Orca
worker, with the code blocks extracted from this release's `SKILL.md` and only the placeholders
and the record directory replaced.

- **First run, before the merge with 0.39.0** (one scratch worktree). Step 2a's command gave
  `mode: structured` and `keptOpen: true`. The stand-in held custody until its closeout stand-in
  was answered, and its chat was still listed four minutes after `worker_done` with
  `autoReleaseAt` empty. The release block refused, changing nothing, for an unsettled dispatch,
  an ordinary chat as the note's sender, a worktree with no record, a dispatch Orca didn't know,
  an old workspace instance and an early settlement. It then released the stand-in: absent from
  `orca agent list` and `orca agent show`, the ordinary chat beside it still listed and running,
  the Setup terminal closed, workspace instance, HEAD and a sentinel file unchanged, `GONE` for its
  wrapper and `claude` processes.
- **Second run, on the merged text** (a fresh scratch worktree; the code blocks are byte for byte
  the ones the first run used). Step 2a passed the integrated kickoff prompt to Orca unchanged.
  A stand-in following the supervised line and "A supervised session" sent no `worker_done` while
  its note listed a question pending with the Head, and the block refused that unsettled session,
  changing nothing. Told that everything had settled, it sent a new note and then `worker_done`.
  Given the new note's timestamp, the block released it while a second supervised chat stayed
  listed in the same worktree; `GONE` passed, and check 4's removal-form scan failed on the second
  chat's `claude` process, so the worktree would have been kept.

## Not in this release

- Not tested: a Director in an ordinary Orca chat (whether its starts come out structured follows
  the Chat or CLI setting for new agent tabs; both runs started from a worker session, whose
  `structured` mode may come from that lineage), a Director restarted between the start and the
  release, a session that works again after `worker_done`, and a supervised session's own mail to
  a real Head.
- A real ticket from kickoff through merge, closeout and release is checked live after this
  release ships (VIL-1043).
- Ordinary chats still need David's click: Orca has no command to close them.
