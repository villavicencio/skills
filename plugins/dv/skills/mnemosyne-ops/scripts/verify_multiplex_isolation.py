#!/usr/bin/env python3
"""Defect-D verification: do two profile homes stay isolated inside ONE process (A -> B -> A),
the way a multiplexed `hermes serve` runs them? Also proves recall is semantic (dense_score > 0).

    verify_multiplex_isolation.py --home-a <throwaway home A> --home-b <throwaway home B> --disposable [--out FILE]

Both homes must already be enabled (enable_profile.py) and must be throwaway: the probe writes a
synthetic fact into each one's bank. One subprocess, Hermes' own loader, the process-global
HERMES_HOME pinned to A the whole time (the import-time root that defect D wrongly used):
  1. A: remember fact_A; its DB must be <A>/mnemosyne/data/banks/<A name>/mnemosyne.db
  2. B: remember fact_B; its DB must be <B>/mnemosyne/data/banks/<B name>/mnemosyne.db, NOT under A
  3. A again: recall fact_A -> found with dense_score > 0; recall fact_B -> absent, and no file
     under <A>/mnemosyne holds fact_B's token (SQLite stores text as-is, so this is exhaustive)
  4. B: recall fact_B -> found (the write really landed in B)
  5. no foreign bank directory under either home
Exit 0 only if every check passes.
"""
import argparse, json, os, subprocess, sys, uuid
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--home-a", required=True)
ap.add_argument("--home-b", required=True)
ap.add_argument("--disposable", action="store_true", help="required: both homes are throwaway and may be written to")
ap.add_argument("--out")
a = ap.parse_args()
A, B = Path(a.home_a).expanduser().resolve(), Path(a.home_b).expanduser().resolve()
live = (Path.home() / ".hermes").resolve()
if not a.disposable:
    sys.exit("refusing: pass --disposable to confirm both homes are throwaway (the probe writes to their banks)")
if A == B or live in (A, B):
    sys.exit(f"refusing: homes must be two distinct throwaway homes, not {live}")
for h in (A, B):
    if not (h / "config.yaml").exists() or not (h / "plugins/mnemosyne/__init__.py").exists():
        sys.exit(f"refusing: {h} is not enabled (no config.yaml or wrapper); run enable_profile.py on it first")

HERMES_AGENT = Path.home() / ".hermes/hermes-agent"
PY = str(HERMES_AGENT / "venv/bin/python")
tok = uuid.uuid4().hex[:8]
FACT_A = f"The lighthouse keeper on Isle {tok}A paints every door cobalt blue."
FACT_B = f"The orchard owner in Vale {tok}B grows only quince trees."

PROBE = r'''
import json, os, sys
sys.path.insert(0, os.environ["HERMES_AGENT"]); os.chdir(os.environ["HERMES_AGENT"])
from plugins.memory import load_memory_provider
out = {}
def run(step, home, ident, remember=None, recalls=()):
    p = load_memory_provider("mnemosyne", register_skills=False)
    if p is None:
        out[step] = {"error": "provider did not load"}; return
    p.initialize(session_id=f"iso-{step}", hermes_home=home, agent_identity=ident,
                 agent_context="cli", platform="cli", agent_workspace="hermes")
    r = {"db_path": str(getattr(p._beam, "db_path", ""))}
    if remember:
        r["remember"] = json.loads(p.handle_tool_call("mnemosyne_remember", {"content": remember}))
    for name, q in recalls:
        res = json.loads(p.handle_tool_call("mnemosyne_recall", {"query": q, "limit": 100})).get("results", [])
        r[name] = [{"content": x.get("content", ""), "dense_score": x.get("dense_score")} for x in res]
    p.shutdown()
    out[step] = r
E = os.environ
run("1_A", E["HOME_A"], E["IDENT_A"], remember=E["FACT_A"])
run("2_B", E["HOME_B"], E["IDENT_B"], remember=E["FACT_B"])
run("3_A", E["HOME_A"], E["IDENT_A"], recalls=[("recall_a", "Which colour does the lighthouse keeper paint the doors?"),
                                              ("recall_b", "What trees does the orchard owner grow?")])
run("4_B", E["HOME_B"], E["IDENT_B"], recalls=[("recall_b", "What trees does the orchard owner grow?")])
print("__RESULT__" + json.dumps(out))
'''

env = {**os.environ, "HERMES_HOME": str(A), "HERMES_AGENT": str(HERMES_AGENT),
       "HOME_A": str(A), "HOME_B": str(B), "IDENT_A": A.name, "IDENT_B": B.name, "FACT_A": FACT_A, "FACT_B": FACT_B}
p = subprocess.run([PY, "-c", PROBE], env=env, capture_output=True, text=True, timeout=600)
line = [l for l in p.stdout.splitlines() if l.startswith("__RESULT__")]
res = json.loads(line[-1][len("__RESULT__"):]) if line else {}

checks = []
def check(ok, name, detail=""):
    checks.append({"name": name, "pass": bool(ok), "detail": str(detail)[:300]})
    print(("PASS" if ok else "FAIL"), name, "-", str(detail)[:200])

if not res:
    check(False, "probe_produced_result", p.stderr[-600:])
else:
    want_a = A / "mnemosyne/data/banks" / A.name / "mnemosyne.db"
    want_b = B / "mnemosyne/data/banks" / B.name / "mnemosyne.db"
    for step, want in (("1_A", want_a), ("2_B", want_b), ("3_A", want_a), ("4_B", want_b)):
        got = res.get(step, {}).get("db_path") or res.get(step, {}).get("error", "")
        check(got and Path(got).resolve() == want, f"db_path_{step}", got)
    hit = lambda rows, tok_: [r for r in rows if tok_ in r["content"]]
    ra = hit(res.get("3_A", {}).get("recall_a", []), f"{tok}A")
    check(ra and (ra[0]["dense_score"] or 0) > 0, "A_recalls_own_fact_with_dense_score", ra[:1])
    check(not hit(res.get("3_A", {}).get("recall_b", []), f"{tok}B"), "A_cannot_recall_B_fact",
          [r["content"][:60] for r in res.get("3_A", {}).get("recall_b", [])])
    leaked = [str(f) for f in sorted((A / "mnemosyne").rglob("*")) if f.is_file() and f"{tok}B".encode() in f.read_bytes()]
    check(not leaked, "A_files_hold_no_B_fact", leaked)
    check(hit(res.get("4_B", {}).get("recall_b", []), f"{tok}B"), "B_recalls_own_fact",
          hit(res.get("4_B", {}).get("recall_b", []), f"{tok}B")[:1])
    for h in (A, B):
        banks = h / "mnemosyne/data/banks"
        foreign = sorted(d.name for d in banks.iterdir() if d.is_dir() and d.name != h.name) if banks.exists() else []
        check(not foreign, f"no_foreign_banks_in_{h.name}", foreign)

out = {"phase": "multiplex-isolation", "home_a": str(A), "home_b": str(B), "results": res, "checks": checks,
       "summary": f"{sum(c['pass'] for c in checks)}/{len(checks)} checks pass"}
if a.out:
    Path(a.out).write_text(json.dumps(out, indent=1))
print(out["summary"])
sys.exit(0 if checks and all(c["pass"] for c in checks) else 1)
