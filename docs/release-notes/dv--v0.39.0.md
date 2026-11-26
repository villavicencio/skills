# dv — v0.39.0

Minor release. When a project names a department Head, `dv:director-mode`, `dv:manager-mode` and
`dv:groom` send the escalations that went to David to that Head, and only the
CEO's 1% reaches David, through him, unless no Director can be verified or the Director replies
`Ask David`. These routing changes apply only when a project names a
Head. Two changes apply always: an answer with a short note, and mail before a question card.
David's role is renamed from the Chairman to the CEO. The other twelve skills have no behaviour
changes; their version moves to `0.39.0` only because the suite is released as one plugin.

Why: David wants to set direction and strategy only. On 2026-11-25 a worktree session asked him a
schedule time in a dialog, and the dialog kept the Director's reply from reaching it (VIL-1178).

## Changed

- **A Head is named by one line** in a project's `AGENTS.md` or `CLAUDE.md`. This repo's names
  the Head of Skills.
- **`dv:director-mode`.** New section "The Head and the CEO's 1%": the one copy of the routing
  rule, the CEO's 1% and what no default decides. The Director forwards to the Head what it
  doesn't decide and relays his answers.
- **`dv:manager-mode`.** With a Head, the session sends every question to the Director, keeps
  working while the Head decides, and asks David nothing outside the CEO's 1%, unless no
  Director can be verified or the Director replies `Ask David`.
- **`dv:groom`.** With a Head, in forks-only mode from a worktree session, its David-only forks
  go through the Director to the Head.
- **`dv:closeout`.** Unchanged apart from the version: its note reaches the
  Director as before, and with a Head the Director forwards the note's open items that aren't the
  CEO's 1% to him. Closeout's own Head routing comes in VIL-1191.
- **Always on: an answer with a short note counts.** An `Answer` that names an offered option
  and adds a `. Note:` counts, unless the note changes what the option does.
- **Always on: mail before a question card.** A session sends its mail to the Director or the
  Head before it opens a question card, and opens none while a question to either still waits.
- **README.** The version, and short pointers in the four skills' entries.

## Not in this release

dotfiles `docs/agents/roles.md` pointing to the new section, and the dotfiles rules that still
say a numeric target is always David's, are dotfiles changes (VIL-1036, VIL-934). How the Head
receives and answers questions may be refined later (VIL-1177).
