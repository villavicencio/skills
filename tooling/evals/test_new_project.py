#!/usr/bin/env python3
"""Runs dv:new-project's script against throwaway folders with `gh` and `orca` stubbed.

The script creates a GitHub repository, an Orca registration and a memory symlink, so these
checks never let it near the real ones. Each case gets its own temp root holding:

  home/        HOME for the run: Projects/, Obsidian/scriptorium/ (with .obsidian/), .claude/
  remotes/     bare git repositories standing in for GitHub; git's url.insteadOf maps
               https://github.com/ here, so the script's real `git push` lands in them
  bin/         stub `gh` and `orca` (Python), first on PATH; anything they don't know exits 99
  state.json   the stubs' GitHub and Orca state; log.jsonl  every stub call, one per line

Checked (the ticket's Done means, plus the partial-run and memory-folder cases):
  - a run without --section exits non-zero before any write or stub call
  - --dry-run changes nothing on disk and makes no create call, and lists every step in order
  - a full run creates the checkout, the private repository, the Orca entry, the section and
    the memory link; `gh repo create` gets --private and never --public
  - a stubbed read-back of PUBLIC fails the run, and nothing after the GitHub step happens
  - a second run after a full run changes nothing and makes no create call
  - after a failure (Orca add, or gh dying right after the create) the next run does only the
    missing steps
  - a collision at the checkout, the GitHub repository, the Orca registration or the section
    exits non-zero with nothing written and no create call
  - a ~/Projects folder sharing the harness slug, or a real memory/ folder with no session
    from this checkout, stops the run with nothing written
  - a check that can't run (`orca repo list` or `gh api` failing) exits 1 with nothing written
  - nothing is pushed before visibility reads back PRIVATE, only the bootstrap commit is pushed,
    and a read-back naming another repository fails the run

Stdlib only, no network. Needs git.

    python3 tooling/evals/test_new_project.py [path/to/new_project.py]

Exits non-zero on any failure. The optional path lets you prove a check is load-bearing:
point it at a copy of the script with that guard removed and the check fails.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else
          REPO_ROOT / "plugins" / "dv" / "skills" / "new-project" / "scripts" / "new_project.py")
NAME, SECTION, LOGIN = "demo", "demo-notes", "tester"
CREATE_CALLS = (("gh", "repo", "create"), ("orca", "repo", "add"))

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name)
    if not ok:
        failures.append(name + (f"\n     {detail}" if detail else ""))


# ---------------------------------------------------------------- stubs

GH_STUB = r'''#!/usr/bin/env python3
import json, os, subprocess, sys
state_path, log_path = os.environ["STUB_STATE"], os.environ["STUB_LOG"]
remotes = os.environ["STUB_REMOTES"]
argv = sys.argv[1:]
with open(log_path, "a") as f:
    f.write(json.dumps(["gh"] + argv) + "\n")
st = json.load(open(state_path))
def save(): json.dump(st, open(state_path, "w"), indent=1)
def git(*a, **k): return subprocess.run(["git", *a], capture_output=True, text=True, **k)
def bare(full): return os.path.join(remotes, full + ".git")
def missing(full):
    sys.stderr.write(f"GraphQL: Could not resolve to a Repository with the name '{full}'. (repository)\n")
    sys.exit(1)

if argv[:2] == ["api", "user"]:
    print(st["login"]); sys.exit(0)
if argv[:1] == ["api"] and argv[1].startswith("repos/") and "/commits/" in argv[1]:
    full, sha = argv[1][len("repos/"):].split("/commits/")
    if st.get("fail_commits_api"):
        sys.stderr.write("gh: Bad Gateway (HTTP 502)\n"); sys.exit(1)
    if full in st["repos"] and not git("-C", bare(full), "for-each-ref", "refs/heads").stdout.strip():
        sys.stderr.write("gh: Git Repository is empty. (HTTP 409)\n"); sys.exit(1)
    if full in st["repos"] and git("-C", bare(full), "cat-file", "-e", sha + "^{commit}").returncode == 0:
        print(git("-C", bare(full), "rev-parse", sha).stdout.strip()); sys.exit(0)
    sys.stderr.write(f"gh: No commit found for SHA: {sha} (HTTP 422)\n"); sys.exit(1)
if argv[:2] == ["config", "get"] and argv[2] == "git_protocol":
    print("https"); sys.exit(0)
if argv[:2] == ["repo", "view"]:
    full = argv[2]
    if full not in st["repos"]:
        missing(full)
    b = bare(full)
    heads = git("-C", b, "for-each-ref", "refs/heads").stdout.strip()
    head = git("-C", b, "symbolic-ref", "--short", "HEAD").stdout.strip() if heads else ""
    shown = st.get("force_name") or full
    print(json.dumps({"nameWithOwner": shown, "url": "https://github.com/" + shown,
                      "visibility": st.get("force_visibility") or st["repos"][full]["visibility"],
                      "defaultBranchRef": {"name": head}, "isEmpty": not heads}))
    sys.exit(0)
if argv[:2] == ["repo", "create"]:
    full = argv[2]
    if st.get("fail_create_before"):
        sys.stderr.write("HTTP 502: stubbed failure\n"); sys.exit(1)
    if full in st["repos"]:
        sys.stderr.write("GraphQL: Name already exists on this account (createRepository)\n"); sys.exit(1)
    vis = "PRIVATE" if "--private" in argv else "PUBLIC" if "--public" in argv else None
    if vis is None:
        sys.stderr.write("stub: no visibility flag\n"); sys.exit(1)
    os.makedirs(os.path.dirname(bare(full)), exist_ok=True)
    git("init", "-q", "--bare", "-b", "main", bare(full))
    st["repos"][full] = {"visibility": vis}
    save()
    if st.pop("fail_create_after", False):
        save(); sys.stderr.write("stub: died after the create\n"); sys.exit(1)
    if "--source" in argv:
        src = argv[argv.index("--source") + 1]
        remote = argv[argv.index("--remote") + 1] if "--remote" in argv else "origin"
        r = git("-C", src, "remote", "add", remote, "https://github.com/" + full + ".git")
        if r.returncode: sys.stderr.write(r.stderr); sys.exit(1)
        if "--push" in argv:
            r = git("-C", src, "push", "-q", "--set-upstream", remote, "HEAD")
            if r.returncode: sys.stderr.write(r.stderr); sys.exit(1)
    print("https://github.com/" + full); sys.exit(0)
sys.stderr.write("stub gh: unsupported call " + json.dumps(argv) + "\n"); sys.exit(99)
'''

ORCA_STUB = r'''#!/usr/bin/env python3
import json, os, re, subprocess, sys, uuid
state_path, log_path = os.environ["STUB_STATE"], os.environ["STUB_LOG"]
argv = sys.argv[1:]
with open(log_path, "a") as f:
    f.write(json.dumps(["orca"] + argv) + "\n")
st = json.load(open(state_path))
if argv == ["repo", "list", "--json"]:
    if st.get("fail_orca_list"):
        sys.stderr.write("Error: Orca runtime is not reachable (stubbed)\n"); sys.exit(1)
    print(json.dumps({"id": str(uuid.uuid4()), "ok": True, "result": {"repos": st["orca"]}}, indent=2))
    sys.exit(0)
if argv[:2] == ["repo", "add"] and "--json" in argv:
    if st.get("fail_orca_add"):
        sys.stderr.write("Error: Orca runtime is not reachable (stubbed)\n"); sys.exit(1)
    path = argv[argv.index("--path") + 1]
    if subprocess.run(["git", "-C", path, "rev-parse", "--git-dir"], capture_output=True).returncode:
        sys.stderr.write("Not a valid git repository: " + path + "\n"); sys.exit(1)
    url = subprocess.run(["git", "-C", path, "config", "--get", "remote.origin.url"],
                         capture_output=True, text=True).stdout.strip()
    key = re.sub(r"\.git$", "", re.sub(r"^https://", "", url)).lower() if url else None
    entry = {"id": str(uuid.uuid4()), "path": path, "displayName": os.path.basename(path),
             "kind": "git", "gitRemoteIdentity": {"canonicalKey": key, "remoteName": "origin",
                                                  "remoteUrl": url} if key else None}
    st["orca"].append(entry)
    json.dump(st, open(state_path, "w"), indent=1)
    print(json.dumps({"id": str(uuid.uuid4()), "ok": True, "result": {"repo": entry}}, indent=2))
    sys.exit(0)
sys.stderr.write("stub orca: unsupported call " + json.dumps(argv) + "\n"); sys.exit(99)
'''


class Sandbox:
    def __init__(self, root: Path):
        self.root = root
        self.home = root / "home"
        self.remotes = root / "remotes"
        self.bin = root / "bin"
        self.state = root / "state.json"
        self.log = root / "log.jsonl"
        for d in (self.home / "Projects", self.home / "Obsidian" / "scriptorium" / ".obsidian",
                  self.home / ".claude" / "projects", self.remotes, self.bin):
            d.mkdir(parents=True, exist_ok=True)
        (self.bin / "gh").write_text(GH_STUB)
        (self.bin / "orca").write_text(ORCA_STUB)
        for s in ("gh", "orca"):
            (self.bin / s).chmod(0o755)
        self.gitconfig = root / "gitconfig"
        self.gitconfig.write_text(
            "[user]\n\tname = Test\n\temail = test@example.invalid\n"
            "[init]\n\tdefaultBranch = main\n"
            f'[url "file://{self.remotes}/"]\n\tinsteadOf = https://github.com/\n')
        self.write_state({"login": LOGIN, "repos": {}, "orca": []})
        self.log.write_text("")

    def write_state(self, st: dict) -> None:
        self.state.write_text(json.dumps(st, indent=1))

    def read_state(self) -> dict:
        return json.loads(self.state.read_text())

    def env(self) -> dict[str, str]:
        git_dir = os.path.dirname(shutil.which("git") or "/usr/bin/git")
        py_dir = os.path.dirname(sys.executable)
        return {
            "PATH": os.pathsep.join([str(self.bin), git_dir, py_dir, "/usr/bin", "/bin"]),
            "HOME": str(self.home),
            "GIT_CONFIG_GLOBAL": str(self.gitconfig),
            "GIT_CONFIG_NOSYSTEM": "1",
            "STUB_STATE": str(self.state),
            "STUB_LOG": str(self.log),
            "STUB_REMOTES": str(self.remotes),
            "LANG": "C.UTF-8",
            # The Mac's /usr/bin/python3 (3.9) caches bytecode under ~/Library/Caches, which
            # would show up as a write in the snapshot. The script itself writes nothing there.
            "PYTHONDONTWRITEBYTECODE": "1",
        }

    def run(self, *args: str) -> tuple[subprocess.CompletedProcess, list[list[str]], dict]:
        """Run the script with --json; return the process, this run's stub calls, the report."""
        before = len(self.calls())
        p = subprocess.run([sys.executable, str(SCRIPT), *args, "--json"], env=self.env(),
                           capture_output=True, text=True, timeout=120)
        try:
            report = json.loads(p.stdout) if p.stdout.strip() else {}
        except ValueError:
            report = {}
        return p, self.calls()[before:], report

    def calls(self) -> list[list[str]]:
        return [json.loads(l) for l in self.log.read_text().splitlines() if l.strip()]

    def snapshot(self) -> dict[str, str]:
        """Every path under home/ and remotes/: type, link target or content hash."""
        snap: dict[str, str] = {}
        for base in (self.home, self.remotes):
            for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
                for n in dirnames + filenames:
                    p = Path(dirpath) / n
                    rel = str(p.relative_to(self.root))
                    if p.is_symlink():
                        snap[rel] = "link:" + os.readlink(p)
                    elif p.is_dir():
                        snap[rel] = "dir"
                    else:
                        snap[rel] = "file:" + hashlib.sha256(p.read_bytes()).hexdigest()
        return snap

    @property
    def checkout(self) -> Path:
        return self.home / "Projects" / NAME

    @property
    def section(self) -> Path:
        return self.home / "Obsidian" / "scriptorium" / SECTION

    @property
    def harness(self) -> Path:
        slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(self.home / "Projects") + "/" + NAME)
        return self.home / ".claude" / "projects" / slug


def creates(calls: list[list[str]]) -> list[list[str]]:
    return [c for c in calls if tuple(c[:3]) in CREATE_CALLS]


def git_out(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout


def sandbox() -> tuple[Sandbox, tempfile.TemporaryDirectory]:
    td = tempfile.TemporaryDirectory(prefix="dv-new-project-test-")
    return Sandbox(Path(td.name).resolve()), td


def ok_run(sb: Sandbox, label: str, *extra: str) -> dict:
    p, _, report = sb.run(NAME, "--section", SECTION, *extra)
    check(f"{label}: exit 0", p.returncode == 0, p.stderr[-1500:])
    return report


def expect_stop(label: str, sb: Sandbox, *args: str, code: int = 3) -> None:
    before = sb.snapshot()
    p, calls, report = sb.run(*(args or (NAME, "--section", SECTION)))
    check(f"{label}: exits {code}", p.returncode == code, f"exit {p.returncode}\n{p.stderr[-1500:]}")
    check(f"{label}: nothing written", sb.snapshot() == before)
    check(f"{label}: no create call", not creates(calls), str(creates(calls)))


# ---------------------------------------------------------------- cases

def test_missing_section() -> None:
    sb, td = sandbox()
    with td:
        before = sb.snapshot()
        p, calls, _ = sb.run(NAME)
        check("no --section: exits non-zero", p.returncode != 0 and p.returncode == 2,
              f"exit {p.returncode}")
        check("no --section: says --section is required", "--section" in p.stderr, p.stderr)
        check("no --section: nothing written", sb.snapshot() == before)
        check("no --section: no stub call at all", calls == [], str(calls))


def test_dry_run_fresh() -> None:
    sb, td = sandbox()
    with td:
        before = sb.snapshot()
        p, calls, report = sb.run(NAME, "--section", SECTION, "--dry-run")
        check("dry run: exit 0", p.returncode == 0, p.stderr[-1500:])
        check("dry run: temp folders unchanged", sb.snapshot() == before)
        check("dry run: no create call", not creates(calls), str(creates(calls)))
        check("dry run: no push or write-like stub call",
              all(c[:2] in (["gh", "api"], ["gh", "repo"], ["orca", "repo"]) and
                  c[:3] != ["gh", "repo", "create"] for c in calls), str(calls))
        order = ["checkout", "github", "orca", "section", "memory", "linear-project", "mergewren-ticket"]
        idx = [p.stderr.find(f"{i}. {s}") for i, s in enumerate(order, 1)]
        check("dry run: prints every step, in order", all(i >= 0 for i in idx) and idx == sorted(idx),
              p.stderr)
        check("dry run: every local step planned as todo",
              [s["state"] for s in report.get("plan", [])] == ["todo"] * 5, str(report.get("plan")))


def test_full_then_idempotent() -> None:
    sb, td = sandbox()
    with td:
        check("fresh: harness project folder absent before the run", not sb.harness.exists())
        p, calls, report = sb.run(NAME, "--section", SECTION)
        check("full run: exit 0", p.returncode == 0, p.stderr[-2000:])
        made = creates(calls)
        gh_create = [c for c in made if c[:3] == ["gh", "repo", "create"]]
        check("full run: one gh repo create", len(gh_create) == 1, str(made))
        check("full run: created with --private", bool(gh_create) and "--private" in gh_create[0])
        check("full run: never --public", not any("--public" in c for c in calls))
        check("full run: one orca repo add with --kind git",
              [c for c in made if c[:3] == ["orca", "repo", "add"]] ==
              [["orca", "repo", "add", "--path", str(sb.checkout), "--kind", "git", "--json"]], str(made))
        add_at = next((i for i, c in enumerate(calls) if c[:3] == ["orca", "repo", "add"]), None)
        check("full run: read back orca with repo list after the add",
              add_at is not None and ["orca", "repo", "list", "--json"] in calls[add_at + 1:])
        files = sorted(git_out(sb.checkout, "ls-files").split())
        check("full run: bootstrap commit has exactly the five files",
              files == [".gitignore", "AGENTS.md", "CLAUDE.md", "README.md", "docs/discovery.md"], str(files))
        msg = git_out(sb.checkout, "log", "-1", "--format=%B")
        check("full run: bootstrap commit carries the marker",
              "Bootstrapped-by: dv:new-project" in msg and f"Project: {NAME}" in msg, msg)
        agents = (sb.checkout / "AGENTS.md").read_text()
        check("full run: AGENTS.md has a ## Vault section naming the section",
              re.search(r"^## Vault\n.*`" + re.escape(SECTION) + "`", agents, re.M | re.S) is not None, agents)
        check("full run: CLAUDE.md imports AGENTS.md",
              "@AGENTS.md" in (sb.checkout / "CLAUDE.md").read_text())
        bare = sb.remotes / LOGIN / f"{NAME}.git"
        check("full run: commit pushed to the (stub) GitHub repository",
              git_out(bare, "rev-parse", "main").strip() == git_out(sb.checkout, "rev-parse", "HEAD").strip())
        check("full run: local main tracks origin/main",
              git_out(sb.checkout, "rev-parse", "--abbrev-ref", "main@{u}").strip() == "origin/main")
        st = sb.read_state()
        check("full run: stub repository is PRIVATE", st["repos"].get(f"{LOGIN}/{NAME}", {}).get("visibility") == "PRIVATE")
        check("full run: Orca has the checkout", [r["path"] for r in st["orca"]] == [str(sb.checkout)])
        check("full run: report has the Orca id", report.get("orca_id") == (st["orca"] or [{}])[0].get("id"))
        g = report.get("github", {})
        check("full run: report reads back owner, URL, visibility, default branch",
              g.get("owner") == LOGIN and g.get("url") == f"https://github.com/{LOGIN}/{NAME}"
              and g.get("visibility") == "PRIVATE" and g.get("default_branch") == "main", str(g))
        check("full run: section memory/ and inbox/ exist",
              (sb.section / "memory").is_dir() and (sb.section / "inbox").is_dir())
        m = sb.harness / "memory"
        check("full run: harness project folder created", sb.harness.is_dir())
        check("full run: harness memory is a symlink to the section's memory/",
              m.is_symlink() and os.path.realpath(m) == os.path.realpath(sb.section / "memory"))
        check("full run: nothing named .obsidian under the section",
              not any(p.name == ".obsidian" for p in sb.section.rglob("*")))
        check("full run: no temp folder left in ~/Projects",
              sorted(os.listdir(sb.home / "Projects")) == [NAME], str(os.listdir(sb.home / "Projects")))

        before = sb.snapshot()
        p, calls, report = sb.run(NAME, "--section", SECTION)
        check("second run: exit 0", p.returncode == 0, p.stderr[-1500:])
        check("second run: no create call", not creates(calls), str(creates(calls)))
        check("second run: nothing changed on disk", sb.snapshot() == before)
        check("second run: every step reported done",
              [s["state"] for s in report.get("plan", [])] == ["done"] * 5 and report.get("did") == [],
              str(report.get("plan")))
        check("second run: still reads back PRIVATE", report.get("github", {}).get("visibility") == "PRIVATE")

        p, calls, _ = sb.run(NAME, "--section", SECTION, "--dry-run")
        check("dry run after a full run: exit 0, no create call, nothing changed",
              p.returncode == 0 and not creates(calls) and sb.snapshot() == before)

        expect_stop("rerun with another --section", sb, NAME, "--section", "other-notes")

        # Later local work is the user's to push: a rerun must not push it.
        (sb.checkout / "later.txt").write_text("work in progress\n")
        subprocess.run(["git", "-C", str(sb.checkout), "add", "later.txt"], env=sb.env(), check=True)
        subprocess.run(["git", "-C", str(sb.checkout), "commit", "-qm", "later"], env=sb.env(), check=True)
        bare = sb.remotes / LOGIN / f"{NAME}.git"
        remote_before = git_out(bare, "rev-parse", "main")
        p, calls, report = sb.run(NAME, "--section", SECTION)
        check("rerun after later local commits: exit 0, nothing done",
              p.returncode == 0 and report.get("did") == [] and not creates(calls), p.stderr[-1500:])
        check("rerun after later local commits: nothing pushed",
              git_out(bare, "rev-parse", "main") == remote_before)


def test_public_readback_fails() -> None:
    sb, td = sandbox()
    with td:
        st = sb.read_state(); st["force_visibility"] = "PUBLIC"; sb.write_state(st)
        p, calls, report = sb.run(NAME, "--section", SECTION)
        check("PUBLIC read-back: run fails", p.returncode == 1, f"exit {p.returncode}")
        check("PUBLIC read-back: error names PUBLIC", "PUBLIC" in report.get("error", ""), str(report))
        gh_create = [c for c in calls if c[:3] == ["gh", "repo", "create"]]
        check("PUBLIC read-back: the create still asked for --private",
              len(gh_create) == 1 and "--private" in gh_create[0], str(gh_create))
        check("PUBLIC read-back: no Orca add after it", not any(c[:3] == ["orca", "repo", "add"] for c in calls))
        bare = sb.remotes / LOGIN / f"{NAME}.git"
        check("PUBLIC read-back: nothing pushed to the repository",
              git_out(bare, "for-each-ref", "refs/heads").strip() == "")
        check("PUBLIC read-back: no section, no memory link",
              not sb.section.exists() and not os.path.lexists(sb.harness / "memory"))
        # A rerun sees an existing PUBLIC repository and stops before writing anything.
        expect_stop("rerun on a PUBLIC repository", sb)


def test_partial_orca_failure() -> None:
    sb, td = sandbox()
    with td:
        st = sb.read_state(); st["fail_orca_add"] = True; sb.write_state(st)
        p, _, report = sb.run(NAME, "--section", SECTION)
        check("partial (orca fails): run fails", p.returncode == 1, f"exit {p.returncode}")
        check("partial (orca fails): checkout and repository made, section not",
              sb.checkout.is_dir() and f"{LOGIN}/{NAME}" in sb.read_state()["repos"] and not sb.section.exists())
        st = sb.read_state(); st["fail_orca_add"] = False; sb.write_state(st)
        p, calls, report = sb.run(NAME, "--section", SECTION)
        check("partial (orca fails) rerun: exit 0", p.returncode == 0, p.stderr[-1500:])
        check("partial (orca fails) rerun: no gh repo create",
              not any(c[:3] == ["gh", "repo", "create"] for c in calls), str(calls))
        check("partial (orca fails) rerun: one orca repo add",
              len([c for c in calls if c[:3] == ["orca", "repo", "add"]]) == 1)
        check("partial (orca fails) rerun: did only orca, section, memory",
              report.get("did") == ["orca", "section", "memory"], str(report.get("did")))


def test_partial_gh_died_after_create() -> None:
    sb, td = sandbox()
    with td:
        st = sb.read_state(); st["fail_create_after"] = True; sb.write_state(st)
        p, _, _ = sb.run(NAME, "--section", SECTION)
        check("partial (gh died after create): run fails", p.returncode == 1, f"exit {p.returncode}")
        check("partial (gh died after create): no origin yet",
              git_out(sb.checkout, "remote").strip() == "")
        p, calls, report = sb.run(NAME, "--section", SECTION)
        check("partial (gh died after create) rerun: exit 0", p.returncode == 0, p.stderr[-1500:])
        check("partial (gh died after create) rerun: no second create",
              not any(c[:3] == ["gh", "repo", "create"] for c in calls), str(calls))
        bare = sb.remotes / LOGIN / f"{NAME}.git"
        check("partial (gh died after create) rerun: pushed to the existing repository",
              git_out(bare, "rev-parse", "main").strip() == git_out(sb.checkout, "rev-parse", "HEAD").strip())
        check("partial (gh died after create) rerun: did github onwards",
              report.get("did") == ["github", "orca", "section", "memory"], str(report.get("did")))


def test_partial_empty_remote_pushes_bootstrap_only() -> None:
    sb, td = sandbox()
    with td:
        st = sb.read_state(); st["fail_create_after"] = True; sb.write_state(st)
        sb.run(NAME, "--section", SECTION)
        root = git_out(sb.checkout, "rev-parse", "HEAD").strip()
        (sb.checkout / "later.txt").write_text("work in progress\n")
        subprocess.run(["git", "-C", str(sb.checkout), "add", "later.txt"], env=sb.env(), check=True)
        subprocess.run(["git", "-C", str(sb.checkout), "commit", "-qm", "later"], env=sb.env(), check=True)
        p, _, _ = sb.run(NAME, "--section", SECTION)
        bare = sb.remotes / LOGIN / f"{NAME}.git"
        check("empty remote + later local commit: rerun exit 0", p.returncode == 0, p.stderr[-1500:])
        check("empty remote + later local commit: only the bootstrap commit is pushed",
              git_out(bare, "rev-parse", "main").strip() == root)


def test_github_check_errors() -> None:
    sb, td = sandbox()
    with td:
        ok_run(sb, "setup for a failing commits API")
        st = sb.read_state(); st["fail_commits_api"] = True; sb.write_state(st)
        expect_stop("gh api commits fails with a 502 (a check that can't run)", sb, code=1)
    sb, td = sandbox()
    with td:
        st = sb.read_state(); st["force_name"] = f"{LOGIN}/renamed"; sb.write_state(st)
        p, _, report = sb.run(NAME, "--section", SECTION)
        check("read-back names another repository: run fails", p.returncode == 1, f"exit {p.returncode}")
        check("read-back names another repository: nothing pushed",
              git_out(sb.remotes / LOGIN / f"{NAME}.git", "for-each-ref", "refs/heads").strip() == "")
        check("read-back names another repository: no Orca add",
              "orca" not in report.get("did", []), str(report.get("did")))


def test_collision_checkout() -> None:
    sb, td = sandbox()
    with td:
        sb.checkout.mkdir(parents=True)
        (sb.checkout / "notes.txt").write_text("someone else's\n")
        expect_stop("collision: checkout path holds other files", sb)
    sb, td = sandbox()
    with td:
        sb.checkout.mkdir(parents=True)
        expect_stop("collision: checkout path is an existing empty folder", sb)
    sb, td = sandbox()
    with td:
        sb.checkout.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(sb.checkout)], env=sb.env(), check=True)
        (sb.checkout / "x").write_text("x\n")
        subprocess.run(["git", "-C", str(sb.checkout), "add", "x"], env=sb.env(), check=True)
        subprocess.run(["git", "-C", str(sb.checkout), "commit", "-qm", "theirs"], env=sb.env(), check=True)
        expect_stop("collision: checkout path is another git repository", sb)


def seed_foreign_remote(sb: Sandbox) -> None:
    src = sb.root / "foreign"
    env = sb.env()
    subprocess.run(["git", "init", "-q", "-b", "main", str(src)], env=env, check=True)
    (src / "f").write_text("foreign\n")
    subprocess.run(["git", "-C", str(src), "add", "f"], env=env, check=True)
    subprocess.run(["git", "-C", str(src), "commit", "-qm", "foreign"], env=env, check=True)
    bare = sb.remotes / LOGIN / f"{NAME}.git"
    bare.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "-q", "--bare", str(src), str(bare)], env=env, check=True)
    shutil.rmtree(src)
    st = sb.read_state(); st["repos"][f"{LOGIN}/{NAME}"] = {"visibility": "PRIVATE"}; sb.write_state(st)


def test_collision_github() -> None:
    sb, td = sandbox()
    with td:
        seed_foreign_remote(sb)
        expect_stop("collision: GitHub repository exists, no local checkout", sb)
    sb, td = sandbox()
    with td:
        # A first run that made the checkout but whose create failed, then someone else's
        # repository of the same name appears: the rerun must not push into it.
        st = sb.read_state(); st["fail_create_before"] = True; sb.write_state(st)
        p, _, _ = sb.run(NAME, "--section", SECTION)
        check("setup: run with a failing create exits 1", p.returncode == 1, f"exit {p.returncode}")
        st = sb.read_state(); st["fail_create_before"] = False; sb.write_state(st)
        seed_foreign_remote(sb)
        expect_stop("collision: GitHub repository has history without our bootstrap commit", sb)


def test_collision_orca() -> None:
    sb, td = sandbox()
    with td:
        st = sb.read_state()
        st["orca"] = [{"id": "o-1", "path": str(sb.checkout), "displayName": NAME, "kind": "git"}]
        sb.write_state(st)
        expect_stop("collision: Orca already has a project at the checkout path", sb)
    sb, td = sandbox()
    with td:
        st = sb.read_state()
        st["orca"] = [{"id": "o-2", "path": str(sb.root / "elsewhere" / NAME), "displayName": NAME,
                       "kind": "git", "gitRemoteIdentity": {"canonicalKey": f"github.com/{LOGIN}/{NAME}"}}]
        sb.write_state(st)
        expect_stop("collision: Orca has the same GitHub repository at another path", sb)
    sb, td = sandbox()
    with td:
        ok_run(sb, "setup for Orca drift")
        st = sb.read_state()
        st["orca"][0]["gitRemoteIdentity"] = {"canonicalKey": "github.com/someone/else"}
        sb.write_state(st)
        expect_stop("collision: Orca's entry at the checkout is for another repository", sb)
    sb, td = sandbox()
    with td:
        ok_run(sb, "setup for an Orca duplicate")
        st = sb.read_state()
        st["orca"].append({"id": "o-3", "path": str(sb.root / "copy" / NAME), "kind": "git",
                           "gitRemoteIdentity": {"canonicalKey": f"github.com/{LOGIN}/{NAME}"}})
        sb.write_state(st)
        expect_stop("collision: a second Orca entry for the same repository", sb)


def test_check_cannot_run() -> None:
    sb, td = sandbox()
    with td:
        st = sb.read_state(); st["fail_orca_list"] = True; sb.write_state(st)
        expect_stop("a check can't run (orca repo list fails)", sb, code=1)


def test_collision_section() -> None:
    sb, td = sandbox()
    with td:
        (sb.section / "memory").mkdir(parents=True)
        (sb.section / "plan.md").write_text("another project's note\n")
        expect_stop("collision: section already has content", sb)
    sb, td = sandbox()
    with td:
        (sb.section / "memory").mkdir(parents=True)
        other = sb.home / ".claude" / "projects" / "-Users-x-Projects-other"
        other.mkdir(parents=True)
        os.symlink(sb.section / "memory", other / "memory")
        expect_stop("collision: section is another project's memory", sb)
    sb, td = sandbox()
    with td:
        shutil.rmtree(sb.home / "Obsidian" / "scriptorium" / ".obsidian")
        expect_stop("vault not set up (no .obsidian/)", sb)


def test_section_scaffold_and_memory_move() -> None:
    sb, td = sandbox()
    with td:
        # A run that stopped at Orca, then a session in the new checkout wrote memory: the
        # empty section scaffold is not a collision, and the real memory folder moves in.
        st = sb.read_state(); st["fail_orca_add"] = True; sb.write_state(st)
        sb.run(NAME, "--section", SECTION)
        st = sb.read_state(); st["fail_orca_add"] = False; sb.write_state(st)
        (sb.section / "memory").mkdir(parents=True)
        (sb.section / "inbox").mkdir()
        (sb.harness / "memory").mkdir(parents=True)
        (sb.harness / "memory" / "MEMORY.md").write_text("- a note\n")
        (sb.harness / "s1.jsonl").write_text(json.dumps({"cwd": str(sb.checkout)}) + "\n")
        ok_run(sb, "scaffold section + real memory folder")
        m = sb.harness / "memory"
        check("memory folder: replaced by a link to the section",
              m.is_symlink() and os.path.realpath(m) == os.path.realpath(sb.section / "memory"))
        check("memory folder: its file moved into the section",
              (sb.section / "memory" / "MEMORY.md").read_text() == "- a note\n")
    sb, td = sandbox()
    with td:
        st = sb.read_state(); st["fail_orca_add"] = True; sb.write_state(st)
        sb.run(NAME, "--section", SECTION)
        st = sb.read_state(); st["fail_orca_add"] = False; sb.write_state(st)
        (sb.section / "memory").mkdir(parents=True)
        (sb.section / "memory" / "MEMORY.md").write_text("section's\n")
        (sb.harness / "memory").mkdir(parents=True)
        (sb.harness / "memory" / "MEMORY.md").write_text("harness's\n")
        (sb.harness / "s1.jsonl").write_text(json.dumps({"cwd": str(sb.checkout)}) + "\n")
        expect_stop("collision: section memory already holds files, harness memory too", sb)


def test_collision_shared_slug() -> None:
    sb, td = sandbox()
    with td:
        # Names that differ only in '-', '_' or '.' share a slug. Another project's harness
        # folder that exists before this checkout does is not this project's.
        (sb.harness / "memory").mkdir(parents=True)
        (sb.harness / "memory" / "MEMORY.md").write_text("another project's memory\n")
        expect_stop("collision: harness folder exists before the checkout", sb)
    sb, td = sandbox()
    with td:
        ok_run(sb, "setup for a shared slug")
        (sb.harness / "s2.jsonl").write_text(
            json.dumps({"cwd": str(sb.home / "Projects" / "demo_x")}) + "\n")
        expect_stop("collision: harness folder holds another checkout's sessions", sb)


def test_memory_guard() -> None:
    sb, td = sandbox()
    with td:
        # foo_bar and foo-bar share a harness folder name: the second project stops.
        (sb.home / "Projects" / "foo_bar").mkdir()
        (sb.home / "Projects" / "foo_bar" / "notes.txt").write_text("another project\n")
        expect_stop("collision: another ~/Projects folder shares the harness slug", sb,
                    "foo-bar", "--section", SECTION)
    sb, td = sandbox()
    with td:
        # The checkout is ours (an earlier run stopped at Orca), but the real memory folder has
        # no session file from this checkout: it is not moved.
        st = sb.read_state(); st["fail_orca_add"] = True; sb.write_state(st)
        sb.run(NAME, "--section", SECTION)
        st = sb.read_state(); st["fail_orca_add"] = False; sb.write_state(st)
        (sb.harness / "memory").mkdir(parents=True)
        (sb.harness / "memory" / "MEMORY.md").write_text("whose?\n")
        expect_stop("memory folder with no session from this checkout is not moved", sb)
        check("memory folder with no session from this checkout: still in place",
              (sb.harness / "memory" / "MEMORY.md").read_text() == "whose?\n"
              and not (sb.section / "memory" / "MEMORY.md").exists())


def main() -> int:
    if not SCRIPT.is_file():
        print(f"FAILED: {SCRIPT} not found")
        return 1
    for t in (test_missing_section, test_dry_run_fresh, test_full_then_idempotent,
              test_public_readback_fails, test_partial_orca_failure,
              test_partial_gh_died_after_create, test_partial_empty_remote_pushes_bootstrap_only,
              test_github_check_errors, test_collision_checkout, test_collision_github,
              test_collision_orca, test_check_cannot_run, test_collision_section, test_collision_shared_slug, test_memory_guard,
              test_section_scaffold_and_memory_move):
        print(f"--- {t.__name__}")
        t()
    if failures:
        print(f"\nFAILED ({len(failures)}):")
        for f in failures:
            print(" - " + f)
        return 1
    print("\nAll dv:new-project checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
