# dv — v0.40.0

Minor release. The Director releases a finished worktree session's chat itself when it started
that session as a supervised Orca worker, so David no longer closes those chats in Orca. Only
`dv:director-mode` and `dv:manager-mode` change. The other fourteen skills have no behaviour
changes; their version moves to `0.40.0` only because the suite is released as one plugin.

Numbering: 0.40.0 follows 0.39.4 and carries everything released through it. It is built on
0.39.0, which routes escalations to a department's Head; where the two meet, the Head routing
wins: a session with anything still pending with the Head is not released. 0.39.1 to 0.39.4
(`dv:groom`, `dv:ticket` and `dv:closeout` fixes, among them 0.39.4's build-output fingerprint,
which director-mode's closeout recheck compares) are unchanged here.

Why: Orca 1.4.277 has no command to close an ordinary chat, but `orca orchestration
worker-release` closes a settled chat that one of its own dispatches owns. On hal on 2026-11-26 it
closed exactly that chat and left the other chat in the worktree, the workspace instance and HEAD
as they were (VIL-1156, VIL-1190).

## Changed

- **`dv:director-mode`, "Open a worktree on request", step 2.** When the Director runs in Orca,
  the session starts with `orca orchestration worker-start --worktree new-child --keep-open` (2a)
  instead of `orca worktree create --surface chat` (2b, kept as the fallback). The
  `worker-start --help` probe that chooses between them, 2a and 2b all run the same executable,
  `"${ORCA_CLI_COMMAND:-orca}"`, so the probe tests the CLI that starts the session. The start block
  starts nothing unless the prompt file was written whole: the write succeeded, and the file
  begins with the prompt's first line and ends with its supervised line. The receipt must say
  `mode: structured` and `keptOpen: true`. One setup block then links the ticket with
  `orca worktree set --linear-issue` and reads the link back, makes sure Orca keeps the chat open,
  and only when every part held writes `<git-common-dir>/orca-supervised/<dispatch id>.json`
  (schema 2, never over an existing file). From Orca's replies: the dispatch with its task and
  Run, the chat's Orca session id, its agent terminal, its mode and keep-open (`worker-show`), and
  the workspace's id, instance, identity key and path, the branch and HEAD (`orca worktree
  show`). From elsewhere: the ticket is the caller's id, kept only once Orca's read-back of the
  link matches it; the coordinator is the caller's `ORCA_AGENT_SESSION_ID`, not checked with
  Orca; the time is the local clock. It prints `RESULT: setup complete`; any other outcome writes no record, so the chat takes
  the manual close, and a `LINK: NOT LINKED` line says the worktree runs without its ticket link.
  Without `--keep-open`, Orca would close the chat about 2 minutes after the session's
  `worker_done`. Orca's mail about the worker is information, and none of it is the Head's
  answer.
- **`dv:director-mode`, kickoff prompt.** A supervised start adds one line: the worker preamble
  is Orca's default, the task asks for Manager Mode as written (its hires, and its questions
  routed to the Director, through it to the Head, and to David only where Manager Mode says so),
  and `worker_done` comes last, with nothing waiting on anyone, the Head included.
- **`dv:director-mode`, "End a finished worktree session".** A supervised session is released,
  not asked about: after checks 1 to 3, "Release a supervised Manager chat" runs in place of
  check 4 and the ask. Check 4's scan would fail on any sibling chat, which the release leaves
  running; the release block's own terminal check (below) covers what the release can end. Check 4 and the global removal checks still run in their
  removal form, on their own, before anything is removed. When check 1, 2 or 3 fails, nothing is released, asked or removed,
  as for any session; a decision still with the Head fails check 1. A newer closeout note from
  the same session replaces the earlier one for the checks and the release.
- **`dv:director-mode`, new "Release a supervised Manager chat".** One block checks, in order:
  exactly one schema 2 record, `structured` and kept open, for this worktree's path and live
  workspace instance, with the same workspace id, identity key and path, none of them empty; the
  closeout note's sender carries the record's chat id and agent terminal in the environment Orca
  set for its `claude` process (`ps -E`, three values printed, nothing else); `worker-show` names
  that dispatch with the record's task and Run, a structured chat, that chat, terminal and
  workspace, a terminal the dispatch owns, and a worker that succeeded after the note's
  timestamp (earlier is early settlement, refused); `orca agent list` lists the chat once as
  `done`, with every row naming its session; the worktree's HEAD can be read; and no terminal the
  release could also close is still open. Orca closes, with the chat, every terminal bound to the
  worker (Orca 1.4.277's server code: the worker's `worker_bound_terminals` rows): the Setup
  terminal (unless setup failed) and startup tabs the start opened, and any terminal the session's
  agent made with `orca terminal create` or `split` without `--keep-open`, in any workspace; no
  Orca command lists the latter. No check can show a live shell idle: one blocked in a builtin
  such as `read` looks like one at its prompt, and work can start after any look. So the block
  takes the start's terminals from `worker-show`'s `effects` and `residualResources`, counts every
  other terminal in `orca terminal list` (which must be whole) unless Orca's evidence shows it open
  more than 60 seconds before the dispatch's `createdAt` (its `lastOutputAt`, or the start of the
  pty process `orca diagnostics memory` names, dated by `ps`), and refuses while any terminal it
  counts is still listed; one nothing dates counts. Any of these that fails or can't run refuses
  with nothing released (exit 3). Then it runs `worker-release`
  once. `released` or `already_released` goes on; `retained` is exit 4 (not released, David
  closes the chat); any other answer, an error or a timeout is exit 5 (release attempted, outcome
  unknown). After a release it proves, with every proof required to run: the chat absent from
  `orca agent list`; `orca agent show` giving it no place, or failing with exactly
  `agent_unknown` (any other failure, a timeout or a malformed reply proves nothing); every other
  agent there still listed; every terminal listed before the release still listed;
  the workspace's id, instance, identity key and path unchanged; and the worktree's directory
  still there with HEAD where it was. It compares no worktree file. Only then does it move the record to `_released/`, never over an existing
  file, and print `RESULT: released`. A proof that fails or can't run, or an archive that would
  overwrite, is exit 5 too. Exit 3 and 4 go on to David's close; on exit 5, or no `RESULT:`
  line, the Director removes nothing and tells David what the block printed. The record's
  ticket, coordinator, branch, HEAD and time are kept for reports and not checked.
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

On hal, 2026-11-26, Orca 1.4.277, all six runs started from a session that was itself an Orca
worker, with the code blocks extracted from `SKILL.md` as it stood for that run and only the
placeholders and the record directory replaced. The first three ran the blocks as first written;
the fourth ran them after the first review fixes (start, setup and release blocks); the fifth ran
an earlier terminal check (step 5), which let a release close terminals it judged idle shells;
the sixth ran the step 5 this release ships, which refuses while any such terminal is open.

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
- **Third run, on the text after merging 0.39.3** (a fresh scratch worktree cut from main at
  394abbf; `dv:director-mode` and `dv:manager-mode` byte for byte as they stood at 77102a5, before
  the review fixes, so every code block is the one the first two runs used). Orca stored the
  kickoff spec byte for byte. The stand-in sent no `worker_done` while its first note listed a
  question pending with the Head, and said why; the block refused it (worker `ready`, dispatch not
  `completed`), and agent list, agent show, the worktree, HEAD, terminals and the sentinel read
  the same before and after. Told that everything had settled, the same stand-in sent a second
  note, read the reply to it and sent `worker_done` 12 seconds after that note. Given that note's
  timestamp, the block released the same dispatch (`released`, `closed_agent_terminal`): the chat
  left `orca agent list`, `orca agent show` gave it no place, and `GONE` passed for its wrapper
  and `claude` processes. A sibling supervised chat in the same worktree stayed listed, and the
  workspace instance, HEAD and a sentinel file of random content (inode, size, mtime and SHA-256)
  were unchanged. Check 4's removal-form scan failed on the sibling's `claude` process, so the
  worktree would have been kept.
- **Fourth run, after the MergeWren review fixes** (a fresh scratch worktree,
  `scratch-vil-1190-fix6-26b34d`, a child of the integration worktree; four stand-ins, numbered
  as under "What stood in" below). The start block passed the first stand-in's prompt to Orca
  (`structured`, `keptOpen: true`). With `orca worktree set` made to fail, the setup block printed
  `LINK: NOT LINKED` and `RESULT: setup incomplete` and wrote no record; run for real it linked
  the ticket, read the link back and wrote the schema 2 record. For the first stand-in the
  release block refused, changing nothing (agent list, workspace, HEAD, sentinel, terminals and
  both workers' states read the same before and after): while its first note had a question
  pending with the Head (worker `ready`, dispatch not `completed`); for a note sender that was the
  second stand-in's `claude` process; and, once it had settled, with `orca agent list` made to
  fail before the release (no `worker-release` call). It then released the first stand-in
  (`released`, `closed_agent_terminal`) while the second stayed listed, and released the third,
  which had read the caller's reply to its final note before `worker_done`, while the fourth,
  not yet finished, stayed listed. Each time the workspace instance, HEAD and a 64 KiB random
  sentinel (SHA-256, inode, size, mtime) were unchanged, the record moved to `_released/`, and
  `GONE` passed for the released chat's wrapper and `claude` processes; the first release also
  closed the worktree's Setup terminal, as Orca documents. For the second stand-in, released for
  real with `orca agent show` made to fail after the release, the block printed `RESULT:
  released, but …` (exit 5), kept the record in place and archived nothing, although Orca had
  closed the chat.
- **Fixtures, after the review fixes**, with a stand-in `orca` that answers from a scenario file,
  a throwaway git repository and a stand-in sender process, run in bash and zsh. The release
  block passed 36 cases: clean releases with `agent show` giving no place or `agent_unknown`;
  exit 5 when, after a release, `agent show` timed out, failed, gave another error or exit code,
  or a malformed reply, when `agent list` or `worktree show` failed or changed, when a sibling
  went missing, when HEAD moved, or when the archive file already existed (both files left as
  they were); exit 4 for `retained`; exit 5 for `release_pending`, `release_unknown` and a failed
  call; and exit 3 with no `worker-release` call for an unreadable HEAD, a missing or empty
  workspace identity on both sides, a list row with no session id, failed reads, the wrong
  sender, a schema 1 or not-kept-open record, a different Run, an unsettled worker and a
  malformed `worker-show` reply. The blocks as first written failed 17 of those cases, among them
  `RESULT: released` after a failed `agent show`, a release with no HEAD read, and an overwritten
  archive. The setup block passed 10 cases (a failed or unconfirmed link, a failed keep-open, a
  terminal-mode worker, a failed `worker-show`, a missing identity key, an existing record and a
  malformed ticket id all wrote no record), and the start block 5 (a write that failed or came
  out short, a failed `mktemp` and a prompt without its supervised line started nothing; a whole
  prompt reached `worker-start` byte for byte).
- **Fifth run, the earlier terminal check, after merging 0.39.4** (a fresh scratch worktree,
  `scratch-vil-1190-q4-383171`, a child of the integration worktree). The start and setup blocks
  ran as written. `worker-show`'s `effects` listed the Setup terminal (with its tab and pane) and
  the agent, and not the terminal the stand-in then opened without `--keep-open` (`AUX-LIVE`,
  running `while [ ! -e <stop file> ]; do sleep 1; done`). With the stand-in settled after its
  note and that loop running, the block refused with no `worker-release` call, naming `AUX-LIVE`
  (`sleep 1` in front, not a shell) and the Projects/axiom terminal Orca's older pty daemon holds
  (no process in `orca diagnostics memory`, no `lastOutputAt`); afterwards the loop's shell was
  still running, both terminals were listed, the chat was listed and the terminal still
  `retained`. With the loop ended by its stop file (no signal), real Orca refused on the axiom
  terminal alone. With that one terminal hidden, it refused, again with no `worker-release` call,
  on each injected gap: `orca diagnostics memory` failing, or naming no process for the Setup
  terminal or for `AUX-LIVE`; no `effects`; no `createdAt`; a `truncated` list; a host left out.
  With only the axiom terminal hidden it released the chat (`released`, `closed_agent_terminal`):
  Orca closed `AUX-LIVE` and the Setup terminal, both idle shells; the sibling chat stayed listed;
  the six terminals open since before the dispatch stayed listed; the workspace instance, HEAD and
  a 64 KiB random sentinel (SHA-256, inode, size, mtime) were unchanged; the record moved to
  `_released/`; `GONE` passed for the chat's wrapper and `claude` processes; and check 4's
  removal-form scan failed on the sibling's `claude` process, so the worktree would have been kept.
  That check's shell test passed a shell blocked in the builtin `read`, so the sixth run's step 5
  replaced it.
- **Sixth run, step 5 as shipped** (a fresh scratch worktree, `scratch-vil-1190-q5-af3923`, a
  child of the integration worktree; dispatch `ctx_a9ba843477c6`, sibling `ctx_c404c833ef61`). The
  start and setup blocks ran as written. The stand-in opened `AUX-READ` without `--keep-open`,
  with `read -r line; echo "READ-RETURNED:$line"` typed into its shell, and settled after its
  note. In `ps` that shell and the Setup terminal's shell at its prompt looked the same (`S+`, no
  child). **Unmodified run, real Orca and its full terminal list:** the block refused (exit 3),
  naming the Setup terminal and `AUX-READ` (each with its pty process running) and the axiom
  terminal (no process Orca names). Orca recorded no release request; the chat and both terminals
  stayed listed and both shells kept running; typing `survived` into `AUX-READ` then printed
  `READ-RETURNED:survived`. After `exit` in both shells Orca listed neither terminal, and the
  unmodified block refused on the axiom terminal alone. **Controlled run, one inventory row
  hidden:** with the axiom row hidden from `orca terminal list` by a wrapper that passed every call
  to the real Orca and changed nothing else, the block released the chat (`released`,
  `closed_agent_terminal`). The sibling chat stayed listed; Orca's full list still held all seven
  terminals right after and a minute later; the workspace's id, instance, identity key, path and
  HEAD were unchanged; the record moved to `_released/`; `GONE` passed for the chat's wrapper and
  `claude` processes; and check 4's removal-form scan failed on the sibling's `claude` process, so
  the worktree would have been kept.
- **Fixtures for step 5**, with a stand-in `orca` answering from scenario files, a throwaway git
  repository and real ptys for the live shells, on the block extracted from this text: 18 of 18
  cases as expected. It released when the start's Setup terminal was gone and every other
  terminal was dated (by `lastOutputAt`; by a pty process started at boot; or, with `orca
  diagnostics memory` failing, by `lastOutputAt` alone), and gave exit 5 after a release when an
  older terminal went missing or the terminal list after failed or was `truncated`. It refused
  with no `worker-release` call for the start's Setup terminal still open with a real `zsh` at its
  prompt; a terminal the session made whose real `zsh` sat in the builtin `read` (afterwards that
  shell was still running, and a typed line came back from the `read`); the start's pane under a
  new handle; a new terminal on another host; a row like hal's axiom terminal; two pids for one
  pty; with `orca diagnostics memory` failing, a terminal dated only by its pty process; a
  `truncated` list or a host left out; an unreadable `createdAt`; no `residualResources`; and a
  start terminal with no handle. The fifth run's block, given the same two live-shell cases,
  called `worker-release` for both, reading the shell in `read` as an idle shell. The 36 fixture
  cases above ran on the block before step 5 and were not rerun; steps 1 to 4 and the other
  proofs after a release are unchanged.

What stood in, in the second to fifth runs. The caller was a worker session in a worktree, not a
Director in the main checkout. In the second and third runs every block ran from the main
checkout; in the fourth they ran from the integration worktree, which shares its git common
directory. In the third and fourth runs the caller was the worker integrating this release, and
the workers it started joined its own coordinator's Run. The supervised session was an Orca
worker told to invoke no skill, to follow the kickoff prompt's supervised line and the quoted "A
supervised session" (in the fourth run, only its `worker_done` timing), and to take as given that
the PR had merged and `dv:closeout` had run: no real `dv:manager-mode`, grooming, PR or
`dv:closeout`. Its closeout notes were one-line stand-ins sent by `orca orchestration ask`, and
the Director's replies were `orca orchestration reply`, not SendMessage with `notify_when_idle`.
The note's timestamp was Orca's message time, not a saved copy's file name, and the `claude` pid
came from matching the chat's session id with `ps -E`, not from a `from` address, so checks 1 to
3 of "End a finished worktree session" never ran. No Head took part: "pending with the Head" was
text in the note, and "settled" was the caller's reply. Every record directory was a scratch
directory.

In the second and third runs the ticket was fake, so `orca worktree set --linear-issue` didn't
run; the sibling had no record, and after it sent `worker_done` the caller released it with a
direct `worker-release`, outside the block, as cleanup. In the third run Orca labeled the
caller's mail with the caller's own dispatch rather than its session, and the sibling held back
its "finish" once until told why.

In the fourth run the ticket id was a placeholder Linear doesn't have (`VIL-0`), which the real
`orca worktree set --linear-issue` stored. The injected failures came from a wrapper that passed
every other call to the real Orca. Four stand-ins took part. The first, held back by its pending
question, then settled, was released while the second stayed listed. The second, a supervised
sibling with its own record in a separate scratch directory, was released by the block with
`orca agent show` made to fail. The third, started in the same worktree, gave the release after
a final reply that it read, while the fourth, a sibling started without `--keep-open` that had
not yet finished, stayed listed; once told to finish, the fourth sent `worker_done` and Orca
closed it about 2 minutes later on its own. The first two sent `worker_done` before reading the
caller's reply to their last note: the caller had taken each question with `orca orchestration
check`, and Orca then told them "Your coordinator stopped without answering your question …
Decide it yourself". For the third the caller waited with `check --peek`, which left the question
open, and the stand-in read the reply before `worker_done`.

In the fifth run the ticket was again `VIL-0`, and the caller read each stand-in's question with
`check --peek`. The supervised stand-in opened its terminal on its own, as its prompt said, so
Orca bound it to that worker. The sibling was a second worker in the same worktree, started
without `--keep-open`, which waited on a question until the end and then finished and was closed
by Orca. To let the release run on hal at all, a wrapper hid one terminal from `orca terminal list`
(the Projects/axiom one, not part of the test) and passed every other call to the real Orca; the
same wrapper injected the gaps. The `claude` pid came from `ps -E` as before, and the note's
timestamp was Orca's message time.

In the sixth run the ticket was again `VIL-0`. The supervised stand-in opened its terminal on its
own, so Orca bound it to that worker, and the caller replied to its note by the message's id. The
sibling was a second worker in the same worktree, started without `--keep-open`, which waited on a
question until after the release, then finished and was closed by Orca. The caller typed the
`survived` line and both `exit` lines with `orca terminal send`. The unmodified runs used no
wrapper; in the controlled run the wrapper hid only the axiom row and injected nothing else. The
`claude` pid came from `ps -E`, and the note's timestamp was Orca's message time.

These runs are pre-merge fixtures. They don't stand in for the live check below.

## Not in this release

- Not tested: a Director in an ordinary Orca chat (whether its starts come out structured follows
  the Chat or CLI setting for new agent tabs; all six runs started from a worker session, whose
  `structured` mode may come from that lineage), a Director restarted between the start and the
  release, a session that works again after `worker_done`, and a supervised session's own mail to
  a real Head.
- A real ticket from kickoff through merge, closeout and release is checked live after this
  release ships (VIL-1043).
- Ordinary chats still need David's click: Orca has no command to close them.
- Orca 1.4.277 has no command that lists the terminals a worker made, so the release counts every
  terminal it can't show to be older than the dispatch, and refuses while any terminal it counts
  is open. A start's Setup terminal keeps a shell at its prompt, so a release refuses until that
  terminal is closed; and one Orca can't date refuses every release while it is open (on hal, the
  Projects/axiom terminal held by Orca's older pty daemon). Until then, supervised chats take
  David's close.
- A terminal the session makes in the seconds between the terminal check and the release isn't
  seen.
