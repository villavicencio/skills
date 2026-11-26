# dv — v0.40.0

Minor release. The Director releases a finished worktree session's chat itself when it started
that session as a supervised Orca worker, so David no longer closes those chats in Orca. Only
`dv:director-mode` and `dv:manager-mode` change. The other fourteen skills have no behaviour
changes; their version moves to `0.40.0` only because the suite is released as one plugin.

Numbering: 0.40.0 follows 0.39.0, which routes escalations to a department's Head. The two
releases change different parts of `dv:director-mode` and `dv:manager-mode`.

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
  about 2 minutes after the session's `worker_done`.
- **`dv:director-mode`, kickoff prompt.** A supervised start adds one line: the worker preamble
  is Orca's default, the task asks for Manager Mode with its hires and its questions to David, and
  `worker_done` comes last.
- **`dv:director-mode`, "End a finished worktree session".** A supervised session is released,
  not asked about: after checks 1 to 3, "Release a supervised Manager chat" runs in place of
  check 4 and the ask. Check 4 and the global removal checks still run in their removal form
  before anything is removed.
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
- **`dv:manager-mode`, new "A supervised session".** Send `worker_done` once, as the last act,
  only after the PR merged, closeout's note was sent and replied, nothing waits on anyone and no
  hired agent runs. Work that ends any other way sends no `worker_done`, and David closes the
  chat. A session that works again after `worker_done` tells the Director, which then asks David
  instead of releasing.
- **README.** The version, and a paragraph on supervised worktree sessions.

## Tested

On hal, 2026-11-26, Orca 1.4.277, with disposable fixtures in one scratch worktree, started from a
session that was itself an Orca worker. Step 2a's command gave `mode: structured` and
`keptOpen: true`. The stand-in held custody until its closeout stand-in was answered, and its chat
was still listed four minutes after `worker_done` with `autoReleaseAt` empty. The release block
refused, changing nothing, for an unsettled dispatch, an ordinary chat as the note's sender, a
worktree with no record, a dispatch Orca didn't know, an old workspace instance and an early
settlement. It then released the stand-in: absent from `orca agent list` and `orca agent show`,
the ordinary chat beside it still listed and running, the Setup terminal closed, workspace
instance, HEAD and a sentinel file unchanged, `GONE` for its wrapper and `claude` processes. The
code blocks run were extracted from this release's `SKILL.md`, with only the placeholders and the
record directory replaced.

## Not in this release

- Not tested: a Director in an ordinary Orca chat (whether its starts come out structured follows
  the Chat or CLI setting for new agent tabs), a Director restarted between the start and the
  release, and a session that works again after `worker_done`.
- A real ticket from kickoff through merge, closeout and release is checked live after this
  release ships (VIL-1043).
- Ordinary chats still need David's click: Orca has no command to close them.
