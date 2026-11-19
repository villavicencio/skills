# dv — v0.11.0

Minor release. It adds one skill, `dv:groom`, and narrows `dv:ticket` to filing. The other eleven
skills have no behaviour changes; their version moves to `0.11.0` only because the suite is
released as one plugin.

## Added

### `dv:groom`: groom one Linear ticket before work starts (VIL-813)

Grooming moved out of `dv:ticket` into its own skill and does more than before:

- **Neighbors and overlap.** Reads each blocker, related ticket and named PR (at most 10) and
  reports any whose state contradicts the ticket, then runs two or three searches for unlinked
  work that already covers or overlaps a Scope step.
- **Verification with a boundary.** Verifies every fact a Scope step or Done means line depends on
  and samples the rest. It checks that each Scope target exists, that each Done means check exists
  (and proposes one when it doesn't), closes "check whether X; if so, Y" steps by running the
  read-only check, reads the code behind a deferred choice, compares current global and project
  rules with the ticket, and asks you for any numeric target instead of setting one.
- **Dependencies as relations.** A real prerequisite becomes a blocked-by relation; a worked
  example or background stays related; an unclear one is asked.
- **Size and split.** A size with the repo and PR count and one sentence of reason, and a split
  verdict: "no split" with its reason, or a proposed split with each child's title, Done means,
  order and blockers.
- **Scouting.** One capped pass (at most 5 items, 3 spin-offs) for in-ticket improvements,
  spin-off tickets and process traps such as a branch name that breaks the repo's rule.
- **Interview and approval.** Every open decision, the split and each spin-off (file, fold or
  drop) go to you in rounds of up to four questions, before any edit. An approval question names
  its item numbers, and a yes to it approves those items, replacements and removals included.
  Patches stay the default; a whole-description replacement can be offered when three or more
  sections change. Approved children and spin-offs are filed with `dv:ticket`'s File rules, except
  that the interview answer stands in for File's draft review (you can still ask to see a draft).
  A split files the children first and changes the parent last in one all-or-none save, so a
  failure part way leaves work duplicated and reported, never lost. No id is written before its
  ticket exists.

## Changed

### `dv:ticket` files; `dv:ticket groom` hands over to `dv:groom`

- `dv:ticket groom VIL-N` and plain "check this ticket" requests now hand the ticket to
  `dv:groom`. Filing is unchanged.
- The rules both skills share (where the format lives and its fallback, the interview rules,
  untrusted text, the Agent notes markers and the branch-name rule) moved into one file,
  `plugins/dv/skills/ticket/references/ticket-format.md`, which both skills read.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

A machine whose marketplace is a local checkout also pulls that checkout first; see "Linux Claude Code instances" in `README.md`.

The new version takes effect in a new session.
