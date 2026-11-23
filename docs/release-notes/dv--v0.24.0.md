# dv — v0.24.0

Minor release. `dv:manager-mode` tells the manager to brief engineers on how to wait for a
MergeWren review, to leave no background shell behind, and to stop a finished agent that is still
listed as waiting once its final report is verified. The other fifteen skills have no behaviour changes; their version moves to
`0.24.0` only because the suite is released as one plugin.

Numbering: 0.24.0 follows 0.23.0, which made `dv:director-mode` run a ticket from kickoff to
cleanup.

Why: a pilot run on VIL-807 (2026-11-19) showed engineers waiting on a reviewer in a shell the
harness moved to the background, then leaving that shell running after the PR merged.

## Changed

- **`dv:manager-mode`, "Briefing an agent".** Two lines join the brief's list.
  - **Waiting for the reviewer**, when the unit includes a MergeWren wait: run
    `mergewren_review <pr>` in the foreground with a long timeout (the command limit is 10
    minutes) and run it again if it times out, until it returns a verdict or the brief's deadline
    passes; at the deadline, report instead of waiting longer. If the harness moves the command to
    the background (after about 180 seconds), wait for that one shell and start no second copy.
  - **No shell left behind:** before its final report the engineer stops any background shell it
    started and says in the report that none is left running.
- **"A "completed" notification can be interim"** adds that an engineer waiting on a reviewer can
  send one per review round, so several on one PR are expected.
- **New: "Stop a finished agent left waiting".** If an agent is still listed as waiting on a
  shell after it has sent its final report (checked against evidence, as the "interim
  notification" rule says) and its PR has merged, the manager stops that shell and the agent
  (TaskStop) and says so in its next report to David.

## Not tested

The text is a behaviour rule for a model; it is proved on the next ticket worked under it.

## Upgrade

```bash
claude plugin marketplace update villavicencio-skills
claude plugin update dv@villavicencio-skills
```

The new version takes effect in a new session.
