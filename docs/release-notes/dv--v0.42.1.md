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
- **A 2a start that came up as a terminal anyway** is replaced at once, before the setup block,
  on that start's own dispatch only. The block first checks that Orca shows the receipt's worktree
  and waits, up to about two minutes, for the start's setup to finish; then
  `orca orchestration worker-stop` stops that dispatch's terminal session, and `orca agent launch --surface chat` starts the session as an ordinary chat
  in the same worktree, with the kickoff prompt without its supervised line. The chat starts only
  when `worker-stop` answered `ok`, that dispatch, `state` `stopped` and `processAction`
  `closed_agent_terminal`, and `orca terminal list`, read whole, no longer lists the agent
  terminal; otherwise nothing more starts and the Director tells David. The setup block then links
  the ticket and writes no record.
  This is the one place the Director stops a session, and only through Orca, on the dispatch it
  made in the same turn; mail from the stopped session, its "Director check" probe included, is
  information and goes unanswered.
- **2b** passes `--json` and checks that `result.launch.outcome.kind` is `structured` (a chat); any
  other answer is reported with Orca's `receipt.detail`, and that session is left for David to
  close.
- **Step 4's reply** names the start that ran (the probe's `START:` line) and, for a replaced
  terminal start, its dispatch, what `worker-stop` printed and the new chat's session id.
- **"Release a supervised Manager chat"**, the "Not tested" note: records the VIL-1043 and VIL-1206
  results and that a host whose `worker-start` takes `--surface` is not yet tested.
- **README**: the plugin table reads `0.42.1`, and the `dv:director-mode` entry and "Supervised
  worktree sessions" describe the probe, the ordinary-chat default and the terminal replacement.

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

On hal, 2026-11-26, Orca 1.4.277, with the setting for new agent tabs terminal, in a disposable
clone:

- A test Director in an ordinary Orca chat followed this text for `open worktree` on a scratch
  ticket (VIL-1210). The probe printed `START: 2b`, and `orca agent list --worktree` listed the
  worktree session with `"kind":"chat"`.
- A second test Director, with a stand-in Orca CLI whose `worker-start --help` listed
  `--surface chat|terminal` and which dropped that option before calling Orca, ran 2a on another
  scratch ticket (VIL-1211), got `"mode":"terminal"`, and followed the terminal case as it then
  stood (setup block first): the setup block linked the ticket and wrote no record, `worker-stop`
  answered `stopped` with `closed_agent_terminal` for that dispatch only (`ctx_ea59f4994150`), and
  the launch gave a chat in the same worktree. The final stop block, which runs before the setup
  block, checks the worktree, waits for setup and reads back the terminal list, was then run
  against stand-ins that replayed that `worker-stop` reply and failing answers: it launched only on
  a confirmed stop, and stopped nothing for a worktree Orca didn't show or a setup that never
  finished. The skill says plainly that the stop can cut short the session's first steps, which
  the replacement chat starts again.
