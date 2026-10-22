# dv — v0.7.0

Minor release. It removes one skill, `dv:vps-health`. The other eleven skills have no behaviour
changes; their version moves to `0.7.0` only because the suite is released as one plugin.

## Removed

### `dv:vps-health`

The skill took a snapshot of `openclaw-prod`'s runtime over SSH. It covered systemd units, the Hermes
cron scheduler, Axiom's tmux pane, fail2ban and cold backups. That host is gone:

- hal took over every server role on 2026-10-04, and `openclaw-prod` no longer resolves from hal or the Mac.
- Axiom was retired to a Hermes profile on 2026-09-02. It runs as `hermes -p axiom --tui` on hal, not
  as `claude` in a systemd-managed tmux pane.

With nothing for it to probe, the skill could only fail, and its description still drew requests like
"how is the VPS doing?".

Rewriting it as a health check for hal would really be a new skill, because none of its probes carry
over. Running as the agent's `david` account, such a check would see only processes, `launchctl` and
ports. It could not read cron state, logs or feed files under `/Users/hal` without a sudo rule, and
`dv:mnemosyne-ops` already covers Mnemosyne health. If a hal check is wanted, it gets its own design.

The lesson the skill taught stays recorded in
`docs/solutions/conventions/verification-requires-real-execution.md`. Its paths now point at tag
`dv--v0.6.0`.

## Also in this release

- **README:** the Linux install note now says the claude CLI clone failure was last seen on
  `claude` 2.1.150 on the retired Axiom host, and was never re-checked on a current CLI.
- **AGENTS.md:** dropped "GH #8 stays open until resolved", since #8 is closed.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The update applies on the next session restart. Once it does, `dv:vps-health` no longer shows up.
