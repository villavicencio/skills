# dv — v0.42.1

Patch release. `dv:director-mode`'s "Open a worktree on request" starts a ticket's worktree session
as a supervised Orca worker only when Orca can show, before anything is created, that the worker
will be a chat; everywhere else it opens an ordinary chat, which David closes. Only
`dv:director-mode` changes. The other fifteen skills have no behaviour changes; their version moves
to `0.42.1` only because the suite is released as one plugin.

Numbering: 0.42.1 comes after 0.41.0 (VIL-1169) and leaves 0.42.0 to the open VIL-932 change, planned to merge first.

Why: `orca orchestration worker-start` starts its agent as a chat or a terminal by the user's
setting for new agent tabs, and has no option to choose. On hal that setting is terminal, so the
first live run of the supervised start (VIL-1043, 2026-11-26) got a terminal session: its setup
block wrote no record, and the session could be neither released nor closed through the
Director's checks. No supported Orca command reads that setting (Orca 1.4.277).

## Changed

- **`dv:director-mode`, "Open a worktree on request", step 2.** A read-only probe runs first and
  prints `START: 2a` or `START: 2b`. The supervised start (2a) needs the session to run in Orca and
  `worker-start --help` to list `--keep-open` and a `--surface chat|terminal` option, which 2a then
  passes as `--surface chat`. Orca 1.4.277 has no such option, so every start there takes the
  ordinary start (2b) for now. Don't read Orca's settings files to decide.
- **A 2a start that came up as a terminal anyway** is reported and left for David. The Director
  doesn't stop it, release it or send it anything about its start, and starts nothing more for the
  ticket. The setup block still runs, so the ticket gets linked; it writes no record. Step 4 says
  the session is a terminal that David closes, with its dispatch id and Orca's
  `startOptions.mode.detail` reason.
- **2b** passes `--json` and checks that `result.launch.outcome.kind` is `structured` (a chat); any
  other answer is reported with Orca's `receipt.detail`, and that session is left for David to
  close.
- **Step 4's reply** names the start that ran (the probe's `START:` line) and, for a 2a start that
  came up as a terminal, that David closes it, with its dispatch id.
- **"Release a supervised Manager chat"**, the "Not tested" note: records the VIL-1043 and VIL-1206
  results and that a host whose `worker-start` takes `--surface` is not yet tested.
- **README**: the plugin table reads `0.42.1`, and the `dv:director-mode` entry and "Supervised
  worktree sessions" describe the probe, the ordinary-chat default, and that a terminal start is
  reported and left for David.

## Tried and not used

Creating the chat first with `orca worktree create --surface chat` and handing it the task with
`orca orchestration worker-start --terminal orca_session_id:<chat session id> --keep-open`. Orca
accepts that, and the chat gets the task with Orca's worker preamble and settles on its
`worker_done`. But Orca records the chat as an external resource (`"mode":"terminal"`, reason
`user_default`, no `processIncarnation`, `ownershipState` `external`) and never closes it:
`worker-release` answers `retained` with `processAction` `none`, with or without `--keep-open`,
and no automatic release is scheduled. Such a chat would still need David's close, like an ordinary
one. The receipt's own handle, `structured-agent-session-<id>`, is refused (`terminal_handle_stale`).
Live probe on hal, Orca 1.4.277, 2026-11-26: scratch ticket VIL-1208, dispatches `ctx_b56e7bf263a8`
and `ctx_fba11a16b2b1`.

Missing Orca contract: for a supervised chat the Director can release, `worker-start` would need to
start an owned structured chat on request (a surface choice), or `--terminal` would need to take
ownership of a chat Orca started, so that `worker-release` closes it.

## Checked live

On hal, 2026-11-26, Orca 1.4.277, with the setting for new agent tabs terminal, in disposable
clones:

- A test Director in an ordinary Orca chat followed this text for `open worktree` on a scratch
  ticket (VIL-1210). The probe printed `START: 2b`, and `orca agent list --worktree` listed the
  worktree session with `"kind":"chat"`.
- A second test Director ran headless (`claude -p`) in another disposable clone, with a stand-in
  Orca CLI that never called Orca: its `worker-start --help` added a `--surface chat|terminal`
  line, and it answered the start, `worker-show` and `worktree set`/`show` with replies saved from
  a real terminal start (ids rewritten), on scratch ticket VIL-1211. The probe printed
  `START: 2a`, the start passed `--surface chat` and got `"mode":"terminal"`, and the Director ran
  the setup block (it printed the replayed `LINK: VIL-1211 linked …` and wrote no record) and reported the session as a terminal
  for David to close, with its dispatch id and the `startOptions.mode.detail` reason. Its call log
  has no `worker-stop`, `worker-release`, send or launch.
