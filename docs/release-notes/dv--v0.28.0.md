# dv — v0.28.0

Minor release. `dv:ticket` File mode records what a new ticket waits on as Linear's blocked-by
relation, not only as a line of prose. The other fifteen skills have no behaviour changes; their
version moves to `0.28.0` only because the suite is released as one plugin.

Numbering: 0.28.0 follows 0.27.0, which made `dv:pickup` and `dv:handoff` list long-running
background work.

Why: a ticket filed with a prerequisite written only in prose ("Pull when VIL-N merges") showed no
blocker in Linear, in views or to an agent reading relations, so it looked ready to start. Two
tickets filed that way on 2026-11-18 had to be corrected by hand (VIL-824).

## Changed

- **`dv:ticket`, File step 4, new "Prerequisites" bullet.** The same rules as `dv:groom` step 3,
  "Prerequisites", worded alike:
  - **Find** each place the request, or a ticket or PR it names, makes the ticket wait ("pull
    when", "wait for", "after X merges", "requires X", "blocked by", "once X lands").
  - **Check** each one's current state: `get_issue` for a ticket, and for a PR its merge state
    from `gh pr view <N> -R <owner>/<repo> --json state,mergedAt,headRefName,body`. A met
    prerequisite (the PR merged, the ticket Done) is not a blocker and the draft says so. A
    prerequisite ticket that is Canceled or a Duplicate, or one whose state can't be read, counts
    as unclear.
  - **Tell a prerequisite from a reference.** A ticket named as a worked example, background or
    related work is related, not blocking. The test: could this ticket's work start and finish
    correctly if the other were never done?
  - **Map** an unmet prerequisite to one Linear issue: a ticket directly, a PR through the ticket
    it is attached to (the ticket's attachments, or the `VIL-N` id in the PR's branch name or
    description). The draft shows "Blocked by VIL-N", with the new ticket as the waiting one. An
    open PR whose ticket is Done, Canceled or a Duplicate counts as unclear. The pull-condition
    line at the end of Why stays.
  - **Ask** before showing the draft when the dependency is unclear or maps to no issue or to
    more than one, including under "Filing without my confirmation". No relation is set on a
    guess. If the answer names no issue, the ticket waits in Backlog on its pull-condition line
    alone.
- **`dv:ticket`, File step 4, State.** A ticket is filed ready to start only when it has no
  prerequisite or every prerequisite is met.
- **`dv:ticket`, File step 6.** The draft shows the relations beside the project, state and
  labels: each "Blocked by" with its evidence, each prerequisite found already met, and each
  related ticket, with where each came from.
- **`dv:ticket`, File step 7.** Just before `save_issue`, each prerequisite is checked again with
  the same reads and mapping. A failed read saves nothing; a changed state or mapping rebuilds
  the draft and shows it again. `save_issue` then passes `blockedBy` and `relatedTo` from the
  draft, and the reply reads the relations back with `get_issue` and names any not expected.
- **`dv:ticket`, Rules.** The relations a filing sets also show on the other ticket; that is the
  only change to it.
- **`dv:ticket`, new `evals/evals.json`.** Six output-eval cases: an open ticket prerequisite, a
  PR prerequisite mapped to its ticket, a worked example that stays related, a prerequisite
  already met, an ambiguous wait that is asked first, and a Canceled prerequisite that is asked.

The format doc's "Pull condition" section in dotfiles (`docs/agents/tickets.md`) gets the same
rule for tickets filed by hand, in its own PR.

## Not tested

The output evals were run through a no-tools `claude -p` proxy for the runner (no API key is
configured), one sample per case. The live checks against Linear are listed in the PR.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
