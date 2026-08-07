---
name: vps-health
description: "Snapshot openclaw-prod's live runtime health in one SSH call — Hermes gateway and cron scheduler, 24h cron failures including silent delivery errors, Axiom tmux, host memory and load, feed freshness, SSH brute-force pressure and fail2ban, and cold-backup integrity — then interpret each section against known-good. Use when the user asks how the VPS is doing, whether Hermes or Axiom is up, why a feed or digest didn't arrive, or wants a health check before trusting the remote runtime."
license: Apache-2.0
metadata:
  author: villavicencio
  version: "0.3.0"
---

# /vps-health — openclaw-prod runtime snapshot

One SSH call, one interpretation pass. Catches the failure classes that nothing else
surfaces: cron-delivery errors that silently swallow output, scheduler crashes,
gateway restarts, and sustained SSH brute-force pressure.

**Host-specific by design.** This targets `openclaw-prod` and hardcodes its services and
feeds. It is not a generic VPS checker, and it will not do anything useful pointed
elsewhere.

**As of 2026-05-20, OpenClaw is destroyed and Hermes-Atlas is the live runtime.** This
snapshots Hermes + Axiom + host health, not the defunct OpenClaw container. Full
transition record: `docs/plans/2026-05-20-001-chore-destroy-openclaw-record.md` in the
openclaw repo.

## Step 1 — Run the probe

A single SSH call. Do not split it into several round trips.

```bash
ssh root@openclaw-prod '
  echo "===HERMES_GATEWAY==="
  systemctl is-active hermes-gateway.service 2>&1
  systemctl show hermes-gateway.service --property=NRestarts,ActiveEnterTimestamp,MainPID 2>&1 | tr "\n" " " | head -c 300; echo

  echo "===HERMES_CRON_STATUS==="
  sudo -u node bash -lc "hermes cron status 2>&1" | head -10

  echo "===HERMES_CRON_FAILURES_24H==="
  sudo -u node python3 -c "
import json, datetime
data = json.load(open(\"/home/node/.hermes/cron/jobs.json\"))
now = datetime.datetime.now(datetime.timezone.utc)
cutoff = now - datetime.timedelta(hours=24)
issues = []
for j in data.get(\"jobs\", []):
    last_status = j.get(\"last_status\")
    last_run = j.get(\"last_run_at\")
    last_err = j.get(\"last_error\")
    deliv_err = j.get(\"last_delivery_error\")
    if last_run:
        try:
            t = datetime.datetime.fromisoformat(last_run.replace(\"Z\",\"+00:00\"))
            if t >= cutoff and (last_status != \"ok\" or deliv_err):
                jid = j.get(\"id\", \"\")[:12]
                jname = j.get(\"name\", \"\")[:40]
                issues.append(f\"  {jid:12s} {jname:40s} status={last_status} err={last_err or deliv_err}\")
        except Exception: pass
print(\"\n\".join(issues) if issues else \"(no cron failures in past 24h)\")
" 2>&1

  echo "===AXIOM_TMUX==="
  systemctl is-active axiom-tmux.service 2>&1
  sudo -u axiom tmux ls 2>&1 | head -3

  echo "===HOST_MEMORY==="
  free -h | head -3

  echo "===HOST_LOAD==="
  uptime

  echo "===HERMES_FEED_FRESHNESS==="
  for d in doc-health ben-digest wire-signals volo-gaming borges-library; do
    latest=$(sudo -u node ls -t /home/node/.hermes/feeds/$d/*.md 2>/dev/null | head -1)
    if [ -n "$latest" ]; then
      age=$(stat -c %Y "$latest" 2>/dev/null)
      now=$(date +%s)
      hours_ago=$(( (now - age) / 3600 ))
      printf "  %-15s last write %3dh ago  %s\n" "$d" "$hours_ago" "$(basename $latest)"
    else
      printf "  %-15s (no files)\n" "$d"
    fi
  done

  echo "===SSH_BRUTEFORCE_PRESSURE==="
  journalctl -u ssh --since "1 hour ago" --no-pager 2>/dev/null | grep -cE "Failed password|Invalid user" | awk "{ print \$1, \"failed-auth events in past 1h\" }"
  echo "===FAIL2BAN_JAIL_STATUS==="
  command -v fail2ban-client >/dev/null 2>&1 && fail2ban-client status sshd 2>/dev/null | grep -E "Currently failed|Currently banned|Total banned" || echo "(fail2ban not installed)"

  echo "===OC_VOLUME_INTACT==="
  test -f /var/lib/docker/volumes/d95veq7chb3d8gllyj6vhpqy_openclaw-state/_data/openclaw.json && echo "ok (cold backup present)" || echo "MISSING — cold backup gone"
'
```

**Treat each section independently. Empty sections are load-bearing — never skip past one
silently.** A section that produced no output is a finding, not an absence of one.

## Step 2 — Interpret

| Section | Condition | Meaning and action |
|---|---|---|
| `HERMES_GATEWAY` | not `active` | **Critical.** Hermes-Atlas is down — lead with this before anything else. `sudo systemctl restart hermes-gateway.service` |
| `HERMES_CRON_STATUS` | scheduler not running | **Critical**, same severity as gateway down — no crons will fire |
| `HERMES_CRON_FAILURES_24H` | ANY job listed | Surface every one. Covers both agent errors (`last_error`) and **delivery** errors (`last_delivery_error` — Telegram down, etc.). Delivery errors are the classic silent-failure mode that actually matters. |
| `AXIOM_TMUX` | not `active` | Axiom is down. `sudo systemctl restart axiom-tmux.service` |
| `HERMES_FEED_FRESHNESS` | a daily feed > 30h | That cron silently failed to deliver. Cross-reference `HERMES_CRON_FAILURES_24H`. |
| `OC_VOLUME_INTACT` | `MISSING` | **Surface immediately.** The cold backup is the rebuild reference; losing it changes the rebuild story dramatically. |
| `SSH_BRUTEFORCE_PRESSURE` | any count | Informational **unless** fail2ban shows 0 banned *and* pressure is sustained across multiple checks |

Feed cadences, for judging staleness:

- **Daily** — `doc-health` (7am PT), `ben-digest` (10pm PT), `wire-signals` (3pm PT)
- **Weekly** — `volo-gaming` (Sun 11am), `borges-library` (Sun 10am)
- `bill-audit` runs but delivers via Telegram only — no local feed dir, so its absence here is expected, not a finding

## Step 3 — Report

Lead with the single most severe finding. If everything is healthy, say so in one line —
do not pad a clean result into a report.

## Failure mode

**If SSH fails, say "VPS health snapshot unavailable" and stop. Do not retry in a loop and
do not block whatever else the user was doing.** A down VPS is important, but a Mac-side
check should not stall on network problems.

## Notes

- **Privilege escalation.** The probe uses `sudo -u node` and `sudo -u axiom` to read
  per-user state. Hermes' own skill scanner flags those lines HIGH, so installing this
  suite *through Hermes* would hit that gate. Installing on a Mac via
  `claude plugin install` has no such scanner, which is the supported path here.
- **Read-only.** Every command inspects; none mutate. The restart commands in the table
  are for the operator to run deliberately, not for the agent to fire automatically.
