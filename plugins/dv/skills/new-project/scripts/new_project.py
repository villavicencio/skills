#!/usr/bin/env python3
"""dv:new-project, the local half: checkout, private GitHub repository, Orca, vault section.

    python3 new_project.py <name> --section <section> [--owner <login>] [--description <text>]
                           [--linear-project <name>] [--dry-run] [--json]

Steps, in order:
  1. checkout  ~/Projects/<name>, one bootstrap commit (AGENTS.md, CLAUDE.md, README.md,
               .gitignore, docs/discovery.md). AGENTS.md has the `## Vault` section.
  2. github    <owner>/<name>, created with --private; once the create succeeds, a receipt
               goes into the checkout's git config. Nothing is pushed until the read-back shows
               this repository (name, URL) as PRIVATE, and only the bootstrap commit is pushed.
               The default branch and the commit are read after.
  3. orca      `orca repo add --path <checkout> --kind git --json`, read back with
               `orca repo list --json` by the same rule as the check.
  4. section   ~/Obsidian/scriptorium/<section>/memory and /inbox.
  5. memory    ~/.claude/projects/<slug>/ (created when missing) and its `memory`, a symlink to
               the section's memory/. A real memory/ folder replaces the section's empty
               memory/ in one rename.

What counts as this project's (one rule per target, used by the check and by the write):
  checkout  a real folder whose refs, except the stash and notes, reach one root commit,
            carrying the lines `Bootstrapped-by: dv:new-project` and `Project: <name>`, with
            no other section in AGENTS.md and no other origin.
  github    PRIVATE, and holding that root commit, or empty while the checkout holds the
            receipt that this tool's create of <owner>/<name> succeeded.
  orca      exactly one entry at the checkout path, kind git, for this repository or with no
            remote known yet, and no entry for this repository anywhere else.
  section   no other project's memory links to it; absent, or linked from this project's
            harness folder, or nothing but an empty memory/ and inbox/ (a Finder .DS_Store
            counts as content).
  harness   no other existing folder maps to the same folder name; absent, or a real folder
            found when the checkout already exists, with no session that started elsewhere,
            whose memory links to the section or that holds a session started in this
            checkout.
Anything else is a collision, and so is a target the checks can't place.

The checks run before the first write; the GitHub visibility read-back runs before the push.
A step already done is skipped, so a second run after a full one writes nothing and a run
after a partial one does only what is missing, or stops on what it can't place: after a
`gh repo create` that exited non-zero once the repository existed, there is no receipt, and
the stop message gives the command that records it. A collision stops the run before it writes
anything. The Linear project and the MergeWren onboarding ticket are the agent's steps
(SKILL.md); the plan lists them last so a dry run shows the whole order.

Exit codes: 0 done (or dry run planned), 1 a check could not run (nothing written) or a step
or a read-back failed, 2 usage error, 3 a collision found by the checks (nothing written).

Stdlib only, Python 3.9+ (the Mac's /usr/bin/python3).
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MARKER = "Bootstrapped-by: dv:new-project"
BRANCH = "main"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_STOP = 0, 1, 2, 3

DONE, TODO, STOP = "done", "todo", "stop"


class Fail(Exception):
    """A step or a read-back failed after the checks passed."""


class Blocked(Exception):
    """The checks could not run (a tool failed), so nothing may be written."""


# ---------------------------------------------------------------- output

JSON_MODE = False


def say(msg: str = "") -> None:
    print(msg, file=sys.stderr if JSON_MODE else sys.stdout, flush=True)


# ---------------------------------------------------------------- helpers

def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    try:
        p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    except FileNotFoundError:
        raise Blocked(f"`{cmd[0]}` is not on PATH")
    if check and p.returncode != 0:
        raise Fail(f"`{' '.join(cmd)}` exited {p.returncode}: {(p.stderr or p.stdout).strip()}")
    return p


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return run(["git", "-C", str(repo), *args], check=check)


def real(p: Path) -> str:
    return os.path.realpath(str(p))


def slug_for(path: str) -> str:
    """Claude Code's project folder name: every character that isn't a letter or digit -> '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def canonical_remote(url: str) -> str:
    """github.com/<owner>/<name>, lower case, from an https, ssh or scp-style URL."""
    u = url.strip()
    u = re.sub(r"^(https?|ssh|git)://", "", u)
    u = re.sub(r"^[^@/]+@", "", u)
    u = u.replace(":", "/", 1) if re.match(r"^[^/]+:", u) else u
    u = re.sub(r"\.git$", "", u.rstrip("/"))
    return u.lower()


class Ctx:
    def __init__(self, a: argparse.Namespace):
        self.name = a.name
        self.section = a.section
        self.description = a.description or ""
        self.linear_project = a.linear_project or a.name
        self.dry_run = a.dry_run
        self.home = Path.home()
        self.projects = self.home / "Projects"
        self.checkout = self.projects / a.name
        self.vault = self.home / "Obsidian" / "scriptorium"
        self.sec = self.vault / a.section
        claude_dir = os.environ.get("CLAUDE_CONFIG_DIR")
        self.claude_projects = (Path(claude_dir) if claude_dir else self.home / ".claude") / "projects"
        # The slug comes from the checkout's real path (Claude Code uses the resolved cwd).
        parent = real(self.projects) if self.projects.exists() else str(self.projects)
        self.slug = slug_for(os.path.join(parent, a.name))
        self.harness = self.claude_projects / self.slug
        self.owner = a.owner
        self.github_view: dict | None = None
        self.report: dict = {
            "name": a.name, "path": str(self.checkout), "section": a.section,
            "linear_project": self.linear_project, "dry_run": a.dry_run,
        }

    @property
    def full(self) -> str:
        return f"{self.owner}/{self.name}"


# ---------------------------------------------------------------- checks (read only)

def check_checkout(c: Ctx) -> tuple[str, str]:
    p = c.checkout
    if not os.path.lexists(p):
        return TODO, f"create {p} with the bootstrap commit"
    if p.is_symlink() or not p.is_dir():
        return STOP, f"{p} exists and is not a folder this tool made"
    if not (p / ".git").exists():
        return STOP, f"{p} already exists and is not a git repository made by dv:new-project"
    # Every ref, not only HEAD, so an unmerged branch or a tag with its own history counts.
    # The stash and notes are left out: `git stash -u` keeps untracked files in a commit with
    # no parent, and `git notes` keeps its own history; neither is the project's.
    roots = git(p, "rev-list", "--max-parents=0", "--exclude=refs/stash", "--exclude=refs/notes/*",
                "--all", check=False)
    root_list = roots.stdout.split() if roots.returncode == 0 else []
    if not root_list:
        return STOP, f"{p} is a git repository with no commits; dv:new-project did not make it"
    if len(root_list) > 1:
        return STOP, f"{p} has {len(root_list)} root commits; dv:new-project makes one"
    root = root_list[0]
    lines = {ln.strip() for ln in git(p, "log", "-1", "--format=%B", root).stdout.splitlines()}
    if MARKER not in lines or f"Project: {c.name}" not in lines:
        return STOP, f"{p} is a git repository that dv:new-project did not make for {c.name} (root {root[:7]})"
    agents = p / "AGENTS.md"
    m = re.search(r"section of the scriptorium vault is `([^`]+)`",
                  agents.read_text() if agents.is_file() else "")
    if m and m.group(1) != c.section:
        return STOP, f"{p}/AGENTS.md names section `{m.group(1)}`, not `{c.section}`"
    origin = git(p, "config", "--get", "remote.origin.url", check=False)
    if origin.returncode == 0 and c.owner and \
            canonical_remote(origin.stdout) != f"github.com/{c.full}".lower():
        return STOP, f"{p}'s origin is {origin.stdout.strip()}, not github.com/{c.full}"
    c.report["root_commit"] = root
    return DONE, f"{p} exists (bootstrap commit {root[:7]})"


def gh_repo_view(c: Ctx) -> dict | None:
    p = run(["gh", "repo", "view", c.full, "--json",
             "nameWithOwner,url,visibility,defaultBranchRef,isEmpty"], check=False)
    if p.returncode != 0:
        if "Could not resolve to a Repository" in (p.stderr + p.stdout):
            return None
        raise Blocked(f"`gh repo view {c.full}` failed: {(p.stderr or p.stdout).strip()}")
    try:
        return json.loads(p.stdout)
    except ValueError:
        raise Blocked(f"`gh repo view {c.full}` printed something other than JSON")


def has_origin(c: Ctx) -> bool:
    return c.checkout.is_dir() and \
        git(c.checkout, "config", "--get", "remote.origin.url", check=False).returncode == 0


def remote_has_root(c: Ctx) -> bool:
    """True when the GitHub repository holds this checkout's bootstrap (root) commit."""
    root = c.report.get("root_commit", "")
    if not root:
        return False
    has = run(["gh", "api", f"repos/{c.full}/commits/{root}", "--jq", ".sha"], check=False)
    if has.returncode == 0:
        return has.stdout.strip() == root
    err = has.stderr + has.stdout
    if "No commit found" in err or "Git Repository is empty" in err:
        return False
    raise Blocked(f"`gh api repos/{c.full}/commits/{root[:7]}` failed: {err.strip()}")


RECEIPT_KEY = "dv-new-project.created"


def has_receipt(c: Ctx) -> bool:
    """True when the checkout records that this tool's `gh repo create` of this repository
    succeeded. It is written only after the create returns success, so it is the proof that
    an empty repository of this name is this project's."""
    got = git(c.checkout, "config", "--local", "--get", RECEIPT_KEY, check=False)
    return got.returncode == 0 and got.stdout.strip().lower() == c.full.lower()


def check_github(c: Ctx, checkout_state: str) -> tuple[str, str]:
    view = gh_repo_view(c)
    c.github_view = view
    if view is None:
        return TODO, (f"create {c.full} with --private, record the receipt, read back name, URL "
                      f"and PRIVATE, set origin if missing, then push the bootstrap commit")
    if checkout_state != DONE:
        return STOP, f"github.com/{c.full} already exists and this run did not make it"
    if view.get("visibility") != "PRIVATE":
        return STOP, f"github.com/{c.full} exists and is {view.get('visibility')}, not PRIVATE"
    if view.get("isEmpty"):
        # An empty repository holds nothing to prove whose it is; the receipt, written only
        # after this tool's create succeeded, is the proof.
        if not has_receipt(c):
            return STOP, (f"github.com/{c.full} exists and is empty, and {c.checkout} has no receipt "
                          f"showing this tool created it. If it is this project's, run `git -C "
                          f"{c.checkout} config {RECEIPT_KEY} {c.full}` and run again")
        return TODO, f"set origin if missing, then push the bootstrap commit to the existing, empty github.com/{c.full}"
    if not remote_has_root(c):
        return STOP, (f"github.com/{c.full} has history without this checkout's bootstrap "
                      f"commit {c.report.get('root_commit', '')[:7]}; it belongs to something else")
    if not has_origin(c):
        return TODO, f"set origin to github.com/{c.full}, which already holds the bootstrap commit"
    return DONE, f"github.com/{c.full} exists, PRIVATE, holds the bootstrap commit"


def orca_repos() -> list[dict]:
    p = run(["orca", "repo", "list", "--json"], check=False)
    if p.returncode != 0:
        raise Blocked(f"`orca repo list --json` failed: {(p.stderr or p.stdout).strip()}")
    try:
        data = json.loads(p.stdout)
        return list(data["result"]["repos"])
    except (ValueError, KeyError, TypeError):
        raise Blocked("`orca repo list --json` printed something other than {result: {repos: [...]}}")


def same_path(a: str, b: Path) -> bool:
    return os.path.normpath(os.path.realpath(a)) == os.path.normpath(real(b))


def orca_match(c: Ctx, repos: list[dict]) -> tuple[str, str, dict | None]:
    """Is Orca's registration this checkout's? One rule, used before the add and after it:
    no entry for this repository at another path, and exactly one entry at the checkout path,
    of kind git, whose remote is this repository or not known yet."""
    want_key = f"github.com/{c.full}".lower()

    def key(r: dict) -> str:
        return ((r.get("gitRemoteIdentity") or {}).get("canonicalKey") or "").lower()

    here, elsewhere = [], []
    for r in repos:
        if r.get("path") and same_path(r["path"], c.checkout):
            here.append(r)
        elif key(r) == want_key:
            elsewhere.append(r)
    if elsewhere:
        r = elsewhere[0]
        return STOP, f"Orca already has github.com/{c.full} at another path: {r.get('path')} (id {r.get('id')})", None
    if not here:
        return TODO, f"Orca has no project at {c.checkout}", None
    if len(here) > 1:
        ids = ", ".join(str(r.get("id")) for r in here)
        return STOP, f"Orca has {len(here)} projects at {c.checkout} (ids {ids}); expected one", None
    r = here[0]
    if r.get("kind") != "git":
        return STOP, f"Orca has {r.get('path')} registered as kind {r.get('kind')}, not git", None
    if key(r) and key(r) != want_key:
        return STOP, f"Orca's project at {r.get('path')} is for {key(r)}, not github.com/{c.full}", None
    return DONE, f"Orca has {r.get('path')} (id {r.get('id')})", r


def check_orca(c: Ctx, checkout_state: str) -> tuple[str, str]:
    state, detail, r = orca_match(c, orca_repos())
    if state == TODO:
        return TODO, f"orca repo add --path {c.checkout} --kind git --json, read back with orca repo list"
    if state == DONE and checkout_state != DONE:
        return STOP, f"Orca already has a project at {c.checkout} (id {r.get('id')}), before this run made it"
    if state == DONE:
        c.report["orca_id"] = r.get("id")
    return state, detail


def empty_dir(p: Path) -> bool:
    """A real folder with nothing in it. A Finder .DS_Store counts as something: the memory
    move replaces the section's memory/ with one rename, and the OS refuses a folder that
    holds anything, so the checks use the same rule."""
    return p.is_dir() and not p.is_symlink() and not os.listdir(p)


def section_extra(sec: Path) -> str | None:
    """The first entry that makes the section more than this tool's scaffolding (an empty
    memory/ and an empty inbox/, either one possibly still missing), or None."""
    for e in sorted(os.listdir(sec)):
        if e not in ("memory", "inbox") or not empty_dir(sec / e):
            return e
    return None


def memory_link_ok(c: Ctx) -> bool:
    m = c.harness / "memory"
    return m.is_symlink() and real(m) == real(c.sec / "memory")


def check_section(c: Ctx) -> tuple[str, str]:
    if c.vault.is_symlink() or not (c.vault / ".obsidian").is_dir():
        return STOP, (f"the vault isn't set up on this Mac ({c.vault} must be a real folder with "
                      f".obsidian/); setting it up is Scribe's work, not this tool's")
    want = real(c.sec / "memory")
    if c.claude_projects.is_dir():
        for d in sorted(c.claude_projects.iterdir()):
            m = d / "memory"
            if d.name != c.slug and m.is_symlink() and real(m) == want:
                return STOP, f"section `{c.section}` is already the memory of another project ({d.name})"
    if not os.path.lexists(c.sec):
        return TODO, f"mkdir {c.sec}/memory {c.sec}/inbox"
    if c.sec.is_symlink() or not c.sec.is_dir():
        return STOP, f"{c.sec} exists and is not a folder"
    if not memory_link_ok(c):
        extra = section_extra(c.sec)
        if extra is not None:
            return STOP, (f"section {c.sec} holds `{extra}`, which isn't this tool's empty scaffolding, "
                          f"and this project's memory doesn't link to it")
    if (c.sec / "memory").is_dir() and (c.sec / "inbox").is_dir():
        return DONE, f"{c.sec} has memory/ and inbox/"
    return TODO, f"mkdir the missing memory/ or inbox/ in {c.sec}"


def slug_twins(c: Ctx) -> list[str]:
    """Existing paths, other than the checkout, that Claude Code would give the same project
    folder: it turns every character that isn't a letter or digit into '-', so ~/Projects/foo_bar,
    ~/Projects/foo/bar and ~/Projects-foo/bar all share foo-bar's folder. The walk starts at /
    and opens only folders whose own name so far matches the start of the slug, so it stays
    small. A folder on that path that can't be listed means the check can't run."""
    mine, found, todo = real(c.checkout), [], ["/"]
    while todo:
        d = todo.pop()
        try:
            names = os.listdir(d)
        except OSError as e:
            raise Blocked(f"can't list {d} to look for paths sharing the harness folder name: {e}")
        for n in names:
            p = os.path.join(d, n)
            s = slug_for(p)
            if s == c.slug:
                if os.path.isdir(p) and os.path.realpath(p) != mine:  # only a folder hosts a session
                    found.append(p)
            elif c.slug.startswith(s + "-") and os.path.isdir(p):
                todo.append(p)
    return sorted(found)


def session_starts(h: Path) -> set[str]:
    """Where each session in the harness folder started: the first `cwd` in each *.jsonl,
    resolved. Later lines can show a subfolder the session moved into, so only the first one
    names the folder the session belongs to."""
    starts: set[str] = set()
    for f in sorted(h.glob("*.jsonl")):
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"cwd"' not in line:
                    continue
                try:
                    cwd = json.loads(line).get("cwd")
                except (ValueError, AttributeError):
                    continue
                if isinstance(cwd, str):
                    starts.add(os.path.realpath(cwd))
                    break
    return starts


def check_memory(c: Ctx, checkout_state: str) -> tuple[str, str]:
    h, m, sec_mem = c.harness, c.harness / "memory", c.sec / "memory"
    if os.path.lexists(h) and (h.is_symlink() or not h.is_dir()):
        return STOP, f"{h} exists and is not a folder"
    twins = slug_twins(c)
    if twins:
        return STOP, (f"{twins[0]} maps to the same harness folder ({c.slug}) as {c.checkout}, "
                      f"so the two would share memory; pick another name")
    if h.is_dir():
        # The folder is this project's only with proof: this tool's link to the section, or
        # sessions that all started in this checkout. A folder older than the checkout, one
        # holding another checkout's sessions, or one with neither proof is a collision.
        if checkout_state != DONE:
            return STOP, f"{h} exists before {c.checkout} does; another project uses this folder name"
        starts = session_starts(h)
        others = sorted(s for s in starts if s != real(c.checkout))
        if others:
            return STOP, f"{h} holds sessions started in {', '.join(others)}; another project uses this folder name"
        if not memory_link_ok(c) and real(c.checkout) not in starts:
            return STOP, (f"{h} exists and nothing in it shows it is this project's (no memory link to "
                          f"the section, no session started in {c.checkout})")
    if m.is_symlink():
        if memory_link_ok(c):
            return DONE, f"{m} -> {sec_mem}"
        return STOP, f"{m} already links to {os.readlink(m)}"
    if not os.path.lexists(m):
        made = "" if h.is_dir() else f"mkdir {h}; "
        return TODO, f"{made}ln -s {sec_mem} {m}"
    if not m.is_dir():
        return STOP, f"{m} exists and is not a folder or a link"
    if os.path.lexists(sec_mem) and not empty_dir(sec_mem):
        return STOP, f"{m} and {sec_mem} both hold files; merge them by hand"
    return TODO, f"move {m} to {sec_mem} (one rename), then link it"


# ---------------------------------------------------------------- writes

def bootstrap_files(c: Ctx) -> dict[str, str]:
    what = c.description or "What this project is: write it in the first session."
    today = datetime.date.today().isoformat()
    return {
        "AGENTS.md": f"""# {c.name}

{what}

AGENTS.md is the canonical instructions file; CLAUDE.md imports it. Edit this file, not that one.

## Workflow
- Changes go on a branch and merge by PR. Review is MergeWren once this repository's onboarding
  ticket in the MergeWren Linear project is done and a real verdict has been seen on a PR. Until
  then this repository has no reviewer: dotfiles `docs/agents/code-review.md` says what may merge.
- Issue tracking: Linear project `{c.linear_project}` (team VIL).
- Discovery notes: `docs/discovery.md`.

## Vault
This project's section of the scriptorium vault is `{c.section}` (`~/Obsidian/scriptorium/{c.section}/`).
Its harness memory lives in `{c.section}/memory/`. The vault's rules: dotfiles
`docs/agents/obsidian-vaults.md`.
""",
        "CLAUDE.md": """# CLAUDE.md

@AGENTS.md

AGENTS.md is the canonical instructions file for every agent. Edit it, not this file.
""",
        "README.md": f"""# {c.name}

{what}

Private repository, started {today}. Instructions for agents: [AGENTS.md](AGENTS.md).
""",
        ".gitignore": """.DS_Store
.env
.env.*
!.env.example
.claude/settings.local.json
""",
        "docs/discovery.md": f"""# Discovery: {c.name}

Notes from before the first feature ticket. No code here.

## The problem

## Who it is for

## What exists already

## Open questions

## Decisions
""",
    }


def do_checkout(c: Ctx) -> None:
    c.projects.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f".{c.name}.new-project-", dir=str(c.projects)))
    try:
        for rel, text in bootstrap_files(c).items():
            f = tmp / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text)
        git(tmp, "init", "-q", "-b", "main")
        git(tmp, "add", "-A")
        msg = (f"chore: bootstrap {c.name}\n\nInstructions (AGENTS.md, CLAUDE.md), README, "
               f".gitignore and a discovery doc. No feature code.\n\n"
               f"{MARKER}\nProject: {c.name}\nSection: {c.section}\n")
        git(tmp, "commit", "-q", "-m", msg)
        if os.path.lexists(c.checkout):
            raise Fail(f"{c.checkout} appeared after the checks; leaving it alone")
        os.rename(tmp, c.checkout)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    c.report["root_commit"] = git(c.checkout, "rev-list", "--max-parents=0", "HEAD").stdout.split()[0]


def require_private(view: dict | None, c: Ctx) -> dict:
    if view is None:
        raise Fail(f"read-back: github.com/{c.full} does not exist after the create")
    if view.get("visibility") != "PRIVATE":
        raise Fail(f"read-back: github.com/{c.full} is {view.get('visibility')}, not PRIVATE. "
                   f"Make it private now (gh repo edit {c.full} --visibility private "
                   f"--accept-visibility-change-consequences) and tell David")
    full = view.get("nameWithOwner") or ""
    url = (view.get("url") or "").rstrip("/")
    if full.lower() != c.full.lower() or url.lower() != f"https://github.com/{c.full}".lower():
        raise Fail(f"read-back: asked for {c.full}, GitHub answered {full} at {url}")
    return view


def do_github(c: Ctx) -> None:
    if c.github_view is None:
        desc = ["--description", c.description] if c.description else []
        run(["gh", "repo", "create", c.full, "--private", *desc])
        # The receipt, written only once the create has returned success, is what lets a
        # rerun take an empty repository of this name as this project's.
        git(c.checkout, "config", "--local", RECEIPT_KEY, c.full)
    # Nothing is pushed until the repository reads back PRIVATE.
    view = require_private(gh_repo_view(c), c)
    if not has_origin(c):
        proto = run(["gh", "config", "get", "git_protocol", "--host", "github.com"],
                    check=False).stdout.strip()
        url = f"git@github.com:{c.full}.git" if proto == "ssh" else f"https://github.com/{c.full}.git"
        git(c.checkout, "remote", "add", "origin", url)
    if view.get("isEmpty"):
        # Push the bootstrap commit only: later local commits are the user's to push.
        root = c.report["root_commit"]
        git(c.checkout, "push", "-q", "origin", f"{root}:refs/heads/{BRANCH}")
        if git(c.checkout, "rev-parse", "--verify", "-q", f"refs/heads/{BRANCH}", check=False).returncode == 0:
            git(c.checkout, "branch", "-q", f"--set-upstream-to=origin/{BRANCH}", BRANCH, check=False)


def read_back_github(c: Ctx) -> None:
    view = require_private(gh_repo_view(c), c)
    full = view.get("nameWithOwner") or ""
    branch = (view.get("defaultBranchRef") or {}).get("name") or ""
    c.report["github"] = {
        "owner": full.split("/")[0], "repo": full, "url": (view.get("url") or "").rstrip("/"),
        "visibility": view.get("visibility"), "default_branch": branch,
    }
    if not branch:
        raise Fail(f"read-back: github.com/{c.full} has no default branch")
    if not remote_has_root(c):
        raise Fail(f"read-back: github.com/{c.full} does not hold the bootstrap commit")


def do_orca(c: Ctx) -> None:
    p = run(["orca", "repo", "add", "--path", str(c.checkout), "--kind", "git", "--json"])
    try:
        added = json.loads(p.stdout)["result"]["repo"]["id"]
    except (ValueError, KeyError, TypeError):
        added = None
    # The same rule as the check, so a registration the check would stop on fails here.
    state, detail, r = orca_match(c, orca_repos())
    if state != DONE:
        raise Fail(f"read-back after orca repo add: {detail}")
    c.report["orca_id"] = r.get("id")
    if not added or added != r.get("id"):
        raise Fail(f"read-back: orca repo add returned id {added}, the list has {r.get('id')}")


def do_section(c: Ctx) -> None:
    (c.sec / "memory").mkdir(parents=True, exist_ok=True)
    (c.sec / "inbox").mkdir(parents=True, exist_ok=True)


def do_memory(c: Ctx) -> None:
    m, sec_mem = c.harness / "memory", c.sec / "memory"
    if not os.path.lexists(c.harness):
        c.harness.mkdir(parents=True)  # fails if it appeared after the checks
        try:
            os.symlink(str(sec_mem), str(m))
        except BaseException:
            c.harness.rmdir()  # the empty folder this run just made
            raise
    elif m.is_dir() and not m.is_symlink():
        # One rename moves the folder and replaces the section's empty memory/ with it; the OS
        # refuses a non-empty target, and a failed rename changes nothing.
        os.rename(m, sec_mem)
        try:
            os.symlink(str(sec_mem), str(m))
        except BaseException:
            os.rename(sec_mem, m)  # put the folder back, and the section's empty memory/
            sec_mem.mkdir()
            raise
    else:
        os.symlink(str(sec_mem), str(m))
    if not memory_link_ok(c):
        raise Fail(f"read-back: {m} does not resolve to {sec_mem}")


# ---------------------------------------------------------------- main

def parse(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="new_project.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("name")
    ap.add_argument("--section", required=True, help="scriptorium section (required)")
    ap.add_argument("--owner", help="GitHub owner (default: the account gh is logged in as)")
    ap.add_argument("--description", help="one line for README.md, AGENTS.md and GitHub")
    ap.add_argument("--linear-project", help="Linear project named in AGENTS.md (default: <name>)")
    ap.add_argument("--dry-run", action="store_true", help="print every action in order, write nothing")
    ap.add_argument("--json", action="store_true", help="print the final report as JSON on stdout")
    a = ap.parse_args(argv)
    for label, v in (("name", a.name), ("--section", a.section)):
        if not NAME_RE.match(v) or v in (".", ".."):
            ap.error(f"{label} {v!r}: use letters, digits, '.', '_' and '-', starting with a letter or digit")
    if a.section == "david":
        ap.error("--section david is David's own section, not a project's")
    return a


def main(argv: list[str]) -> int:
    global JSON_MODE
    a = parse(argv)
    JSON_MODE = a.json
    c = Ctx(a)

    try:
        if not c.owner:
            c.owner = run(["gh", "api", "user", "--jq", ".login"], check=False).stdout.strip()
            if not c.owner:
                raise Blocked("could not read the GitHub login (`gh api user`); pass --owner")
        c.report["owner"] = c.owner
        s_checkout = check_checkout(c)
        s_github = check_github(c, s_checkout[0])
        s_orca = check_orca(c, s_checkout[0])
        s_section = check_section(c)
        s_memory = check_memory(c, s_checkout[0])
    except (Blocked, Fail, OSError) as e:
        say(f"FAILED before any write: {e}")
        c.report["error"] = str(e)
        if JSON_MODE:
            print(json.dumps(c.report, indent=2))
        return EXIT_FAIL

    steps = [
        ("checkout", s_checkout, do_checkout),
        ("github", s_github, lambda c: (do_github(c), read_back_github(c))),
        ("orca", s_orca, do_orca),
        ("section", s_section, do_section),
        ("memory", s_memory, do_memory),
    ]
    agent_steps = [
        ("linear-project", f"agent: use Linear project `{c.linear_project}`, creating it if none exists"),
        ("mergewren-ticket", f"agent: file the MergeWren onboarding ticket for {c.full} if none exists"),
    ]

    say(f"dv:new-project {c.name} --section {c.section}  ({'dry run' if c.dry_run else 'live'})")
    for i, (name, (state, detail), _) in enumerate(steps, 1):
        verb = {DONE: "done, skip", TODO: "would" if c.dry_run else "todo", STOP: "STOP"}[state]
        say(f"  {i}. {name:<9} {verb}: {detail}")
    for j, (name, detail) in enumerate(agent_steps, len(steps) + 1):
        say(f"  {j}. {name:<9} {detail}")
    c.report["plan"] = [{"step": n, "state": s, "detail": d} for n, (s, d), _ in steps]

    stops = [(n, d) for n, (s, d), _ in steps if s == STOP]
    if stops:
        say("")
        for n, d in stops:
            say(f"STOP ({n}): {d}")
        say("Nothing was written. Resolve the collision, or pick another name or section.")
        c.report["stopped"] = [{"step": n, "detail": d} for n, d in stops]
        if JSON_MODE:
            print(json.dumps(c.report, indent=2))
        return EXIT_STOP

    if c.dry_run:
        say("\nDry run: nothing was written.")
        if JSON_MODE:
            print(json.dumps(c.report, indent=2))
        return EXIT_OK

    c.report["did"] = []
    try:
        for name, (state, _), action in steps:
            if state == TODO:
                say(f"-> {name}")
                action(c)
                c.report["did"].append(name)
            elif name == "github":
                read_back_github(c)
    except (Fail, Blocked, OSError) as e:
        say(f"FAILED at {name}: {e}")
        say(f"Done before the failure: {', '.join(c.report['did']) or 'nothing'}. "
            "Fix the cause and run the same command again; it does only what is missing, "
            "or stops and says why.")
        c.report["error"] = f"{name}: {e}"
        if JSON_MODE:
            print(json.dumps(c.report, indent=2))
        return EXIT_FAIL

    g = c.report.get("github", {})
    say("")
    say("Report")
    say(f"  repository: {g.get('url')} ({g.get('visibility')}, default branch {g.get('default_branch')})")
    say(f"  path:       {c.checkout}")
    say(f"  orca id:    {c.report.get('orca_id')}")
    say(f"  section:    {c.sec} (memory: {c.harness / 'memory'} -> {c.sec / 'memory'})")
    say(f"  did:        {', '.join(c.report['did']) or 'nothing (everything was already done)'}")
    say(f"  next:       Linear project `{c.linear_project}` and the MergeWren onboarding ticket (agent)")
    if JSON_MODE:
        print(json.dumps(c.report, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
