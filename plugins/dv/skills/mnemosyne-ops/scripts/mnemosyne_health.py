#!/usr/bin/env python3
"""Mnemosyne health check for a Hermes profile home. Read-only. Exit 0 = healthy, 1 = drift.

    mnemosyne_health.py [--home ~/.hermes] [--json]

Checks the invariants VIL-143 established (DECISION.md §12–§13):
  config       config.yaml exists and parses
  provider     memory.provider == mnemosyne
  tools        memory.mnemosyne.tools is an explicit subset of real tool names (not the 40-tool default)
  filters      memory.mnemosyne.ignore_patterns covers Hermes-injected system turns
  patch        fixes C and D are in effect in the code this home loads (functional check: carried
               patch or upstream equivalent both pass, so an upgrade that ships the fix stays healthy)
  isolation    no other profile's bank living under this home (multiplex leak, defect D)
  override     installer's 'mnemosyne-memory-override' skill is absent
  leak         no Hermes-injected system turns stored as valid [USER] rows in the last 7 days
  freshness    last working-memory write within 48h (autosave alive)
  versions     installed (core, hermes) pair is one we have TESTED; add a pair only after a pilot run
"""
import argparse, ast, json, os, re, sqlite3, sys
from datetime import datetime, timedelta
from pathlib import Path

# (mnemosyne_memory, mnemosyne_hermes) pairs verified on this deployment. 0.7.1 on core 3.15.1 is an
# upgrade CANDIDATE (ships upstream #958 = fix D) — add it here only after a pilot run passes.
TESTED_PAIRS = {("3.15.1", "0.5.0")}
DEFAULT_SITE = Path.home() / ".hermes/venvs/mnemosyne/lib/python3.11/site-packages"
# Functional, version-agnostic checks on the provider source the wrapper loads, done on the parsed
# AST so quoting, spacing and line-wrapping can't hide a regression.
# C: upstream (#1101) mirrors MEMORY.md writes with
#        scope = "global" if target == "user" else "session"
#    Fix C is the ABSENCE of any conditional that yields the string "session" for the scope.
# D: upstream #958 binds the private DB to the per-call hermes_home by calling
#        Mnemosyne(..., db_path=private_db_path, ...)
#    Fix D is the PRESENCE of a db_path= keyword passed a name/expression involving private_db_path.
#    Our backport and upstream >=0.7.1 both contain it.


def _fix_c_broken(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "on_memory_write":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "scope" for t in sub.targets):
                    if isinstance(sub.value, ast.IfExp) and any(
                            isinstance(c, ast.Constant) and c.value == "session" for c in (sub.value.body, sub.value.orelse)):
                        return True
    return False


def _fix_d_present(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "db_path" and any(isinstance(n, ast.Name) and n.id == "private_db_path" for n in ast.walk(kw.value)):
                    return True
    return False
LEAK_SQL = [
    "[USER] [IMPORTANT: You are running as a scheduled cron job%",
    "[USER] [IMPORTANT: Background process%",
    "[USER] [IMPORTANT: _ background processes%",
    "[USER] [IMPORTANT: Watch patterns%",
    "[USER] [System note:%",
    "[USER] [ASYNC %COMPLETE%",
]
REQUIRED_FILTERS = ["scheduled cron job", "Background process", "System note", "Message from 🤖"]


def load_config(p: Path):
    """Return (config, error). A missing, unreadable or invalid config is drift, never {}."""
    if not p.exists():
        return {}, f"missing {p}"
    try:
        import yaml
    except ImportError:
        return {}, "PyYAML not importable — run with the Hermes venv python"
    try:
        cfg = yaml.safe_load(p.read_text())
    except (OSError, yaml.YAMLError) as e:
        return {}, f"unreadable/invalid YAML: {type(e).__name__}: {str(e)[:120]}"
    if not isinstance(cfg, dict):
        return {}, "config root is not a mapping"
    return cfg, None


def site_for(home: Path):
    """Return (site, error) for the side venv this home's wrapper loads. No silent fallback:
    a home without its own wrapper is drift, not evidence of an install elsewhere."""
    wrap = home / "plugins/mnemosyne/__init__.py"
    if not wrap.exists():
        return None, f"wrapper missing: {wrap}"
    m = re.search(r"^_SITE\s*=\s*['\"]([^'\"]+)['\"]", wrap.read_text(), re.M)
    if not m:
        return None, f"wrapper has no _SITE: {wrap}"
    site = Path(m.group(1))
    if not site.is_dir():
        return None, f"wrapper _SITE does not exist: {site}"
    return site, None


def known_tool_names(site):
    """Tool names from the installed catalog, or None when it cannot be read (never an empty pass)."""
    t = site / "mnemosyne_hermes/tools.py" if site else None
    if not t or not t.exists():
        return None
    names = set(re.findall(r"[\"'](mnemosyne_[a-z_]+)[\"']", t.read_text()))
    return names or None


def as_mapping(v, where: str, problems: list) -> dict:
    if v is None:
        return {}
    if not isinstance(v, dict):
        problems.append(f"{where} is {type(v).__name__}, not a mapping")
        return {}
    return v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", default=str(Path.home() / ".hermes"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    home = Path(a.home).expanduser()
    res = {}
    site, site_err = site_for(home)

    cfg, cfg_err = load_config(home / "config.yaml")
    shape = []
    mem = as_mapping(cfg.get("memory"), "memory", shape)
    mn = as_mapping(mem.get("mnemosyne"), "memory.mnemosyne", shape)
    err = cfg_err or ("; ".join(shape) if shape else None)
    res["config"] = (err is None, "ok" if err is None else err)
    prov = mem.get("provider")
    prov_ok = prov == "mnemosyne" and site_err is None
    prov_desc = "''" if prov in (None, "") else (prov if isinstance(prov, str) else f"{type(prov).__name__} {prov!r}"[:60])
    res["provider"] = (prov_ok, prov_desc + (f"; {site_err}" if site_err else ""))
    tools = mn.get("tools")
    known = known_tool_names(site)
    if not isinstance(tools, list):
        res["tools"] = (False, "unset (all 40)" if tools is None else f"not a list ({type(tools).__name__})")
    elif known is None:
        res["tools"] = (False, f"{len(tools)} tools; tool catalog unreadable — cannot validate names")
    else:
        bad = [t for t in tools if not isinstance(t, str) or t not in known]
        dup = len(tools) != len(set(map(str, tools)))
        good = bool(tools) and len(tools) < 40 and not bad and not dup
        res["tools"] = (good, f"{len(tools)} tools" + (f"; unknown {bad}" if bad else "") + ("; duplicates" if dup else ""))
    pats = mn.get("ignore_patterns")
    if pats is None:
        pats = []
    if not isinstance(pats, list) or not all(isinstance(p, str) for p in pats):
        res["filters"] = (False, f"ignore_patterns must be a list of strings (got {type(pats).__name__})")
    else:
        joined = " ".join(pats)
        missing = [k for k in REQUIRED_FILTERS if k.lower() not in joined.lower()]
        res["filters"] = (not missing, f"{len(pats)} patterns" + (f"; missing {missing}" if missing else ""))

    init = site / "mnemosyne_hermes/__init__.py" if site else None
    src = init.read_text() if init and init.exists() else ""
    if not src:
        res["patch"] = (False, "provider source not found — cannot verify fixes C/D")
    else:
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            tree = None
            res["patch"] = (False, f"provider source does not parse: {e.msg} (line {e.lineno})")
        if tree is not None:
            missing_p = (["C (MEMORY.md mirrors scoped to session)"] if _fix_c_broken(tree) else []) + \
                        ([] if _fix_d_present(tree) else ["D (bank root not bound to hermes_home)"])
            res["patch"] = (not missing_p, "fixes C+D in effect" if not missing_p else f"MISSING {missing_p} — re-apply (SKILL.md Step 4)")

    # Foreign banks under this home = another profile's memory landed here (defect D).
    banks = home / "mnemosyne/data/banks"
    own = None if home.resolve() == (Path.home() / ".hermes").resolve() else home.name
    foreign = sorted(d.name for d in banks.iterdir() if d.is_dir() and d.name != own) if banks.exists() else []
    res["isolation"] = (not foreign, "no foreign banks" if not foreign else f"foreign banks in this home: {foreign}")

    ov = home / "skills/memory/mnemosyne-memory-override"
    res["override"] = (not ov.exists(), "absent" if not ov.exists() else f"PRESENT at {ov} — remove (contradicts §7/§8)")

    vers = {}
    for name in ("mnemosyne_memory", "mnemosyne_hermes"):
        hits = sorted(site.glob(f"{name}-*.dist-info")) if site else []
        vers[name] = hits[-1].name[len(name) + 1:-len(".dist-info")] if hits else None
    pair = (vers["mnemosyne_memory"], vers["mnemosyne_hermes"])
    res["versions"] = (pair in TESTED_PAIRS, f"core={pair[0]} hermes={pair[1]}"
                       + ("" if pair in TESTED_PAIRS else " — untested pair; pilot it, then add to TESTED_PAIRS"))

    # The private bank file this home actually writes (mirrors patch D's resolution):
    # default profile -> <home>/mnemosyne/data/mnemosyne.db; named profile -> .../banks/<name>/mnemosyne.db
    is_default = home.resolve() == (Path.home() / ".hermes").resolve()
    db = (home / "mnemosyne/data/mnemosyne.db") if is_default else (home / "mnemosyne/data/banks" / home.name / "mnemosyne.db")
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
