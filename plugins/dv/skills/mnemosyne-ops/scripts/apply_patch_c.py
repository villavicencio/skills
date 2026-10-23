#!/usr/bin/env python3
"""Carried patch C: MEMORY.md mirrors are stored global, not session (upstream #1101 still open).

    apply_patch_c.py --site <side venv site-packages> [--check]

Upstream on_memory_write has   scope = "global" if target == "user" else "session"
Patch C makes it               scope = "global"  # ATLAS CARRIED PATCH C ...
Idempotent: a second run reports "already applied". Refuses if the upstream line is not there
exactly once (a release that changed or fixed it needs a human look, not a blind edit).

After applying (or with --check, without writing), it verifies the installed mnemosyne_hermes
against its wheel's RECORD hashes: every file must match, and __init__.py must match once patch C is
reversed. That proves nothing else is patched, so a retired patch (D after 0.7.1) is really gone.
Exit 0 = patch C in place and nothing else differs from the wheel.
"""
import argparse, base64, csv, hashlib, sys
from pathlib import Path

OLD = 'scope = "global" if target == "user" else "session"'
NEW = 'scope = "global"  # ATLAS CARRIED PATCH C: MEMORY.md mirrors are global, not session (upstream #1101)'

ap = argparse.ArgumentParser()
ap.add_argument("--site", required=True, help="site-packages of the side venv, e.g. ~/.hermes/venvs/mnemosyne/lib/python3.11/site-packages")
ap.add_argument("--check", action="store_true", help="verify only; write nothing")
a = ap.parse_args()
site = Path(a.site).expanduser()
init = site / "mnemosyne_hermes/__init__.py"
if not init.exists():
    sys.exit(f"FAIL: no provider source at {init}")
dists = sorted(site.glob("mnemosyne_hermes-*.dist-info"))
if len(dists) != 1:
    sys.exit(f"FAIL: expected one mnemosyne_hermes dist-info in {site}, found {[d.name for d in dists]}")

text = init.read_bytes().decode("utf-8")
if NEW in text:
    print("patch C: already applied")
elif a.check:
    sys.exit("FAIL: patch C is not applied (run without --check to apply)")
elif text.count(OLD) != 1:
    sys.exit(f"FAIL: expected the upstream scope line exactly once in {init}, found {text.count(OLD)}; inspect by hand")
else:
    init.write_bytes(text.replace(OLD, NEW).encode("utf-8"))
    print("patch C: applied")
    text = init.read_bytes().decode("utf-8")
if text.count(NEW) != 1:
    sys.exit("FAIL: patch C marker is present more than once")


def b64(algo: str, data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.new(algo, data).digest()).rstrip(b"=").decode()


bad = []
with (dists[0] / "RECORD").open(newline="") as f:
    for path, digest, _ in csv.reader(f):
        if not digest or not path.startswith("mnemosyne_hermes/"):
            continue
        algo, want = digest.split("=", 1)
        p = site / path
        if not p.exists():
            bad.append(f"{path} (missing)")
            continue
        data = text.replace(NEW, OLD).encode("utf-8") if path == "mnemosyne_hermes/__init__.py" else p.read_bytes()
        if b64(algo, data) != want:
            bad.append(path)
print(f"{dists[0].name[:-len('.dist-info')]}: files differing from the wheel besides patch C: {bad or 'none'}")
sys.exit(1 if bad else 0)
