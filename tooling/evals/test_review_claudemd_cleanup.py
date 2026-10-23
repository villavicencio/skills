#!/usr/bin/env python3
"""Executes dv:review-claudemd's own Step 2 and Step 6 bash to test scratch cleanup.

Step 6 once ran `rm -rf "${TMPDIR:-/tmp}"/claudemd-review.*`, which deleted the scratch
dir of every run on the machine, including one still in its Step 3 analysis (VIL-433).
These checks run the fenced bash blocks the skill actually ships, never a copy:

  - two overlapping runs: run A's Step 6 leaves run B's dir in place
  - an aborted run's dir older than the threshold is removed
  - a fresh dir from another live run is kept, and so is an old dir with a fresh file
  - a placeholder left unsubstituted removes nothing fresh
  - the sweep still works when TMPDIR is a symlink (macOS /tmp is one)

Every run uses a throwaway TMPDIR made here, never the real one. Each block runs under
every shell present (bash, zsh) and every find present: the system find, plus GNU find
through a PATH shim when `gfind` is installed (macOS with Homebrew findutils). On the
ubuntu CI runner the system find is GNU, so CI covers GNU and a Mac covers BSD.

Stdlib only, no network. Needs jq, which Step 2 itself requires (ubuntu runners ship it).

    python3 tooling/evals/test_review_claudemd_cleanup.py [path/to/SKILL.md]

Exits non-zero on any failure. The optional path lets you prove the test is load-bearing:
point it at the pre-fix SKILL.md and it fails.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_MD = REPO_ROOT / "plugins" / "dv" / "skills" / "review-claudemd" / "SKILL.md"
PLACEHOLDER = "<scratch path printed by Step 2>"
STALE_STAMP = time.strftime("%Y%m%d%H%M", time.localtime(time.time() - 3 * 86400))

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if not ok:
        failures.append(f"{name}" + (f"\n     {detail}" if detail else ""))


def fenced_bash(md: str, heading: str) -> str:
    """Return the first ```bash block under `## <heading>`, tolerating indented fences."""
    lines = md.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(f"## {heading}")), None)
    if start is None:
        raise SystemExit(f"FAILED: no '## {heading}' section in SKILL.md")
    body: list[str] = []
    inside = False
    indent = ""
    for line in lines[start + 1:]:
        if not inside and line.startswith("## "):
            break
        m = re.match(r"^(\s*)```(\w*)\s*$", line)
        if not inside and m and m.group(2) == "bash":
            inside, indent = True, m.group(1)
            continue
        if inside and m and not m.group(2):
            return "\n".join(body) + "\n"
        if inside:
            body.append(line[len(indent):] if line.startswith(indent) else line)
    raise SystemExit(f"FAILED: no closed ```bash block under '## {heading}'")


def run(shell: str, script: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run([shell, "-c", script], env=env, capture_output=True, text=True,
                          timeout=60)


def backdate(path: Path) -> None:
    """Backdate a dir and everything in it (files first: touching them leaves the dir alone)."""
    targets = [str(p) for p in sorted(path.rglob("*"), reverse=True)] + [str(path)]
    subprocess.run(["touch", "-t", STALE_STAMP, *targets], check=True)


def make_convo_dir(root: Path) -> Path:
    convo = root / "convo"
    convo.mkdir()
    msgs = ['{"type":"user","message":{"content":"please keep tests honest"}}',
            '{"type":"assistant","message":{"content":[{"type":"text","text":"ok"}]}}']
    (convo / "old.jsonl").write_text("\n".join(msgs) + "\n")
    (convo / "live.jsonl").write_text(msgs[0] + "\n")
    os.utime(convo / "old.jsonl", (time.time() - 600, time.time() - 600))
    return convo


def step2(shell: str, script: str, env: dict[str, str], label: str) -> Path | None:
    p = run(shell, script, env)
    m = re.search(r"into: (.*claudemd-review\.\S+) ===$", p.stdout, re.M)
    if p.returncode != 0 or not m:
        failures.append(f"{label}: Step 2 did not create a scratch dir\n"
                        f"     rc={p.returncode} stdout={p.stdout!r} stderr={p.stderr!r}")
        return None
    return Path(m.group(1))


def scenario(shell: str, find_label: str, path_env: str, md: str) -> None:
    tag = f"[{shell}, {find_label} find]"
    s2 = fenced_bash(md, "Step 2")
    s6 = fenced_bash(md, "Step 6")
    check(f"{tag} Step 2 block is the one that makes the scratch dir",
          "mktemp -d" in s2 and "claudemd-review." in s2)
    check(f"{tag} Step 6 block carries the scratch-path placeholder", PLACEHOLDER in s6)

    with tempfile.TemporaryDirectory(prefix="vil433-") as work:
        root = Path(work).resolve()
        tmp = root / "tmp"
        tmp.mkdir()
        convo = make_convo_dir(root)
        env = {"PATH": path_env, "HOME": str(root), "TMPDIR": str(tmp) + "/",
               "CONVO_DIR": str(convo), "LC_ALL": "C"}

        # Two overlapping runs, both through the real Step 2.
        a = step2(shell, s2, env, f"{tag} run A")
        b = step2(shell, s2, env, f"{tag} run B")
        if a is None or b is None:
            return
        check(f"{tag} run A and run B got distinct dirs", a != b, f"{a} == {b}")
        check(f"{tag} Step 2 wrote the transcript", any(a.glob("*.txt")))

        aborted = tmp / "claudemd-review.ABORTD"         # an earlier run that died
        aborted.mkdir()
        (aborted / "old.txt").write_text("secret\n")
        backdate(aborted)
        old_fresh_file = tmp / "claudemd-review.OLDDIR"  # old dir, file rewritten recently
        old_fresh_file.mkdir()
        (old_fresh_file / "x.txt").write_text("x\n")
        backdate(old_fresh_file)
        (old_fresh_file / "x.txt").write_text("rewritten in place\n")
        bystander = tmp / "unrelated-old-dir"
        bystander.mkdir()
        backdate(bystander)

        # Run A's Step 6 while run B is mid-analysis.
        p = run(shell, s6.replace(PLACEHOLDER, str(a)), env)
        check(f"{tag} run A's Step 6 exits 0", p.returncode == 0,
              f"rc={p.returncode} stderr={p.stderr!r}")
        check(f"{tag} run A's own dir is removed", not a.exists(), p.stdout)
        check(f"{tag} run B's live dir survives run A's Step 6", b.is_dir(), p.stdout)
        check(f"{tag} run B's transcript survives too", any(b.glob("*.txt")))
        check(f"{tag} aborted dir older than the threshold is removed",
              not aborted.exists(), p.stdout)
        check(f"{tag} old dir holding a freshly rewritten file is kept",
              old_fresh_file.is_dir(), p.stdout)
        check(f"{tag} non-matching dir is untouched", bystander.is_dir())

        # An unsubstituted placeholder must remove nothing fresh.
        p = run(shell, s6, env)
        check(f"{tag} placeholder run exits 0", p.returncode == 0, p.stderr)
        check(f"{tag} placeholder run leaves run B alone", b.is_dir(), p.stdout)

        # TMPDIR as a symlink (macOS /tmp -> private/tmp): the sweep must still see in.
        link = root / "tmplink"
        link.symlink_to(tmp)
        aborted2 = tmp / "claudemd-review.ABORT2"
        aborted2.mkdir()
        backdate(aborted2)
        p = run(shell, s6.replace(PLACEHOLDER, str(b)),
                {**env, "TMPDIR": str(link)})
        check(f"{tag} run B's own Step 6 removes run B's dir", not b.exists(), p.stdout)
        check(f"{tag} stale dir is swept through a symlinked TMPDIR",
              not aborted2.exists(), p.stdout)
        check(f"{tag} the symlinked TMPDIR itself is untouched", link.is_symlink() and tmp.is_dir())


def main() -> int:
    skill = Path(sys.argv[1]) if len(sys.argv) > 1 else SKILL_MD
    md = skill.read_text()
    if not shutil.which("jq"):
        print("FAILED: jq is not installed; Step 2 needs it")
        return 1

    shells = [s for s in ("bash", "zsh") if shutil.which(s)]
    finds = [("system", os.environ.get("PATH", "/usr/bin:/bin"))]
    gfind = shutil.which("gfind")
    shim_dir = tempfile.mkdtemp(prefix="vil433-shim-")
    try:
        if gfind:
            os.symlink(gfind, os.path.join(shim_dir, "find"))
            finds.append(("GNU (gfind)", shim_dir + os.pathsep + finds[0][1]))
        for shell in shells:
            for label, path_env in finds:
                scenario(shell, label, path_env, md)
    finally:
        shutil.rmtree(shim_dir, ignore_errors=True)

    combos = len(shells) * len(finds)
    if failures:
        print(f"FAILED — {len(failures)} check(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"OK — review-claudemd scratch cleanup ({combos} shell/find combination(s): "
          f"{', '.join(shells)} x {', '.join(l for l, _ in finds)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
