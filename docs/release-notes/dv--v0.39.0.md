# dv — v0.39.0

Minor release. When a project names a department Head, `dv:director-mode`, `dv:manager-mode` and
`dv:groom` send the escalations that went to David to that Head, and only the
CEO's 1% reaches David, through him, unless the Director replies `Ask David`, and apart from
`dv:closeout`'s own reply, which still asks David until VIL-1191. With no Director that can be
verified, a session sends its questions straight to the Head under their keys, as advice only,
and asks David nothing; review findings past the fix-round budget and a passed PR's merge stay
pending until a Director is verified, and the ticket's record names who resumes each.
The routing to the Head is in place, but his answers are advisory for now: A Head's mailed answer is advisory until verified Head decision delivery ships (VIL-1193). Head-only choices stay pending, and reserved choices need the person's authenticated original approval.
Two exceptions need David's explicit yes, relayed by the Head and verified by the acting session against his own words: keeping a 13-point ticket whole (`dv:groom` step 4), and creating a new milestone (`dv:groom` step 3, "Milestone"). These routing changes apply only when a project names a
Head. Three changes apply always: an answer with a short note, mail before a question card, and
a kickoff that counts a ticket as groomed only by its `groomed` label (VIL-993).
David's role is renamed from the Chairman to the CEO. The other thirteen skills have no behaviour
changes; their version moves to `0.39.0` only because the suite is released as one plugin.

Why: David wants to set direction and strategy only. On 2026-11-25 a worktree session asked him a
schedule time in a dialog, and the dialog kept the Director's reply from reaching it (VIL-1178).

## Changed

- **A Head is named by one line** in a project's `AGENTS.md` or `CLAUDE.md`, with his Orca
  address and Linear handle. This repo's names the Head of Skills.
- **`dv:director-mode`.** New section "The Head and the CEO's 1%": the one copy of the routing
  rule, the CEO's 1% and what no default decides. The Director forwards to the Head what it
  doesn't decide and relays his answers as advice; it decides the routine matters delegated to it
  as its own, taking his advice into account. Each question sent to the Head has one record on its
  ticket, keyed by the ticket, the asking session's ID and its Qk, and claimed before the send. A
  failed, unclear or interrupted send is never sent again: the record gets the Head's Linear
  mention, and the question never falls back to David.
- **`dv:manager-mode`.** With a Head, the session sends every question to the Director, keeps
  working while the Head advises, and asks David nothing outside the CEO's 1% (apart from
  `dv:closeout`'s own reply until VIL-1191), unless the Director replies `Ask David`. With no
  Director that can be verified, it sends the question straight to the Head under its key, as
  advice only; review findings past the fix-round budget and a passed PR's merge stay pending,
  with the ticket's record naming who resumes each once a Director is verified.
- **`dv:groom`.** With a Head, in forks-only mode from a worktree session, its David-only forks
  go through the Director to the Head; keeping a 13 whole and creating a new milestone still need
  David's explicit yes, which the Head relays and the session verifies against his own words.
  Anything no default decides stays a gap for the ready test, and the forks only the Head decides
  stay pending while his answers are advisory.
- **`dv:closeout`.** Unchanged apart from the version: its note reaches the
  Director as before, and with a Head the Director forwards the note's open items, the CEO's 1%
  included, to him. Closeout's own reply, delivery and Head routing are unchanged until VIL-1191.
- **Always on: an answer with a short note counts.** An `Answer` that names an offered option
  and adds a `. Note:` counts, unless the note changes what the option does.
- **Always on: mail before a question card.** A session sends its mail to the Director or the
  Head before it opens a question card, and opens none while any question to either is still
  open. With a Head, a question stays open past its 10-minute wait until an answer that counts settles it (the Head's advice doesn't),
  under the same Qk; an ask to David that falls due meanwhile goes as plain text in the chat.
- **Always on: the kickoff counts a ticket as groomed only by its `groomed` label (VIL-993).**
  `dv:director-mode`'s kickoff prompt leaves out the `dv:groom` line only for a ticket with the
  `groomed` label; a dated grooming line alone, which grooming writes on every run, no longer
  counts. Every kickoff starts the work only once `dv:groom`'s ready test passes.
- **README.** The version, and short pointers in the four skills' entries.

## Not in this release

dotfiles `docs/agents/roles.md` pointing to the new section, and the dotfiles rules that still
say a numeric target is always David's, are dotfiles changes (VIL-1036, VIL-934). How the Head
receives and answers questions may be refined later (VIL-1177).
