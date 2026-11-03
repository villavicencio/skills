#!/usr/bin/env python3
"""Verify mnemosyne_health.py's `freshness` check on disposable homes (VIL-535). Touches no real home.

    verify_freshness_check.py          # needs PyYAML; the Hermes venv python has it

Each case builds a throwaway profile home holding a Mnemosyne bank and a Hermes state.db, runs the
health check with --json, and asserts only the `freshness` result (the other checks fail on a fake
home by design). Exit 0 when every case matches.
"""
import json, sqlite3, subprocess, sys, tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HEALTH = Path(__file__).with_name("mnemosyne_health.py")
# Half a second past the second, so a turn and its autosave share a second deterministically.
NOW = datetime.now(timezone.utc).replace(microsecond=500000)
FILTERS = ["scheduled cron job", "Background process", "System note", "Message from 🤖"]


def ts(hours_ago: float) -> str:
    return (NOW - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")


def ep(hours_ago: float) -> float:
    return (NOW - timedelta(hours=hours_ago)).timestamp()


def build(root: Path, name: str, writes, turns, state_db=True, extra_patterns=()) -> Path:
    """writes: [(hours_ago, source)] memory rows. turns: [(hours_ago, session_source, text)] user turns."""
    home = root / name
    bank = home / "mnemosyne/data/banks" / name
    bank.mkdir(parents=True)
    (home / "config.yaml").write_text(
        "memory:\n  provider: mnemosyne\n  mnemosyne:\n    ignore_patterns:\n"
        + "".join(f"    - {json.dumps(f)}\n" for f in [*FILTERS, *extra_patterns]))
    m = sqlite3.connect(bank / "mnemosyne.db")
    m.execute("create table working_memory (content text, created_at text, valid_until text, source text)")
    m.executemany("insert into working_memory values (?, ?, null, ?)",
                  [(f"[USER] row {i}", ts(h), src) for i, (h, src) in enumerate(writes)])
    m.commit(); m.close()
    if state_db:
        s = sqlite3.connect(home / "state.db")
        s.execute("create table sessions (id text primary key, source text not null)")
        s.execute("create table messages (id integer primary key, session_id text, role text, content text, timestamp real)")
        for i, (h, src, text) in enumerate(turns):
            s.execute("insert into sessions values (?, ?)", (f"s{i}", src))
            s.execute("insert into messages (session_id, role, content, timestamp) values (?, 'user', ?, ?)", (f"s{i}", text, ep(h)))
            s.execute("insert into messages (session_id, role, content, timestamp) values (?, 'assistant', 'reply text here', ?)", (f"s{i}", ep(h)))
        s.commit(); s.close()
    return home


CASES = [
    # (name, writes, turns, state_db, expect_ok, why)
    ("quiet", [(120, "conversation")], [(121, "slack", "hello atlas, how are you")], True, True,
     "no conversation for 5 days and a working provider: HEALTHY (the VIL-535 false alarm)"),
    ("dead", [(120, "conversation")], [(72, "slack", "please remember the gate code")], True, False,
     "a real turn 3 days ago that autosave never stored: FAIL"),
    ("noise", [(120, "conversation")],
     [(72, "cron", "run the daily check-in"),
      (60, "subagent", "child task prompt text"),
      (50, "cli", "[IMPORTANT: Background process 123 finished]"),
      (40, "cli", "[System note: context compacted]"),
      (30, "cli", "ok")], True, True,
     "cron, subagent, filtered system turns and a <=5-char reply are not expected to be stored"),
    ("inflight", [(120, "conversation")], [(0.25, "tui", "long task started a few minutes ago")], True, True,
     "a turn younger than the grace window may still be in flight"),
    ("mirror-masks", [(120, "conversation"), (1, "builtin_memory_user")], [(72, "slack", "remember my flight number")], True, False,
     "a later MEMORY.md mirror row doesn't hide an unstored conversation turn"),
    ("stored", [(71.9, "conversation")], [(72, "slack", "remember my flight number")], True, True,
     "a turn followed by its autosave row is fine"),
    ("fallback-old", [(120, "conversation")], [], False, False,
     "no state.db: falls back to the 48h age rule, which FAILs here and says why"),
    ("fallback-new", [(3, "conversation")], [], False, True,
     "no state.db and a recent write: the age rule passes"),
    ("empty", [], [(72, "slack", "anyone home?")], True, False,
     "no working_memory rows at all: FAIL"),
    ("same-second", [(72, "conversation")], [(72, "slack", "remember the gate code")], True, True,
     "a turn and its autosave in the same second (row truncated to the second) is stored, not missing"),
    ("odd-pattern", [(120, "conversation")], [(72, "slack", "please remember the gate code")], True, False,
     "a non-string ignore_patterns entry doesn't crash the check; the unstored turn still FAILs",
     (123,)),
]


def main() -> int:
    failed = 0
    with tempfile.TemporaryDirectory(prefix="mn-fresh-") as tmp:
        for name, writes, turns, state_db, expect, why, *extra in CASES:
            home = build(Path(tmp), name, writes, turns, state_db, *extra)
            out = subprocess.run([sys.executable, str(HEALTH), "--home", str(home), "--json"],
                                 capture_output=True, text=True)
            try:
                got = json.loads(out.stdout)["checks"]["freshness"]
            except (ValueError, KeyError) as e:
                print(f"[FAIL] {name}: no freshness result ({type(e).__name__}); stderr: {out.stderr.strip()[-300:]}")
                failed += 1
                continue
            good = got["ok"] is expect
            failed += not good
            print(f"[{'OK  ' if good else 'FAIL'}] {name:13s} expect {'ok' if expect else 'FAIL'}, got "
                  f"{'ok' if got['ok'] else 'FAIL'}: {got['detail']}\n       {why}")
    print("ALL PASS" if not failed else f"{failed} case(s) failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
