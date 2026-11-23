# dv — v0.21.0

Minor release. `dv:groom` gains a forks-only mode: it decides routine calls itself, asks David only
about real forks, applies its edits without the approval question, and records what it decided so
he can overrule it. Without the argument, grooming works as before. The other fifteen skills have
no behaviour changes, except the `dv:ticket groom` hand-off below; their version moves to `0.21.0`
only because the suite is released as one plugin.

Numbering: 0.21.0 follows 0.20.0, which let worktree sessions handle routine PR work without
asking. This release was first numbered 0.20.0; both changes took that number, so this one moved up.

Why: grooming is where a worktree session spends most of David's attention, and the interview
asked him every open decision, routine ones included. He chose to have sessions make the routine
calls and ask only the forks (VIL-915).

## Added

- **`dv:groom VIL-N forks-only`.** A new "Forks-only mode" section, and a marked paragraph in each
  step it changes (Before anything else items 5 and 6, steps 4, 6, 7 and 8, and Rules). Nothing in
  them applies without the argument.
  - **Forks, which are asked:** a change to scope or Out of scope (a Scope step added or removed,
    a Done means line dropped), a design choice between real alternatives (including rules that
    conflict), anything destructive or hard to undo, a target or pull condition only David can
    supply, a split, and a prerequisite that cannot be mapped to one issue. When it cannot tell, the
    call is a fork.
  - **Routine calls, which it decides:** wording, ordering, Size, Done means phrasing, filing,
    folding or dropping a spin-off, settling a verified `[assumed]` marker, a clearly mapped
    relation, a conditional step closed (removed or made unconditional), and a Done means line
    reworded or added that proves the existing scope. It takes the option it would have marked
    "(Recommended)". A spin-off whose duplicate search found an open or Done match that covers the
    work is dropped, not filed, and the match is named; any other match, it files. With no forks,
    it asks nothing.
  - **No approval question in step 7.** It shows the numbered edit list and applies it. The order
    of writes, the re-reads before a split and the patch rules still hold. A split stays a question,
    and its approval covers the children and the parent's change. The whole-description
    replacement is not offered, since it needs its own question, and a description with text but
    no headings is left alone, with the sections it would add shown in the report.
  - **Recorded so it can be overruled.** Each routine call is a Decisions line, "<decision>.
    Decided by dv:groom (forks-only), <date>"; forks keep "<decision>. <name>, <date>". The "no
    split" line takes the same form. A ticket that needs no edits gets no Decisions lines; its
    routine calls are only listed in the report. A routine call that settles a Decisions line
    marked open replaces that line. The Rules line "Nothing is created or edited in Linear before I
    approve it" names the exception.
  - **The report** lists each edit as written and ends with a "Decided without asking" list, one
    line per routine call.
- **Description, README and manifest** name the mode.

## Changed

- **`dv:ticket`, "Groom":** the hand-off passes the rest of the arguments to `dv:groom` as given,
  so `dv:ticket groom VIL-N forks-only` keeps `forks-only`. It passed only the ticket id or link.

## Not changed

- Where the mode is turned on (`dv:director-mode`'s kickoff prompt) is a separate ticket.
- What counts as groomed, and the `groomed` label, are untouched.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
