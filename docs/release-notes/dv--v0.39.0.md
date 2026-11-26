# dv — v0.39.0

Minor release. `dv:director-mode`, `dv:manager-mode`, `dv:groom` and `dv:closeout` route every
escalation that went to David to the department's Head, when the project has one, so only the
CEO's 1% reaches David, except when the Head can't be reached (a failed send to him) or no
Director can be verified, which fall back to asking David as before. David's role is renamed from the Chairman to the CEO. The other twelve
skills have no behaviour changes; their version moves to `0.39.0` only because the suite is
released as one plugin.

Why: David wants to set direction and strategy only. On 2026-11-25 a worktree session asked him a
schedule time in a dialog, and the dialog kept the Director's reply from reaching it (VIL-1178).

## Changed

- **A Head is configured by one line.** A project has a Head when its `AGENTS.md` or `CLAUDE.md`
  has a line that starts `Head:` and names him and his Orca address (`bot:<name>`). With no such
  line, every skill behaves as in 0.38.0, except that an `Answer` with a `. Note:` now counts
  (below). This repo's `AGENTS.md` names the Head of Skills,
  `bot:Head of Skills`.
- **`dv:director-mode`, new section "The Head and the CEO's 1%".** The one copy of the routing
  rule and of the five items that still reach David, which the Head brings to him collected. With a
  Head, the Director forwards each question it doesn't decide, the CEO's 1% included, to him with
  `orca orchestration send --to "<address>" --chat new --type question`, replies
  `Forwarded to the Head, VIL-N, Qk: <the way forward>`, relays his answer to the session as
  `Answer from the Head, VIL-N, Qk: <option>` (at once, when he has already answered), and for a question still unanswered when the
  session's other work is done takes the session's recommended option. A failed send counts as
  the Head unreachable and falls back to asking David. `dv:groom`'s split, target, pull-condition
  and new-milestone forks go to the Head; the Director no longer replies `Ask David` to them when
  a Head is configured. Held items, closeout `WAITING ON` decisions and `REPLY NEEDED` questions
  route the same way. "Held for me, the Chairman" now reads "the CEO".
- **`dv:manager-mode`, "Questions go to the Director first".** New "With a Head" rules: every
  question goes to the Director; a forwarded question never blocks (the session takes the way
  forward and applies the Head's answer when it arrives); no answer in time leads to a way
  forward, not to David; the CEO's 1% comes back as `Forwarded to the Head` and is not asked at
  the end (a `Held for David` now means the send to the Head failed, and is asked as before); and
  a question still unanswered when the other work is done is sent to the Director as
  `Unanswered, VIL-N, Qk: …`, which takes the recommended option except for the CEO's 1% and a
  decline of a high or critical finding on a safety boundary, which no default decides. The question
  message lists the new `Answer from the Head` and `Forwarded to the Head` replies. The PR-body
  record gains the Head's form.
- **An answer with a short note counts** (`dv:manager-mode`, "What counts as the answer", and
  `dv:groom`'s forks-only Director rule), with or without a Head: an `Answer` that names an
  offered option and adds a note (a wording note, say) is an answer, not "ask David", unless the
  note changes what the option does. A reply that relays the Head's decision counts too, even
  when it is not the session's recommended option.
- **`dv:groom`, forks-only mode.** With a Head, the four David-only forks go to the Director and on
  to the Head, are recorded in a Head form, and a fork on its way forward is not a gap for the
  ready test. With none, they go to David as before.
- **`dv:closeout`.** With a Head, the note's `WAITING ON` names him (the CEO's 1% marked), and the
  reply asks David nothing: losses to accept go under `WAITING ON`, no removal offer is made, and
  **Needs you** is left out.
- **Mail before a card, always** (`dv:manager-mode`, pointed to from `dv:groom`,
  `dv:director-mode` and `dv:closeout`). An open question card blocks the session's turn, Orca
  cannot answer or dismiss it, and mail queues behind it. So a session sends its mail to the
  Director or the Head before opening a card in the same turn, and opens none while a question to
  the Director or the Head still waits. With a Head, the CEO's 1% goes by mail, never in a card.
- **README.** The version, and the `dv:director-mode`, `dv:manager-mode`, `dv:groom` and
  `dv:closeout` entries.

## Not in this release

dotfiles `docs/agents/roles.md` pointing to the new section, and the dotfiles rules that still
say a numeric target is always David's, are dotfiles changes (VIL-1036, VIL-934). How the Head
receives and answers questions may be refined later (VIL-1177).
