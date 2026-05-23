# VPS health snapshot — Step 2c of `/pickup`

Loaded by `/pickup` only when the current project targets `openclaw-prod` (detected via `git remote -v` matching "openclaw"). Captures Hermes + Axiom + host health so a degraded VPS doesn't go unnoticed for several session turns.

**As of 2026-05-20, OpenClaw is destroyed and Hermes-Atlas is the live runtime.** This step snapshots Hermes + Axiom + host health instead of the (defunct) OpenClaw container. See `docs/plans/2026-05-20-001-chore-destroy-openclaw-record.md` in the openclaw repo for the full transition.

This step is defensive — it catches classes of failure that HANDOFF.md doesn't (cron-delivery errors that silently swallow output, scheduler crashes, Hermes-gateway restarts, sustained SSH bruteforce). Without it, the session can go several turns before you notice that the VPS has been degraded the whole time.

## The probe

Run this **single SSH call** and include the resulting headline in your Step 3 synthesis:

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
                issues.append(f\"  {j[\"id\"][:12]:12s} {j[\"name\"][:40]:40s} status={last_status} err={last_err or deliv_err}\")
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

Treat each section independently — empty sections are load-bearing. Never skip past one silently.

## Interpretation rules

- **`HERMES_GATEWAY` not `active`** — Hermes-Atlas is down. This is critical; surface as the headline before anything else. Restart via `sudo systemctl restart hermes-gateway.service`.
- **`HERMES_CRON_STATUS` shows scheduler not running** — crons won't fire. Same severity as gateway down.
- **`HERMES_CRON_FAILURES_24H` lists ANY job** — surface them. The output includes both agent errors (`last_error`) and delivery errors (`last_delivery_error` — Telegram down, etc.). Delivery errors are the classic silent-failure mode the user actually cares about.
- **`AXIOM_TMUX` not `active`** — Axiom is down. Restart via `sudo systemctl restart axiom-tmux.service`.
- **`HERMES_FEED_FRESHNESS` showing a daily feed > 30h** — that cron silently failed to deliver. Cross-reference with `HERMES_CRON_FAILURES_24H`. Daily feeds: `doc-health` (7am PT), `ben-digest` (10pm PT), `wire-signals` (3pm PT). Weekly: `volo-gaming` (Sun 11am), `borges-library` (Sun 10am). Note: `bill-audit` cron exists but delivers via Telegram only — no local feed dir to track.
- **`OC_VOLUME_INTACT` missing** — the cold backup is gone. Surface immediately; the rebuild reference is the volume, so losing it changes the rebuild story dramatically.
- **SSH brute-force pressure** — informational unless fail2ban is at 0 banned + pressure is sustained over multiple `/pickup` calls.

## Failure mode

If SSH fails: note "VPS health snapshot unavailable" and continue; do not block pickup. Rationale: a down VPS is important information, but a Mac-side `/pickup` shouldn't stall on network problems.
