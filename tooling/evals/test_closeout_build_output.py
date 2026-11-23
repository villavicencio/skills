#!/usr/bin/env python3
"""Executes dv:closeout's own Step 1 bash to test how it lists ignored build output.

Closeout once called a worktree "NOT safe to delete" only because Python caches below the top
level (`tooling/evals/__pycache__/*.pyc`) or a top-level `.venv/` differed from the main
checkout's copies: its listing grouped ignored entries by top-level path, and only "only here"
entries under a top-level build-output path counted as accepted build output. These checks run
the fenced bash block the skill actually ships under "Step 1", never a copy, against a scratch
main repo and a linked worktree made here:

  a. differing files in a nested __pycache__/ are one `__pycache__/ (any depth)` line with
     their entry and directory counts, and nothing outside build output is listed
  b. differing files in a top-level .venv/ are listed under `.venv/ (any depth)`
  c. a differing ignored file outside the build-output names is still listed as "different"
  d. near-miss names (myvenv/, venv_notes/, a file named venv) are not build output
  e. an entry under two names (node_modules/pkg/__pycache__/x) counts once, under the outermost
  f. a nested git repo is never build output: inside .venv/ and outside build output alike it
     is on its top-level line and listed by path as nested-repo, so it blocks "safe"; a
     differing file beside it in .venv/ stays build output
  g. names git quotes in plain porcelain (a space, a non-ASCII letter) are matched and compared
     as they are: build output with a space in its path stays build output, and a nested repo
     with a space in its name under a nested .venv/ still blocks "safe"
  h. a nested repo git cannot open (.git without HEAD, a .git file pointing nowhere, and one
     holding only its .git folder, which git does not list at all) inside .venv/ is listed
     once, by path, as nested-repo, not as build output
  i. nested repos in an untracked folder that is not ignored (one git cannot open, holding only
     .git, which git status does not list at all; one valid) are listed by path as nested-repo
  j. an initialized submodule is not a nested repo

Step 1 also calls gh and git fetch. A gh shim that always fails keeps the run off the network
(the block then lists "gh missing" among the checks that did not run, which these checks
ignore), and the scratch repo has no origin. Every repo is made in a temp dir created and
removed here. The block runs under bash, and under zsh when it is installed, each with the
system awk, plus gawk and mawk through a PATH shim when they are installed and are not the
system awk. On a Mac the system awk is BSD awk; the ubuntu CI runner has no zsh and runs the
system awk plus mawk.

Stdlib only, no network.

    python3 tooling/evals/test_closeout_build_output.py [path/to/SKILL.md]

Exits non-zero on any failure. The optional path lets you prove the test is load-bearing:
point it at the pre-change SKILL.md and it fails.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_MD = REPO_ROOT / "plugins" / "dv" / "skills" / "closeout" / "SKILL.md"
GITIGNORE = "\n".join([
    "__pycache__/", ".venv/", "node_modules/", "*.local", "myvenv/", "venv_notes/", "notes/", "",
])

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if not ok:
        failures.append(f"{name}" + (f"\n     {detail}" if detail else ""))


def step1_bash(md: str) -> str:
    """Return the first ```bash block under the `### Step 1` heading."""
    lines = md.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("### Step 1")), None)
    if start is None:
        raise SystemExit("FAILED: no '### Step 1' section in SKILL.md")
    body: list[str] = []
    inside = False
    indent = ""
    for line in lines[start + 1:]:
        if not inside and re.match(r"^#{2,3} ", line):
            break
        m = re.match(r"^(\s*)```(\w*)\s*$", line)
        if not inside and m and m.group(2) == "bash":
            inside, indent = True, m.group(1)
            continue
        if inside and m and not m.group(2):
            return "\n".join(body) + "\n"
        if inside:
            body.append(line[len(indent):] if line.startswith(indent) else line)
    raise SystemExit("FAILED: no closed ```bash block under '### Step 1'")


def write(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def git(env: dict[str, str], cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True)


def ignored_section(stdout: str) -> list[str] | None:
    """The lines under '=== Ignored entries ...' up to the next '=== ' header."""
    lines = stdout.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("=== Ignored entries")), None)
    if start is None:
        return None
    out = []
    for line in lines[start + 1:]:
        if line.startswith("=== "):
            break
        out.append(line)
    return out


def run_case(shell: str, path_env: str, block: str, main_files: dict[str, str],
             wt_files: dict[str, str], wt_repos: tuple[str, ...] = (),
             wt_broken: tuple[str, ...] = (), wt_bare_git: tuple[str, ...] = (),
             submodule: bool = False) -> tuple[list[str] | None, str]:
    with tempfile.TemporaryDirectory(prefix="vil869-") as work:
        root = Path(work).resolve()
        home = root / "home"
        home.mkdir()
        env = {"PATH": path_env, "HOME": str(home), "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
        main = root / "main"
        main.mkdir()
        git(env, main, "init", "-q")
        git(env, main, "symbolic-ref", "HEAD", "refs/heads/main")
        write(main, ".gitignore", GITIGNORE)
        write(main, "README", "scratch\n")
        git(env, main, "add", ".gitignore", "README")
        git(env, main, "commit", "-q", "-m", "init")
        if submodule:  # an initialized submodule is not a nested repo
            src = root / "subsrc"
            src.mkdir()
            write(src, "lib.txt", "lib\n")
            git(env, src, "init", "-q")
            git(env, src, "add", "lib.txt")
            git(env, src, "commit", "-q", "-m", "lib")
            git(env, main, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(src),
                "libs/sub")
            git(env, main, "commit", "-q", "-m", "add submodule")
        wt = root / "wt"
        git(env, main, "worktree", "add", "-q", "-b", "feature", str(wt))
        if submodule:
            git(env, wt, "-c", "protocol.file.allow=always", "submodule", "update", "--init", "-q")
        for rel, content in main_files.items():
            write(main, rel, content)
        for rel, content in wt_files.items():
            write(wt, rel, content)
        for rel in wt_repos:  # a nested repo: git lists it as one entry, "not examined"
            (wt / rel).mkdir(parents=True, exist_ok=True)
            git(env, wt / rel, "init", "-q")
        for rel in wt_broken:  # repos git cannot open: it lists their files one by one
            (wt / rel / "a").mkdir(parents=True, exist_ok=True)
            write(wt / rel / "a", "work.txt", "unpushed work\n")
            git(env, wt / rel / "a", "init", "-q")
            (wt / rel / "a" / ".git" / "HEAD").unlink()
            write(wt / rel / "b", "work.txt", "unpushed work\n")
            write(wt / rel / "b", ".git", "gitdir: /nonexistent/vil869\n")
            (wt / rel / "c").mkdir(parents=True, exist_ok=True)  # only .git: git lists nothing
            git(env, wt / rel / "c", "init", "-q")
            git(env, wt / rel / "c", "commit", "-q", "--allow-empty", "-m", "unpushed")
            (wt / rel / "c" / ".git" / "HEAD").unlink()
        for rel in wt_bare_git:  # an unopenable repo holding only .git, in any folder
            (wt / rel).mkdir(parents=True, exist_ok=True)
            git(env, wt / rel, "init", "-q")
            git(env, wt / rel, "commit", "-q", "--allow-empty", "-m", "unpushed")
            (wt / rel / ".git" / "HEAD").unlink()
        p = subprocess.run([shell, "-c", block], cwd=wt, env=env, capture_output=True,
                           text=True, timeout=120)
        return ignored_section(p.stdout), f"rc={p.returncode} stdout={p.stdout!r} stderr={p.stderr!r}"


BUILD_LINE = re.compile(r"^  (\S+/) \(any depth\): ")
TOP_LINE = re.compile(r"^  (\S+)  \d+ entries: ")
EXAMPLE = re.compile(r"^    (different|not-examined|nested-repo): (.*)$")


def scenario(shell: str, awk_label: str, path_env: str, block: str) -> None:
    tag = f"[{shell}, {awk_label} awk]"

    def section(name: str, main_files: dict[str, str], wt_files: dict[str, str],
                wt_repos: tuple[str, ...] = (), wt_broken: tuple[str, ...] = (),
                wt_bare_git: tuple[str, ...] = (), submodule: bool = False):
        sec, detail = run_case(shell, path_env, block, main_files, wt_files, wt_repos, wt_broken,
                               wt_bare_git, submodule)
        if sec is None:
            failures.append(f"{tag} {name}: no 'Ignored entries' section in the output\n     {detail}")
        return sec, detail

    # a. Only nested __pycache__/ differences.
    sec, detail = section("a", {"tooling/evals/__pycache__/x.pyc": "main copy\n",
                                "pkg/__pycache__/z.pyc": "same\n"},
                          {"tooling/evals/__pycache__/x.pyc": "worktree copy\n",
                           "tooling/evals/__pycache__/y.pyc": "only here\n",
                           "pkg/__pycache__/z.pyc": "same\n"})
    if sec is not None:
        want = ("  __pycache__/ (any depth): 3 entries in 2 directories: 1 same as the main "
                "checkout, 1 only here, 1 different, 0 not examined")
        check(f"{tag} a. one __pycache__/ (any depth) line with entry and directory counts",
              want in sec, detail)
        check(f"{tag} a. nothing listed outside build output",
              all(BUILD_LINE.match(l) for l in sec if l.strip()), detail)
        check(f"{tag} a. no 'different' example listed", not any(EXAMPLE.match(l) for l in sec),
              detail)

    # b. Top-level .venv/ differences.
    sec, detail = section("b", {".venv/bin/python": "main interpreter\n"},
                          {".venv/bin/python": "worktree interpreter\n",
                           ".venv/lib/site.py": "only here\n"})
    if sec is not None:
        want = ("  .venv/ (any depth): 2 entries in 1 directory: 0 same as the main checkout, "
                "1 only here, 1 different, 0 not examined")
        check(f"{tag} b. differing .venv/ files listed as build output under .venv/",
              want in sec, detail)
        check(f"{tag} b. no top-level line and no 'different' example for .venv/",
              not any(TOP_LINE.match(l) or EXAMPLE.match(l) for l in sec), detail)

    # c. A differing ignored file outside build output, beside nested build output.
    sec, detail = section("c", {"config.local": "main\n", "src/__pycache__/m.pyc": "main\n"},
                          {"config.local": "edited here\n", "src/__pycache__/m.pyc": "wt\n"})
    if sec is not None:
        check(f"{tag} c. the outside file is on a top-level line as different",
              "  config.local  1 entries: 0 same as the main checkout, 0 only here, 1 different, "
              "0 not examined, 0 nested git repos" in sec, detail)
        examples = [EXAMPLE.match(l).groups() for l in sec if EXAMPLE.match(l)]
        check(f"{tag} c. the outside file is the one 'different' example",
              examples == [("different", "config.local")], detail)
        check(f"{tag} c. the nested cache is still build output",
              any(l.startswith("  __pycache__/ (any depth): 1 entry in 1 directory:") for l in sec),
              detail)

    # d. Near-miss names are not build output.
    near = {"myvenv/lib/x.py": "main\n", "src/venv_notes/n.txt": "main\n", "notes/venv": "main\n"}
    sec, detail = section("d", near, {k: "edited here\n" for k in near})
    if sec is not None:
        check(f"{tag} d. no near-miss name is treated as build output",
              not any(BUILD_LINE.match(l) for l in sec), detail)
        tops = {TOP_LINE.match(l).group(1) for l in sec if TOP_LINE.match(l)}
        check(f"{tag} d. each near miss is on a top-level line",
              tops == {"myvenv/", "src/", "notes/"}, detail)
        examples = sorted(e for k, e in (EXAMPLE.match(l).groups() for l in sec if EXAMPLE.match(l)))
        check(f"{tag} d. each near miss is listed as different",
              examples == sorted(near), detail)

    # e. An entry under two names counts once, under the outermost.
    sec, detail = section("e", {"node_modules/a.js": "main\n"},
                          {"node_modules/a.js": "edited\n",
                           "node_modules/pkg/__pycache__/x.pyc": "only here\n"})
    if sec is not None:
        check(f"{tag} e. counted once under node_modules/",
              "  node_modules/ (any depth): 2 entries in 1 directory: 0 same as the main "
              "checkout, 1 only here, 1 different, 0 not examined" in sec, detail)
        check(f"{tag} e. no separate __pycache__/ line",
              not any(l.startswith("  __pycache__/") for l in sec), detail)

    # f. Nested git repos block "safe" wherever they are; other build output stays accepted.
    sec, detail = section("f", {".venv/lib/a.py": "main\n"}, {".venv/lib/a.py": "wt\n"},
                          (".venv/src/dep", "vendor.local"))
    if sec is not None:
        check(f"{tag} f. the .venv/ line holds only the non-repo entry",
              "  .venv/ (any depth): 1 entry in 1 directory: 0 same as the main checkout, "
              "0 only here, 1 different, 0 not examined" in sec, detail)
        check(f"{tag} f. the repo inside .venv/ is on the .venv/ top-level line as a nested repo",
              "  .venv/  1 entries: 0 same as the main checkout, 0 only here, 0 different, "
              "0 not examined, 1 nested git repos" in sec, detail)
        examples = sorted(EXAMPLE.match(l).groups() for l in sec if EXAMPLE.match(l))
        check(f"{tag} f. both nested repos are listed by path as nested-repo",
              examples == [("nested-repo", ".venv/src/dep/"), ("nested-repo", "vendor.local/")],
              detail)

    # g. Paths git quotes in plain porcelain output are matched and compared as they are.
    sec, detail = section("g", {"a/.venv/my pkg/x y.py": "main\n"},
                          {"a/.venv/my pkg/x y.py": "wt\n", ".venv/caf\u00e9.py": "only here\n",
                           "sub dir/__pycache__/m.pyc": "only here\n"},
                          ("a/.venv/src/my repo",))
    if sec is not None:
        check(f"{tag} g. files with a space or a non-ASCII letter in .venv/ paths are build output",
              "  .venv/ (any depth): 2 entries in 2 directories: 0 same as the main checkout, "
              "1 only here, 1 different, 0 not examined" in sec, detail)
        check(f"{tag} g. a cache under a top-level dir with a space is build output",
              "  __pycache__/ (any depth): 1 entry in 1 directory: 0 same as the main checkout, "
              "1 only here, 0 different, 0 not examined" in sec, detail)
        check(f"{tag} g. a nested repo with a space in its name blocks, named by path",
              "    nested-repo: a/.venv/src/my repo/" in sec
              and "  a/  1 entries: 0 same as the main checkout, 0 only here, 0 different, "
              "0 not examined, 1 nested git repos" in sec, detail)
        check(f"{tag} g. no quoted path is left over", not any('"' in l for l in sec), detail)

    # h. Repos git cannot open are walked into by git; they must still block, named once.
    sec, detail = section("h", {}, {".venv/lib/ok.py": "x\n"}, (), (".venv/src",))
    if sec is not None:
        check(f"{tag} h. only the plain file is on the .venv/ build-output line",
              "  .venv/ (any depth): 1 entry in 1 directory: 0 same as the main checkout, "
              "1 only here, 0 different, 0 not examined" in sec, detail)
        examples = sorted(EXAMPLE.match(l).groups() for l in sec if EXAMPLE.match(l))
        check(f"{tag} h. each unopenable repo is listed once, by path, as nested-repo",
              examples == [("nested-repo", ".venv/src/a/"), ("nested-repo", ".venv/src/b/"),
                           ("nested-repo", ".venv/src/c/")],
              detail)

    # i. Nested repos in an untracked folder with no ignore rule still block.
    sec, detail = section("i", {}, {}, ("scratch/valid",), (), ("scratch/old",))
    if sec is not None:
        examples = sorted(EXAMPLE.match(l).groups() for l in sec if EXAMPLE.match(l))
        check(f"{tag} i. both repos in an unignored untracked folder are listed as nested-repo",
              examples == [("nested-repo", "scratch/old/"), ("nested-repo", "scratch/valid/")],
              detail)
        check(f"{tag} i. they are counted on the scratch/ top-level line",
              "  scratch/  2 entries: 0 same as the main checkout, 0 only here, 0 different, "
              "0 not examined, 2 nested git repos" in sec, detail)

    # j. An initialized submodule is not a nested repo.
    sec, detail = section("j", {}, {"x.local": "x\n"}, submodule=True)
    if sec is not None:
        check(f"{tag} j. the submodule is not listed as a nested repo",
              not any("nested-repo" in l or "libs" in l for l in sec), detail)
        check(f"{tag} j. the listing still ran (the ignored file is there)",
              any(l.startswith("  x.local  1 entries:") for l in sec), detail)


def main() -> int:
    skill = Path(sys.argv[1]) if len(sys.argv) > 1 else SKILL_MD
    block = step1_bash(skill.read_text())
    if "=== Ignored entries" not in block:
        print("FAILED: the Step 1 block no longer prints the 'Ignored entries' listing")
        return 1

    shells = [s for s in ("bash", "zsh") if shutil.which(s)]
    base = os.environ.get("PATH", "/usr/bin:/bin")
    shim_root = tempfile.mkdtemp(prefix="vil869-shim-")
    try:
        gh_dir = os.path.join(shim_root, "gh")
        os.mkdir(gh_dir)
        gh = os.path.join(gh_dir, "gh")
        with open(gh, "w") as f:
            f.write("#!/bin/sh\nexit 1\n")
        os.chmod(gh, 0o755)
        awks = [("system", gh_dir + os.pathsep + base)]
        for name in ("gawk", "mawk"):
            found = shutil.which(name)
            if found and os.path.realpath(found) != os.path.realpath(shutil.which("awk") or ""):
                d = os.path.join(shim_root, name)
                os.mkdir(d)
                os.symlink(found, os.path.join(d, "awk"))
                awks.append((name, d + os.pathsep + gh_dir + os.pathsep + base))
        for shell in shells:
            for label, path_env in awks:
                scenario(shell, label, path_env, block)
    finally:
        shutil.rmtree(shim_root, ignore_errors=True)

    combos = len(shells) * len(awks)
    if failures:
        print(f"FAILED — {len(failures)} check(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"OK — closeout build-output listing ({combos} shell/awk combination(s): "
          f"{', '.join(shells)} x {', '.join(l for l, _ in awks)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
