#!/usr/bin/env python3
"""Defect-4 verification: does `memory.mnemosyne.tools` in the profile's config.yaml actually
gate what the provider exposes, when loaded through Hermes' own provider loader?

Three cases, one provider load each (fresh process per case via subprocess so config is re-read):
  A. tools = the 6-name list  -> exactly those 6 schemas, in that order; est tokens recorded
  B. tools = 6 + one typo      -> provider must fail LOUDLY (ValueError / unavailable), not expose 40
  C. tools key absent          -> all 40 (the historical default), to prove A is the config doing work

Pilot/disposable homes only. The original config.yaml bytes are restored in `finally`, even on error.
Exit 0 only if every check passes.
"""
import json, os, subprocess, sys, yaml
from pathlib import Path

HOME = Path(sys.argv[sys.argv.index("--home") + 1]) if "--home" in sys.argv else Path.home() / ".hermes/profiles/mnemosyne-pilot"
if "pilot" not in str(HOME) and "--disposable" not in sys.argv:
    sys.exit(f"refusing: {HOME} is not a pilot home (pass --disposable to override for a throwaway home)")
CFG = HOME / "config.yaml"
PY = "/home/node/.hermes/hermes-agent/venv/bin/python"
SIX = ["mnemosyne_remember", "mnemosyne_recall", "mnemosyne_invalidate",
       "mnemosyne_stats", "mnemosyne_triple_add", "mnemosyne_triple_query"]

PROBE = r'''
import json, os, sys, traceback
sys.path.insert(0, "/home/node/.hermes/hermes-agent"); os.chdir("/home/node/.hermes/hermes-agent")
out = {"loaded": False}
try:
    from plugins.memory import load_memory_provider
    prov = load_memory_provider("mnemosyne", register_skills=False)
    out["provider_is_none"] = prov is None
    if prov is not None:
        prov.initialize(session_id="tools-cfg-1", hermes_home=os.environ["HERMES_HOME"], agent_identity="mnemosyne-pilot",
                        agent_context="cli", platform="cli", agent_workspace="hermes")
        sch = prov.get_tool_schemas()
        out["loaded"] = True
        out["tool_names"] = [s["name"] for s in sch]
        out["count"] = len(sch)
        out["schema_chars"] = len(json.dumps(sch))
        out["est_tokens"] = round(len(json.dumps(sch)) / 4)
        prov.shutdown()
except Exception as e:
    out["exception_type"] = type(e).__name__
    out["exception"] = str(e)[:400]
print("__RESULT__" + json.dumps(out))
'''

def set_tools(value):
    cfg = yaml.safe_load(CFG.read_text())
    m = cfg["memory"]["mnemosyne"]
    if value is None:
        m.pop("tools", None)
    else:
        m["tools"] = value
    CFG.write_text(yaml.safe_dump(cfg, sort_keys=False))

def probe():
    env = {**os.environ, "HERMES_HOME": str(HOME), "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", "x")}
    p = subprocess.run([PY, "-c", PROBE], env=env, capture_output=True, text=True, timeout=120)
    line = [l for l in p.stdout.splitlines() if l.startswith("__RESULT__")]
    res: dict = json.loads(line[-1][len("__RESULT__"):]) if line else {"no_result": True}
    res["stderr_tail"] = p.stderr[-600:]
    return res

results, checks = {}, []
def check(ok, name, detail=""):
    checks.append({"name": name, "pass": bool(ok), "detail": detail[:300]})
    print(("PASS" if ok else "FAIL"), name, "—", detail[:200])

ORIGINAL = CFG.read_bytes()
try:
  # A
  set_tools(SIX); a = probe(); results["A_six"] = a
  check(a.get("loaded") and a.get("tool_names") == SIX, "config_tools_six_exposes_exactly_six", json.dumps({k: a.get(k) for k in ("count", "tool_names", "est_tokens")}))

  # B
  set_tools(SIX + ["mnemosyne_recal"]); b = probe(); results["B_typo"] = b
  loud = (not b.get("loaded")) and ("Unknown Mnemosyne tool" in (str(b.get("exception", "")) + str(b.get("stderr_tail", ""))) or bool(b.get("provider_is_none")))
  check(loud and b.get("count") != 40, "config_tools_typo_fails_loudly_not_silently_all", json.dumps({k: b.get(k) for k in ("loaded", "provider_is_none", "exception_type", "exception")}))

  # C
  set_tools(None); c = probe(); results["C_absent"] = c
  check(c.get("loaded") and c.get("count") == 40, "config_tools_absent_exposes_all_forty", json.dumps({k: c.get(k) for k in ("count", "est_tokens")}))

finally:
  CFG.write_bytes(ORIGINAL)
check(CFG.read_bytes() == ORIGINAL, "config_restored_byte_identical", str(CFG))

out = {"phase": "tools-config", "hermes_home": str(HOME), "results": results, "checks": checks,
       "summary": f"{sum(c['pass'] for c in checks)}/{len(checks)} checks pass"}
dest = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else Path("/dev/stdout")
dest.write_text(json.dumps(out, indent=1))
print(out["summary"])
sys.exit(0 if all(c["pass"] for c in checks) else 1)
