#!/usr/bin/env python3
"""Mnemosyne health check for a Hermes profile home. Read-only. Exit 0 = healthy, 1 = drift.

    mnemosyne_health.py [--home ~/.hermes] [--json]

Checks the invariants VIL-143 established (DECISION.md §12–§13):
  provider     memory.provider == mnemosyne
  tools        memory.mnemosyne.tools is an explicit subset (not the 40-tool default)
  filters      memory.mnemosyne.ignore_patterns covers Hermes-injected system turns
  patch        carried patches C and D present in the side venv (re-apply after upgrades)
  isolation    no other profile's bank living under this home (multiplex leak, defect D)
  override     installer's 'mnemosyne-memory-override' skill is absent
  leak         no Hermes-injected system turns stored as valid [USER] rows in the last 7 days
  freshness    last working-memory write within 48h (autosave alive)
  versions     installed mnemosyne-memory / mnemosyne-hermes match the pins
"""
import argparse, json, os, re, sqlite3, sys
from datetime import datetime, timedelta
from pathlib import Path

PINS = {"mnemosyne_memory": "3.15.1", "mnemosyne_hermes": "0.5.0"}
VENV_SITE = Path.home() / ".hermes/venvs/mnemosyne/lib/python3.11/site-packages"
PATCH_MARKERS = {"C (MEMORY.md mirror scope)": "ATLAS CARRIED PATCH (VIL-143 defect C",
                 "D (multiplex bank root, upstream #958)": "ATLAS CARRIED PATCH (VIL-143 defect D"}
LEAK_SQL = [
    "[USER] [IMPORTANT: You are running as a scheduled cron job%",
    "[USER] [IMPORTANT: Background process%",
    "[USER] [IMPORTANT: _ background processes%",
    "[USER] [IMPORTANT: Watch patterns%",
    "[USER] [System note:%",
    "[USER] [ASYNC %COMPLETE%",
]
REQUIRED_FILTERS = ["scheduled cron job", "Background process", "System note"]


def load_yaml(p: Path) -> dict:
    try:
        import yaml
        return yaml.safe_load(p.read_text()) or {}
    except ImportError:  # minimal fallback: we only need to know the file exists
        return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", default=str(Path.home() / ".hermes"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    home = Path(a.home).expanduser()
    res = {}

    cfg = load_yaml(home / "config.yaml")
    mem = cfg.get("memory") or {}
    mn = mem.get("mnemosyne") or {}
    res["provider"] = (mem.get("provider") == "mnemosyne", mem.get("provider") or "''")
    tools = mn.get("tools")
    res["tools"] = (isinstance(tools, list) and 0 < len(tools) < 40, f"{len(tools)} tools" if isinstance(tools, list) else "unset (all 40)")
    pats = mn.get("ignore_patterns") or []
    joined = " ".join(pats)
    missing = [k for k in REQUIRED_FILTERS if k.lower() not in joined.lower()]
    res["filters"] = (not missing, f"{len(pats)} patterns" + (f"; missing {missing}" if missing else ""))

    init = VENV_SITE / "mnemosyne_hermes/__init__.py"
    src = init.read_text() if init.exists() else ""
    missing_p = [k for k, m in PATCH_MARKERS.items() if m not in src]
    res["patch"] = (not missing_p, "C+D present" if not missing_p else f"MISSING {missing_p} — re-apply (SKILL.md Step 4)")

    # Foreign banks under this home = another profile's memory landed here (defect D).
    banks = home / "mnemosyne/data/banks"
    foreign = sorted(d.name for d in banks.iterdir() if d.is_dir() and "." not in d.name) if banks.exists() else []
    if home.name != ".hermes":
        foreign = [b for b in foreign if b != home.name]
    res["isolation"] = (not foreign, "no foreign banks" if not foreign else f"foreign banks in this home: {foreign}")

    ov = home / "skills/memory/mnemosyne-memory-override"
    res["override"] = (not ov.exists(), "absent" if not ov.exists() else f"PRESENT at {ov} — remove (contradicts §7/§8)")

    vers = {}
    for name, pin in PINS.items():
        hits = sorted(VENV_SITE.glob(f"{name}-*.dist-info"))
        vers[name] = hits[-1].name[len(name) + 1:-len(".dist-info")] if hits else None
    res["versions"] = (all(vers[k] == v for k, v in PINS.items()), ", ".join(f"{k}={vers[k]}" for k in PINS))

    db = home / "mnemosyne/data/mnemosyne.db"
    if db.exists():
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        since = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        leak = 0
        for pat in LEAK_SQL:
            leak += c.execute(
                "select count(*) from working_memory where content like ? and created_at >= ? "
                "and (valid_until is null or valid_until='')", (pat, since)).fetchone()[0]
        res["leak"] = (leak == 0, f"{leak} injected system turns stored in last 7d")
        last = c.execute("select max(created_at) from working_memory").fetchone()[0]
        valid = c.execute("select count(*) from working_memory where valid_until is null or valid_until=''").fetchone()[0]
        fresh = bool(last) and datetime.utcnow() - datetime.fromisoformat(last.replace("T", " ")[:19]) < timedelta(hours=48)
        res["freshness"] = (fresh, f"last write {last} UTC; {valid} valid rows")
        c.close()
    else:
        res["leak"] = (False, f"no DB at {db}")
        res["freshness"] = (False, "no DB")

    ok = all(v[0] for v in res.values())
    if a.json:
        print(json.dumps({"healthy": ok, "checks": {k: {"ok": v[0], "detail": v[1]} for k, v in res.items()}}, indent=1))
    else:
        for k, (good, detail) in res.items():
            print(f"[{'OK  ' if good else 'FAIL'}] {k:10s} {detail}")
        print("HEALTHY" if ok else "DRIFT — see FAIL lines")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
