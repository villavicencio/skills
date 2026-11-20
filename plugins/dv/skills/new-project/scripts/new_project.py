#!/usr/bin/env python3
"""dv:new-project, the local half: checkout, private GitHub repository, Orca, vault section.

    python3 new_project.py <name> --section <section> [--owner <login>] [--description <text>]
                           [--linear-project <name>] [--dry-run] [--json]

Steps, in order:
  1. checkout  ~/Projects/<name>, one bootstrap commit (AGENTS.md, CLAUDE.md, README.md,
               .gitignore, docs/discovery.md). AGENTS.md has the `## Vault` section.
  2. github    <owner>/<name>, created with --private, pushed, then read back. A read-back
               that is not PRIVATE fails the run.
  3. orca      `orca repo add --path <checkout> --kind git --json`, read back with
               `orca repo list --json`.
  4. section   ~/Obsidian/scriptorium/<section>/memory and /inbox.
  5. memory    ~/.claude/projects/<slug>/ (created when missing) and its `memory`, a symlink
               to the section's memory/. A real memory/ folder's files move into the section;
               a name in both folders is a collision.
The Linear project and the MergeWren onboarding ticket are the agent's steps (SKILL.md); the
plan lists them last so a dry run shows the whole order.

Every check runs before the first write. A step already done is skipped, so a second run
after a full one writes nothing and a run after a partial one does only what is missing.
Anything at a target that this tool did not make, or that belongs to another project, is a
collision: the run stops before writing anything.

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
    entries = [e for e in os.listdir(p) if e != ".DS_Store"]
    if not entries:
        return TODO, f"create the bootstrap commit in the empty folder {p}"
    if not (p / ".git").exists():
        return STOP, f"{p} already holds files and is not a git repository made by dv:new-project"
    roots = git(p, "rev-list", "--max-parents=0", "HEAD", check=False)
    if roots.returncode != 0 or not roots.stdout.strip():
        return STOP, f"{p} is a git repository with no commits; dv:new-project did not make it"
    root = roots.stdout.split()[-1]
    msg = git(p, "log", "-1", "--format=%B", root).stdout
    if MARKER not in msg or f"Project: {c.name}" not in msg:
        return STOP, f"{p} is a git repository that dv:new-project did not make (root {root[:7]})"
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
    return has.returncode == 0 and has.stdout.strip() == root


def check_github(c: Ctx, checkout_state: str) -> tuple[str, str]:
    view = gh_repo_view(c)
    c.github_view = view
    if view is None:
        return TODO, f"create {c.full} with --private, push, read back visibility"
    if checkout_state != DONE:
        return STOP, f"github.com/{c.full} already exists and this run did not make it"
    if view.get("visibility") != "PRIVATE":
        return STOP, f"github.com/{c.full} exists and is {view.get('visibility')}, not PRIVATE"
    if view.get("isEmpty"):
        return TODO, f"push the bootstrap commit to the existing, empty github.com/{c.full}"
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


def check_orca(c: Ctx, checkout_state: str) -> tuple[str, str]:
    want_key = f"github.com/{c.full}".lower()
    for r in orca_repos():
        path = r.get("path") or ""
        key = ((r.get("gitRemoteIdentity") or {}).get("canonicalKey") or "").lower()
        if same_path(path, c.checkout):
            if checkout_state != DONE:
                return STOP, f"Orca already has a project at {path} (id {r.get('id')}), before this run made it"
            if r.get("kind", "git") != "git":
                return STOP, f"Orca has {path} registered as kind {r.get('kind')}, not git"
            c.report["orca_id"] = r.get("id")
            return DONE, f"Orca has {path} (id {r.get('id')})"
        if key and key == want_key:
            return STOP, f"Orca already has github.com/{c.full} at another path: {path} (id {r.get('id')})"
    return TODO, f"orca repo add --path {c.checkout} --kind git --json, read back with orca repo list"


def section_is_scaffold(sec: Path) -> bool:
    """True when the section holds nothing but empty memory/ and inbox/ folders."""
    for e in os.listdir(sec):
        if e == ".DS_Store":
            continue
        q = sec / e
        if e not in ("memory", "inbox") or q.is_symlink() or not q.is_dir():
            return False
        if [x for x in os.listdir(q) if x != ".DS_Store"]:
            return False
    return True


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
    if not memory_link_ok(c) and not section_is_scaffold(c.sec):
        return STOP, f"section {c.sec} already has content and isn't this project's"
    if (c.sec / "memory").is_dir() and (c.sec / "inbox").is_dir():
        return DONE, f"{c.sec} has memory/ and inbox/"
    return TODO, f"mkdir the missing memory/ or inbox/ in {c.sec}"


def check_memory(c: Ctx) -> tuple[str, str]:
    h, m = c.harness, c.harness / "memory"
    if os.path.lexists(h) and (h.is_symlink() or not h.is_dir()):
        return STOP, f"{h} exists and is not a folder"
    if m.is_symlink():
        if memory_link_ok(c):
            return DONE, f"{m} -> {c.sec / 'memory'}"
        return STOP, f"{m} already links to {os.readlink(m)}"
    if not os.path.lexists(m):
        made = "" if h.is_dir() else f"mkdir {h}; "
        return TODO, f"{made}ln -s {c.sec / 'memory'} {m}"
    if not m.is_dir():
        return STOP, f"{m} exists and is not a folder or a link"
    entries = sorted(os.listdir(m))
    clash = [e for e in entries if os.path.lexists(c.sec / "memory" / e)]
    if clash:
        return STOP, f"{m} and {c.sec / 'memory'} both hold {', '.join(clash)}"
    return TODO, f"move {len(entries)} file(s) from {m} into {c.sec / 'memory'}, then link it"


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
        if c.checkout.is_dir():
            # The checks allowed only an empty folder (or one holding .DS_Store) here. rmdir
            # refuses a folder that gained files since, so nothing else is removed.
            if (c.checkout / ".DS_Store").is_file():
                (c.checkout / ".DS_Store").unlink()
            c.checkout.rmdir()
        os.rename(tmp, c.checkout)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    c.report["root_commit"] = git(c.checkout, "rev-list", "--max-parents=0", "HEAD").stdout.split()[-1]


def do_github(c: Ctx) -> None:
    origin = has_origin(c)
    if c.github_view is None:
        desc = ["--description", c.description] if c.description else []
        if origin:
            run(["gh", "repo", "create", c.full, "--private", *desc])
        else:
            run(["gh", "repo", "create", c.full, "--private", *desc, "--source", str(c.checkout),
                 "--remote", "origin", "--push"])
            return
    elif not origin:
        proto = run(["gh", "config", "get", "git_protocol", "--host", "github.com"],
                    check=False).stdout.strip()
        url = f"git@github.com:{c.full}.git" if proto == "ssh" else f"https://github.com/{c.full}.git"
        git(c.checkout, "remote", "add", "origin", url)
    if not remote_has_root(c):
        git(c.checkout, "push", "-q", "--set-upstream", "origin", "HEAD")


def read_back_github(c: Ctx) -> None:
    view = gh_repo_view(c)
    if view is None:
        raise Fail(f"read-back: github.com/{c.full} does not exist after the create")
    c.report["github"] = {
        "owner": c.owner, "repo": view.get("nameWithOwner"), "url": view.get("url"),
        "visibility": view.get("visibility"),
        "default_branch": (view.get("defaultBranchRef") or {}).get("name"),
    }
    if view.get("visibility") != "PRIVATE":
        raise Fail(f"read-back: github.com/{c.full} is {view.get('visibility')}, not PRIVATE. "
                   f"Make it private now (gh repo edit {c.full} --visibility private "
                   f"--accept-visibility-change-consequences) and tell David")
    if not remote_has_root(c):
        raise Fail(f"read-back: github.com/{c.full} does not hold the bootstrap commit")


def do_orca(c: Ctx) -> None:
    p = run(["orca", "repo", "add", "--path", str(c.checkout), "--kind", "git", "--json"])
    try:
        added = json.loads(p.stdout)["result"]["repo"].get("id")
    except (ValueError, KeyError, TypeError, AttributeError):
        added = None
    found = [r for r in orca_repos() if same_path(r.get("path") or "", c.checkout)]
    if not found:
        raise Fail(f"read-back: `orca repo list --json` has no project at {c.checkout}")
    c.report["orca_id"] = found[0].get("id")
    if added and added != c.report["orca_id"]:
        raise Fail(f"read-back: orca repo add returned id {added}, the list has {c.report['orca_id']}")


def do_section(c: Ctx) -> None:
    (c.sec / "memory").mkdir(parents=True, exist_ok=True)
    (c.sec / "inbox").mkdir(parents=True, exist_ok=True)


def do_memory(c: Ctx) -> None:
    m = c.harness / "memory"
    c.harness.mkdir(parents=True, exist_ok=True)
    if m.is_dir() and not m.is_symlink():
        for e in sorted(os.listdir(m)):
            target = c.sec / "memory" / e
            if os.path.lexists(target):
                raise Fail(f"{target} appeared after the checks; stopping before overwriting it")
            shutil.move(str(m / e), str(target))
        m.rmdir()
    os.symlink(str(c.sec / "memory"), str(m))
    if not memory_link_ok(c):
        raise Fail(f"read-back: {m} does not resolve to {c.sec / 'memory'}")


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
        s_memory = check_memory(c)
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
            "Fix the cause and run the same command again; it does only what is missing.")
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
