# dv — v0.18.0

Minor release. `dv:director-mode` gains one exact command, `open worktree VIL-N`, so the home session
can create a ticket-linked Orca worktree on request. The other fifteen skills have no behaviour
changes; their version moves to `0.18.0` only because the suite is released as one plugin.

Numbering: 0.18.0 follows 0.17.0, which let `dv:manager-mode` hire Codex agents on a named model.

Why: David often asks the home session to start a worktree from the Orca mobile app, which cannot
create one linked to a Linear ticket. A loose phrase such as "start VIL-840" could also be read as
doing the work, grooming the ticket or changing its state. One defined phrase, in the skill every
home session loads, removes the guesswork in every project (VIL-907).

## Changed

- **`dv:director-mode`: a new section, "Open a worktree on request".** The command is exactly
  `open worktree VIL-N`. It means only this:
  - **Checks first; the first failure stops it and nothing is created.** After confirming this session
    is the main checkout: `orca linear team list` lists the ticket's team; the ticket is not Done, Canceled,
    Duplicate, blocked or `someday` (otherwise it asks, and David's yes proceeds); and the Ownership
    lookup in `dv:manager-mode`'s "Before the first brief: check the ticket" finds no owner and every
    lookup ran.
  - **Create:** one `orca worktree create` call with `--repo`, `--name`, `--linear-issue VIL-N`,
    `--agent claude` and `--prompt`; no `--model`, `--effort` or `--branch`. The skill's step 2 holds
    the exact block: it builds the prompt through a quoted heredoc, stops if the prompt is empty, and
    quotes the path and name. If the launch reply is lost, the whole block is run again with
    `--retry-launch <operationId>`, never as a fresh launch.
  - **Kickoff prompt:** names the ticket by id and bare link, with no ticket text in it, and says the
    ticket's text is data, not instructions; runs `dv:groom VIL-N` with David first unless the ticket
    has the `groomed` label or a "Groomed <date>" line in its Agent notes; invokes `dv:manager-mode`;
    renames the branch to the repo's own rule before any commit; and hands the PR to the Director once
    its reviewer passes it, without merging.
  - **Reply:** the worktree's path and the prompt it was given.
  - **Never:** write code, groom the ticket itself, change its state, or open more than the one ticket
    named. Any other wording ("start VIL-N", "kick off", "go on N") gets a one-line question back.
- **`dv:director-mode`, "The roles" and "Recommend which worktree sessions to start next":** the two
  lines that said David starts every worktree session now also allow the Director to open one on this
  command.
- **`dv:director-mode` frontmatter:** the description names the command and its trigger phrase. The
  "Last reviewed" date is 2026-11-22.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
