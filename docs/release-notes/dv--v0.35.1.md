# dv — v0.35.1

Patch release. `dv:director-mode` no longer sends a SIGTERM to end a finished worktree session.
It asks you to close that worktree's chat in Orca and removes the worktree after you say you did.
The other fifteen skills have no behaviour changes; their version moves to `0.35.1` only because
the suite is released as one plugin.

Numbering: 0.35.1 follows 0.35.0, which added the stale-state sweep at session start.

Why: on 2026-11-25 a Director sent one SIGTERM to the `orca-provider-exec` wrapper of a finished
Orca chat session after all four checks passed. A minute later the wrapper, the `claude` process
and their children were all still running. Closing the chat in the Orca app ended them, and the
worktree was then removed normally. Orca has no CLI command to close a chat (`orca --help`,
`orca agent --help` and `orca terminal --help` list none), so the Director asks.

## Changed

- **`dv:director-mode`, "End a finished worktree session".** The SIGTERM step is gone. Once the
  four checks and the global removal procedure's step 2 checks pass, the Director asks you, as
  one highlight line naming the worktree folder, to close that chat in Orca, then waits for you
  to say you did, without polling. It then runs the `GONE` check and check 4 in its removal form
  and removes the worktree only when both pass; if anything still runs it removes nothing and
  says what. "Before the signal", "Stopping it" and "After the signal" become "Before asking me to
  close it", "Asking me to close it" and "After I close it".
- **`dv:director-mode`, "Take closeout notes" and "Merge and clean up".** The Director never
  signals or stops a session's process; the one-SIGTERM exception (approved 2026-11-22) is
  removed.
- **README and plugin manifest.** The `dv:director-mode` entry and the plugin description follow
  the new rule, and the plugin table shows `0.35.1`.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
