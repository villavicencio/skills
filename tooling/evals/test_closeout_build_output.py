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
  k. bare repos without HEAD, including paths with spaces or newlines and symlinked marker
     directories, are detected; the worktree root and an objects-only folder are not repos
  l. a failed find reports that repository discovery did not run
  m. each build-output line ends with a fingerprint over its entries' paths, file contents and
     symlink targets: a second run on an unchanged tree prints every line the same, and a file
     edited in place (same size, every count unchanged), a symlink pointed elsewhere (also to a
     target that differs only by a tab against "?"), a file renamed in its directory, a file with
     a newline in its name edited or renamed to the same name with "?" changes that line's
     fingerprint and nothing else; a change to the main checkout's copy alone changes no
     fingerprint
  n. when hashing fails, in the batch or for one line after another line's succeeded, every
     fingerprint reads "unknown" and the check is listed as not run
  o. no run leaves a file or folder behind in TMPDIR

Step 1 also calls gh and git fetch. A gh shim that always fails keeps the run off the network
(the block then lists "gh missing" among the checks that did not run, which these checks
ignore), and the scratch repo has no origin. A failing external test shim guards against launching test for
every directory; shell builtins still work. Every repo is made in a temp dir created and
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
from typing import Callable

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


Step = Callable[[Path, Path], None]


def run_case(shell: str, path_env: str, block: str, main_files: dict[str, str],
             wt_files: dict[str, str], wt_repos: tuple[str, ...] = (),
             wt_broken: tuple[str, ...] = (), wt_bare_git: tuple[str, ...] = (),
             submodule: bool = False, bare_repos: tuple[str, ...] = (),
             bare_links: bool = False, label: str = "") -> tuple[list[str] | None, str]:
    return run_steps(shell, path_env, block, main_files, wt_files, wt_repos, wt_broken,
                     wt_bare_git, submodule, bare_repos, bare_links, label=label)[0]


def run_steps(shell: str, path_env: str, block: str, main_files: dict[str, str],
              wt_files: dict[str, str], wt_repos: tuple[str, ...] = (),
              wt_broken: tuple[str, ...] = (), wt_bare_git: tuple[str, ...] = (),
              submodule: bool = False, bare_repos: tuple[str, ...] = (),
              bare_links: bool = False, wt_links: dict[str, str] | None = None,
              steps: tuple[tuple[str, Step], ...] = (),
              extra_env: dict[str, str] | None = None,
              label: str = "") -> list[tuple[list[str] | None, str]]:
    """Run the block on a fresh tree, then once more after each step(main, wt) changes it."""
    with tempfile.TemporaryDirectory(prefix="vil869-") as work:
        root = Path(work).resolve()
        home = root / "home"
        home.mkdir()
        env = {"PATH": path_env, "HOME": str(home), "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
               "TMPDIR": str(root / "tmp"), **(extra_env or {})}
        (root / "tmp").mkdir()
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
        for rel in bare_repos:
            (wt / rel).mkdir(parents=True, exist_ok=True)
            git(env, wt / rel, "init", "--bare", "-q")
            (wt / rel / "HEAD").unlink()  # still detected when Git cannot open it
        if bare_links:
            # Both marker directories may be symlinks; the root itself is never nested.
            (root / "objects-target").mkdir()
            (root / "refs-target").mkdir()
            (wt / ".venv/src/links").mkdir(parents=True, exist_ok=True)
            (wt / ".venv/src/links/objects").symlink_to(root / "objects-target")
            (wt / ".venv/src/links/refs").symlink_to(root / "refs-target")
            (wt / "objects").mkdir()
            (wt / "refs").mkdir()
            (wt / ".venv/src/not-a-repo/objects").mkdir(parents=True)
        for rel, target in (wt_links or {}).items():
            (wt / rel).parent.mkdir(parents=True, exist_ok=True)
            (wt / rel).symlink_to(target)
        results = []
        for name, step in (("first run", None), *steps):
            if step is not None:
                step(main, wt)
            p = subprocess.run([shell, "-c", block], cwd=wt, env=env, capture_output=True,
                               text=True, timeout=120)
            # The block's status is that of its closing `if [ -n "$FAILS" ] ... fi`, which prints
            # and returns 0 whether or not a check failed to run. Anything else is a block that
            # broke.
            check(f"{label} ({name}): the Step 1 block exits 0", p.returncode == 0,
                  f"rc={p.returncode} stdout={p.stdout!r} stderr={p.stderr!r}")
            results.append((ignored_section(p.stdout),
                            f"rc={p.returncode} stdout={p.stdout!r} stderr={p.stderr!r}"))
            # o. The block removes every temp file and folder it made.
            left = sorted(x.name for x in (root / "tmp").iterdir())
            check(f"{label} ({name}): o. nothing is left in TMPDIR", not left, f"left: {left}")
        return results


BUILD_LINE = re.compile(r"^  (\S+/) \(any depth\): ")
FINGERPRINT = re.compile(r"; fingerprint ([0-9a-f]{12}|unknown)$")


def unprinted(sec: list[str]) -> list[str]:
    """The section with the fingerprint cut off each build-output line."""
    return [FINGERPRINT.sub("", l) if BUILD_LINE.match(l) else l for l in sec]


def fingerprints(sec: list[str]) -> dict[str, str]:
    """Build-output name -> the fingerprint its line prints."""
    out = {}
    for l in sec:
        b, f = BUILD_LINE.match(l), FINGERPRINT.search(l)
        if b and f:
            out[b.group(1)] = f.group(1)
    return out


def edit(rel: str, content: str, where: str = "wt") -> Step:
    def step(main: Path, wt: Path) -> None:
        ((wt if where == "wt" else main) / rel).write_text(content)
    return step


def relink(rel: str, target: str) -> Step:
    def step(main: Path, wt: Path) -> None:
        (wt / rel).unlink()
        (wt / rel).symlink_to(target)
    return step


def rename(rel: str, new_rel: str) -> Step:
    def step(main: Path, wt: Path) -> None:
        (wt / rel).rename(wt / new_rel)
    return step


def unchanged(main: Path, wt: Path) -> None:
    pass
TOP_LINE = re.compile(r"^  (\S+)  \d+ entries: ")
EXAMPLE = re.compile(r"^    (different|not-examined|nested-repo): (.*)$")


def scenario(shell: str, awk_label: str, path_env: str, block: str) -> None:
    tag = f"[{shell}, {awk_label} awk]"

    def section(name: str, main_files: dict[str, str], wt_files: dict[str, str],
                wt_repos: tuple[str, ...] = (), wt_broken: tuple[str, ...] = (),
                wt_bare_git: tuple[str, ...] = (), submodule: bool = False,
                bare_repos: tuple[str, ...] = (), bare_links: bool = False):
        sec, detail = run_case(shell, path_env, block, main_files, wt_files, wt_repos, wt_broken,
                               wt_bare_git, submodule, bare_repos, bare_links,
                               label=f"{tag} {name}")
        if sec is None:
            failures.append(f"{tag} {name}: no 'Ignored entries' section in the output\n     {detail}")
            return sec, detail
        # Every build-output line carries a fingerprint; the checks below compare the rest.
        check(f"{tag} {name}. every build-output line ends with a 12-digit fingerprint",
              all(re.search(r"; fingerprint [0-9a-f]{12}$", l) for l in sec if BUILD_LINE.match(l)),
              detail)
        return unprinted(sec), detail

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

    # k. Bare repositories, even without HEAD, are never build output.
    sec, detail = section("k", {}, {".venv/lib/ok.py": "x\n"},
                          bare_repos=(".venv/src/demo.git", "scratch/bare", ".venv/src/my bare",
                                      ".venv/src/line\nbreak"), bare_links=True)
    if sec is not None:
        examples = sorted(EXAMPLE.match(l).groups() for l in sec if EXAMPLE.match(l))
        check(f"{tag} k. bare repos listed by path", examples == [
            ("nested-repo", ".venv/src/demo.git/"), ("nested-repo", ".venv/src/line?break/"),
            ("nested-repo", ".venv/src/links/"), ("nested-repo", ".venv/src/my bare/"),
            ("nested-repo", "scratch/bare/")], detail)
        check(f"{tag} k. ordinary build output remains",
              "  .venv/ (any depth): 1 entry in 1 directory: 0 same as the main checkout, "
              "1 only here, 0 different, 0 not examined" in sec, detail)

    # m. The fingerprint changes with what is in build output, and only then.
    nl_name = ".venv/lib/line\nbreak.py"
    # Each step: what it does, and whether it changes the .venv/ and node_modules/ lines.
    plan = (("rerun, nothing changed", unchanged, False, False),
            ("a.py edited in place", edit(".venv/lib/a.py", "hellp\n"), True, False),
            ("symlink pointed elsewhere", relink(".venv/bin/python", "python3.13"), True, False),
            ("file renamed in its directory",
             rename(".venv/lib/sp ace.py", ".venv/lib/sp ade.py"), True, False),
            ("file with a newline in its name edited", edit(nl_name, "NL\n"), True, False),
            ("that file renamed to the same name with ?",
             rename(nl_name, ".venv/lib/line?break.py"), True, False),
            ("symlink target with a tab", relink(".venv/bin/python", "py\tthon"), True, False),
            ("symlink target with ? for the tab", relink(".venv/bin/python", "py?thon"), True, False),
            ("only the main checkout's copy edited",
             edit(".venv/lib/d.py", "main copy, edited\n", where="main"), False, False),
            ("node_modules file edited in place", edit("node_modules/x/i.js", "JS\n"), False, True))
    runs = run_steps(
        shell, path_env, block,
        {".venv/lib/d.py": "main copy\n", "node_modules/x/same.js": "same\n"},
        {".venv/lib/a.py": "hello\n", ".venv/lib/d.py": "worktree copy\n",
         ".venv/lib/sp ace.py": "x\n", nl_name: "nl\n", "node_modules/x/same.js": "same\n",
         "node_modules/x/i.js": "js\n"},
        wt_links={".venv/bin/python": "python3.12"},
        steps=tuple((name, step) for name, step, _, _ in plan),
        label=f"{tag} m")
    secs = [sec for sec, _ in runs]
    detail = "\n     ".join(d for _, d in runs)
    if any(sec is None for sec in secs):
        failures.append(f"{tag} m: no 'Ignored entries' section in some run\n     {detail}")
    else:
        fps = [fingerprints(sec) for sec in secs]
        check(f"{tag} m. both build-output lines carry a 12-digit fingerprint",
              all(set(f) == {".venv/", "node_modules/"} and
                  all(re.fullmatch(r"[0-9a-f]{12}", v) for v in f.values()) for f in fps),
              detail)
        check(f"{tag} m. the counts are the same in every run",
              all(unprinted(sec) == unprinted(secs[0]) for sec in secs), detail)
        check(f"{tag} m. a rerun on an unchanged tree prints every line the same",
              secs[1] == secs[0], detail)
        # A change gives a fingerprint not seen before on that line; no change keeps the last one.
        for i, (name, _, venv_changes, nm_changes) in enumerate(plan, start=1):
            for line, changes in ((".venv/", venv_changes), ("node_modules/", nm_changes)):
                now, seen = fps[i].get(line), [f.get(line) for f in fps[:i]]
                check(f"{tag} m. {name}: {line} fingerprint "
                      + ("changes to a new value" if changes else "stays the same"),
                      (now not in seen) if changes else now == seen[-1],
                      f"{[f.get(line) for f in fps]}\n     {detail}")


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
        # find must not need an external test process per traversed directory.
        test = os.path.join(gh_dir, "test")
        with open(test, "w") as f:
            f.write("#!/bin/sh\nexit 1\n")
        os.chmod(test, 0o755)
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
        fail_dir = os.path.join(shim_root, "failed-find")
        os.mkdir(fail_dir)
        find = os.path.join(fail_dir, "find")
        with open(find, "w") as f:
            f.write("#!/bin/sh\nexit 1\n")
        os.chmod(find, 0o755)
        _, detail = run_case(shells[0], fail_dir + os.pathsep + gh_dir + os.pathsep + base,
                             block, {}, {".venv/ordinary.py": "x\n"}, label="failed discovery")
        check("failed discovery makes safety unconfirmed",
              "finding nested repositories below the worktree failed" in detail, detail)
        # n. A batch hash that fails leaves every fingerprint unknown and the check not run.
        fail_xargs = os.path.join(shim_root, "failed-xargs")
        os.mkdir(fail_xargs)
        xargs = os.path.join(fail_xargs, "xargs")
        with open(xargs, "w") as f:
            f.write("#!/bin/sh\nexit 1\n")
        os.chmod(xargs, 0o755)
        for shell in shells:
            sec, detail = run_case(shell, fail_xargs + os.pathsep + gh_dir + os.pathsep + base,
                                   block, {}, {".venv/ordinary.py": "x\n",
                                               "node_modules/a.js": "y\n"},
                                   label=f"[{shell}] failed hashing")
            check(f"[{shell}] n. failed hashing prints every fingerprint as unknown",
                  sec is not None and fingerprints(sec) == {".venv/": "unknown",
                                                            "node_modules/": "unknown"}, detail)
            check(f"[{shell}] n. failed hashing makes safety unconfirmed",
                  "- fingerprinting the build output failed" in detail, detail)
        # n. The second line's hash fails after the first line's succeeded: both read unknown.
        real_git = shutil.which("git") or "git"
        git_dir = os.path.join(shim_root, "second-hash-fails")
        os.mkdir(git_dir)
        with open(os.path.join(git_dir, "git"), "w") as f:
            f.write('#!/bin/sh\n'
                    'if [ "$1" = hash-object ] && [ "$2" = --stdin ]; then\n'
                    '  echo x >> "$HASH_CALLS"\n'
                    '  [ "$(grep -c x "$HASH_CALLS")" -ge 2 ] && exit 1\n'
                    'fi\n'
                    'exec "$REAL_GIT" "$@"\n')
        os.chmod(os.path.join(git_dir, "git"), 0o755)
        for shell in shells:
            calls = os.path.join(shim_root, f"hash-calls-{shell}")
            sec, detail = run_steps(shell, git_dir + os.pathsep + gh_dir + os.pathsep + base,
                                    block, {}, {".venv/ordinary.py": "x\n",
                                                "node_modules/a.js": "y\n"},
                                    extra_env={"REAL_GIT": real_git, "HASH_CALLS": calls},
                                    label=f"[{shell}] second line's hash fails")[0]
            check(f"[{shell}] n. a later line's failed hash makes every fingerprint unknown",
                  sec is not None and fingerprints(sec) == {".venv/": "unknown",
                                                            "node_modules/": "unknown"}, detail)
            check(f"[{shell}] n. a later line's failed hash makes safety unconfirmed",
                  "- fingerprinting the build output failed" in detail, detail)
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
