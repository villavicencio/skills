# dv — v0.26.0

Minor release. `dv:pickup` and `dv:handoff` list the shells and agents a session left running
for a long time. The other fourteen skills have no behaviour changes; their version moves to
`0.26.0` only because the suite is released as one plugin.

Numbering: 0.26.0 follows 0.25.0, which let the caller set the model and effort of
`dv:critique`'s three agents.

Why: a session can end with a command that never returned or a wait loop with no bound, and the
only sign may be `/restart` refusing with "Can't restart while work is running in the
background" (VIL-794).

## Changed

- **`dv:pickup`, new Step 1c "Background work still running".** It lists the shells the harness
  started under the Claude Code process (a shell-list block that reads `ps`, flags any running 30
  minutes or more, skips its own shell and says so when the list can't be read) and the background agents
  this session started and that are still running (ListAgents, or the harness's task list, with
  the current session and peer sessions left out; if ownership can't be told, the list is
  reported as unverified). Anything running longer than about 30
  minutes is reported: what it is, how long it has run, and whether it waits on something that
  has already finished. The kickoff gets a new "Background work" line for these, which is never
  cut, and the numbered kickoff list shifts by one. The skill stops nothing.
- **`dv:handoff`, new Step 1c "Background work still running".** The same listing. Work running
  longer than about 30 minutes goes under "Gotchas & Watch-outs" in `HANDOFF.md`, one bullet
  each, starting "Still running when this handoff was written:". The agent list is scoped the same way. The closing reply adds a
  "Still running in the background" line. Shorter-lived work is left out, and the skill stops
  nothing.

## Not tested

The shell-list block is exercised on the host it is written for (macOS); behaviour on another
host is not covered. The rest is proved the next time `dv:pickup` or `dv:handoff` runs with
long-running work present.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
