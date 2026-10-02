#!/usr/bin/env python3
"""VIL-143 §11 runbook: enable Mnemosyne on ONE named profile with a before/after integrity gate.

    enable-profile.py --home /home/node/.hermes            --identity default [--tools 6|3] [--dry-run]
    enable-profile.py --home /home/node/.hermes/profiles/X --identity X

Steps (each prints what it did; the script stops at the first failure):
  0. integrity BEFORE: sha256 of config.yaml, memories/MEMORY.md, memories/USER.md -> records/
  1. install the wrapper plugin into <home>/plugins/mnemosyne (side venv; never touches Hermes' venv)
  2. write the §6 memory block into <home>/config.yaml via ruamel round-trip (comments preserved;
     `hermes config set` strips YAML comments - verified 2026-09-02)
  3. integrity AFTER: config.yaml MUST differ by exactly the memory block; MEMORY.md and USER.md
     MUST be byte-identical to step 0
  4. provider smoke: load through Hermes' own loader; tool list == configured subset; DB path under <home>

Rollback at any point: `hermes [-p X] memory off` (tested; DB stays), or restore the config backup
this script writes to records/.
"""
import argparse, datetime, hashlib, json, os, subprocess, sys, shutil
from pathlib import Path
from ruamel.yaml import YAML

VENV = Path("/home/node/.hermes/venvs/mnemosyne")
RECORDS = Path(os.environ.get("MNEMOSYNE_OPS_RECORDS", str(Path.home() / ".hermes/mnemosyne/records")))
RECORDS.mkdir(parents=True, exist_ok=True)
SIX = ["mnemosyne_remember", "mnemosyne_recall", "mnemosyne_invalidate",
       "mnemosyne_stats", "mnemosyne_triple_add", "mnemosyne_triple_query"]
THREE = SIX[:3]

ap = argparse.ArgumentParser()
ap.add_argument("--home", required=True)
ap.add_argument("--identity", required=True, help="profile name; 'default' for ~/.hermes")
ap.add_argument("--tools", choices=["3", "6"], default="6")
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--owner-confirmed", action="store_true",
                help="required for any profile other than default: the profile's owner (or David) is running this")
a = ap.parse_args()

HOME = Path(a.home).resolve()
CFG = HOME / "config.yaml"
FILES = [CFG, HOME / "memories" / "MEMORY.md", HOME / "memories" / "USER.md"]
TS = datetime.datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
TAG = f"{a.identity}-{TS}"
assert CFG.exists(), CFG
if a.identity != "default" and not a.owner_confirmed:
    sys.exit(f"refusing: '{a.identity}' is another profile's home; its owner enables it. Re-run with --owner-confirmed.")

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "MISSING"

def step(n, msg):
    print(f"\n== step {n}: {msg}")

# 0. integrity BEFORE
step(0, "integrity BEFORE")
before = {str(p): sha(p) for p in FILES}
for k, v in before.items():
    print(f"  {v[:16]}  {k}")
if not a.dry_run:
    (RECORDS / f"integrity-before-{TAG}.sha256").write_text("".join(f"{v}  {k}\n" for k, v in before.items()))
    shutil.copy2(CFG, RECORDS / f"config-backup-{TAG}.yaml")
    print(f"  backup -> records/config-backup-{TAG}.yaml")

# 1. wrapper install
step(1, "install wrapper plugin")
WRAP = HOME / "plugins" / "mnemosyne" / "__init__.py"
cmd = [str(VENV / "bin" / "mnemosyne-hermes"), "--hermes-home", str(HOME), "install",
       "--mode", "wrapper", "--python", str(VENV / "bin" / "python")]
if WRAP.exists() and str(VENV) in WRAP.read_text():
    print(f"  already installed and points at {VENV}; skipping (idempotent)")
elif WRAP.exists():
    sys.exit(f"refusing: {WRAP} exists but does not point at {VENV}; inspect before --force")
else:
    print("  $", " ".join(cmd))
    if not a.dry_run:
        r = subprocess.run(cmd, capture_output=True, text=True)
        print("  " + (r.stdout + r.stderr).strip().replace("\n", "\n  "))
        if r.returncode != 0:
            sys.exit(f"wrapper install failed rc={r.returncode}")
        assert WRAP.exists()

# 1b. the installer drops a skill that tells the agent MEMORY.md is deprecated — contrary to §7/§8.
SKILL = HOME / "skills" / "memory" / "mnemosyne-memory-override"
if SKILL.exists():
    if a.dry_run:
        print(f"  (dry-run) would remove installer-dropped skill {SKILL}")
    else:
        shutil.rmtree(SKILL)
        try: SKILL.parent.rmdir()
        except OSError: pass
        print(f"  removed installer-dropped skill {SKILL} (contradicts decision record §7/§8)")
else:
    print("  no installer-dropped override skill present")

# 2. config write — TEXTUAL SPLICE of the memory block only.
#    A whole-document ruamel round-trip is not byte-stable on this file (re-indents lists,
#    re-wraps long emoji strings) and the §3 gate rightly refused it three times. So: parse the
#    existing block, merge, render just that block, and splice it between the same line bounds.
step(2, f"write memory block ({a.tools}-tool subset) into {CFG}")
import io, re
yaml = YAML(); yaml.preserve_quotes = True; yaml.indent(mapping=2, sequence=4, offset=2)
old_text = CFG.read_text()
old_lines = old_text.splitlines()
# locate the top-level memory block: 'memory:' at col 0 through the last indented/blank line before the next top-level key
starts = [i for i, l in enumerate(old_lines) if l.startswith("memory:")]
assert len(starts) == 1, f"expected exactly one top-level memory: key, found {len(starts)}"
s = starts[0]; e = s + 1
while e < len(old_lines) and (old_lines[e].startswith(" ") or old_lines[e].strip() == "" or old_lines[e].lstrip().startswith("#")):
    e += 1
# trailing blank/comment lines belong to the next section, not to us
while e > s + 1 and (old_lines[e - 1].strip() == "" or old_lines[e - 1].lstrip().startswith("#")):
    e -= 1
block_text = "\n".join(old_lines[s:e]) + "\n"
mem_doc = yaml.load(block_text)
mem = mem_doc["memory"]
mem["memory_enabled"] = True
mem["user_profile_enabled"] = True
mem["provider"] = "mnemosyne"
mem["mnemosyne"] = {
    "profile_isolation": True,
    "shared_surface_read": False,
    "shared_surface_path": str(HOME / "mnemosyne" / "data" / "shared" / "mnemosyne.db"),
    "skip_contexts": "cron,flush,subagent,background,skill_loop",
    "sync_roles": ["user"],
    "auto_sleep": False,
    "reflect": False,
    "default_scope": "global",
    "tools": SIX if a.tools == "6" else THREE,
    # Hermes injects background-process / cron / system notices as user turns; keep them out.
    "ignore_patterns": [
        r"^\s*\[IMPORTANT: You are running as a scheduled cron job",
        r"^\s*\[IMPORTANT: (?:Background process|\d+ background processes|Watch patterns)",
        r"^\s*\[ASYNC (?:DELEGATION )?(?:BATCH )?COMPLETE",
        r"^\s*\[(?:CONTEXT COMPACTION|CONTEXT SUMMARY|PRIOR CONTEXT)",
        r"^\s*\[System note:",
        r"^\s*A background (?:fan-out of \d+ subagent\(s\)|subagent) you dispatched earlier has finished",
    ],
}
buf = io.StringIO(); yaml.dump(mem_doc, buf); new_block = buf.getvalue().rstrip("\n").splitlines()
new_lines = old_lines[:s] + new_block + old_lines[e:]
new_text = "\n".join(new_lines) + ("\n" if old_text.endswith("\n") else "")
print(f"  memory block lines {s+1}-{e} ({e-s} lines) -> {len(new_block)} lines; rest of file untouched")
comments_before = sum(1 for l in old_lines if l.lstrip().startswith("#"))
comments_after = sum(1 for l in new_lines if l.lstrip().startswith("#"))
print(f"  comment lines: {comments_before} -> {comments_after}")
if comments_after < comments_before:
    sys.exit("refusing: would drop comments")
if a.dry_run:
    print("  (dry-run) new memory block would be:")
    print("  " + "\n  ".join(new_block))
else:
    CFG.write_text(new_text)
    print("  written")

# 3. integrity AFTER
step(3, "integrity AFTER")
after = {str(p): sha(p) for p in FILES}
ok = True
for p in FILES:
    k = str(p); changed = before[k] != after[k]
    expect_change = (p == CFG) and not a.dry_run
    status = "changed" if changed else "identical"
    verdict = "OK" if changed == expect_change else "FAIL"
    ok &= verdict == "OK"
    print(f"  [{verdict}] {status:9s} {k}")
if not a.dry_run:
    (RECORDS / f"integrity-after-{TAG}.sha256").write_text("".join(f"{v}  {k}\n" for k, v in after.items()))
    # config diff must be confined to the memory block — checked two ways:
    #  (a) semantically: parse both and diff; only /memory/* may differ
    #  (b) textually: no +/- line outside the memory block (catches re-indentation churn)
    import difflib, yaml as _pyyaml
    _old_doc = _pyyaml.safe_load("\n".join(old_lines)) or {}
    _new_doc = _pyyaml.safe_load(new_text) or {}
    sem = [k for k in set(_old_doc) | set(_new_doc) if k != "memory" and _old_doc.get(k) != _new_doc.get(k)]
    print(f"  semantic diff outside memory: {sem or 'none'}")
    ok &= not sem
    diff = [l for l in difflib.unified_diff(old_lines, new_text.splitlines(), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
    # Lines inside the memory block (old and new): 'memory:' itself plus its indented body
    def _block(lines):
        s, inb = set(), False
        for l in lines:
            if l.startswith("memory:"): inb = True; s.add(l); continue
            if inb and (l.startswith(" ") or l.strip() == ""): s.add(l); continue
            inb = False
        return s
    mem_block = _block(new_text.splitlines()) | _block(old_lines)
    outside = [l for l in diff if l[1:] not in mem_block]
    print(f"  config diff lines: {len(diff)}; outside memory block: {len(outside)}")
    for l in outside[:10]:
        print("    ", l)
    ok &= not outside
if not ok:
    sys.exit("integrity gate FAILED — restore from records/config-backup and investigate")

# 4. provider smoke via Hermes' own loader
step(4, "provider smoke through plugins.memory.load_memory_provider")
if a.dry_run:
    print("  (dry-run) skipped")
else:
    probe = r'''
import json, os, sys
sys.path.insert(0, "/home/node/.hermes/hermes-agent"); os.chdir("/home/node/.hermes/hermes-agent")
from plugins.memory import load_memory_provider
p = load_memory_provider("mnemosyne", register_skills=False)
out = {"provider_none": p is None}
if p is not None:
    p.initialize(session_id="enable-smoke", hermes_home=os.environ["HERMES_HOME"], agent_identity=os.environ["IDENT"],
                 agent_context="cli", platform="cli", agent_workspace="hermes")
    out["tools"] = [s["name"] for s in p.get_tool_schemas()]
    out["db_path"] = str(getattr(p._beam, "db_path", ""))
    out["prompt_block_chars"] = len(p.system_prompt_block() or "")
    p.shutdown()
print("__R__" + json.dumps(out))
'''
    env = {**os.environ, "HERMES_HOME": str(HOME), "IDENT": a.identity}
    r = subprocess.run(["/home/node/.hermes/hermes-agent/venv/bin/python", "-c", probe], env=env, capture_output=True, text=True, timeout=180)
    line = [l for l in r.stdout.splitlines() if l.startswith("__R__")]
    res = json.loads(line[-1][5:]) if line else {"error": r.stderr[-800:]}
    want = SIX if a.tools == "6" else THREE
    print("  ", json.dumps(res))
    assert not res.get("provider_none"), "provider did not load"
    assert res.get("tools") == want, f"tool subset mismatch: {res.get('tools')}"
    assert res.get("db_path", "").startswith(str(HOME)), f"db not under home: {res.get('db_path')}"
    print(f"  OK: {len(want)} tools, db under {HOME}")

print(f"\nDONE {TAG}. Rollback: hermes{'' if a.identity == 'default' else ' -p ' + a.identity} memory off")
