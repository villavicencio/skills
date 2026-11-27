#!/usr/bin/env python3
"""Runs plugins/dv/scripts/dv_latest_check.py against a stand-in `gh`, never the real one.

Each case builds a throwaway client home (a Claude Code one with plugins/installed_plugins.json,
or a Codex one with only version directories in its plugin cache), puts a stand-in `gh` first on
PATH, runs `python3 -I dv_latest_check.py <base dir>` and checks the outcome word, the exit code
and the versions named. The stand-in `gh` records its argv, then prints a release list from a
file, exits with an error, prints something that isn't JSON or sleeps; with no stand-in and no
real `gh` on PATH, the run checks the "gh missing" path.

Checked (each name below is printed with ok or FAIL):
  current (Claude Code and Codex homes, a SKILL.md path given instead of its directory, a
  development copy read by metadata.version, one ahead of the release); an installed copy ahead
  of every stable release is not verified, whether it is the loaded copy or only the installed
  version (with the loaded copy at or below the release); which Claude Code entry applies (a project-scope
  entry for the working directory or a parent, one for another directory, one with no
  projectPath, an unplaceable entry or two disagreeing entries at one path making the install
  unknown even when another entry applies); stale with the install
  current (a fresh session is enough) and with the install itself behind, on both clients, and
  with the installed version unreadable; the latest release ignoring drafts, pre-releases, other
  plugins' tags and malformed dv tags, and gh asked to exclude drafts and pre-releases; release
  unreadable (gh exits non-zero, prints non-JSON, lists no dv release, is missing, times out);
  DV_LATEST_CHECK_GH naming the gh to run;
  a loaded copy that an update removed (the version still read from its path); base path
  unreadable or malformed (missing, relative, empty, an unfilled placeholder, a development copy
  with no metadata.version); and every dv SKILL.md runs the same first step before its first section.

Stdlib only, no network.

    python3 tooling/evals/test_dv_latest_check.py [path/to/dv_latest_check.py]
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (
    REPO / "plugins" / "dv" / "scripts" / "dv_latest_check.py")

FAILURES: list = []

# Absolute paths only: the "gh missing" cases run with a PATH that has nothing on it (a CI runner
# has a real gh in /usr/bin).
FAKE_GH = r"""#!/bin/sh
printf '%s\n' "$@" > "$FAKE_GH_DIR/argv"
case "$FAKE_GH_MODE" in
  fail) echo "error connecting to api.github.com" >&2; exit 1 ;;
  garbage) echo "not json"; exit 0 ;;
  sleep) /bin/sleep 5; exit 0 ;;
esac
/bin/cat "$FAKE_GH_DIR/releases.json"
"""


def releases(*tags, drafts=(), pre=()):
    rows = [{"tagName": t, "isDraft": False, "isPrerelease": False} for t in tags]
    rows += [{"tagName": t, "isDraft": True, "isPrerelease": False} for t in drafts]
    rows += [{"tagName": t, "isDraft": False, "isPrerelease": True} for t in pre]
    return rows


class Sandbox:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="dv-latest-check-"))
        self.bin = self.root / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(0o755)
        self.set_releases(releases("dv--v0.51.0", "dv--v0.50.0"))

    def set_releases(self, rows):
        (self.bin / "releases.json").write_text(json.dumps(rows))

    def skill(self, home: Path, version: str, name: str = "pickup", meta: str | None = None) -> Path:
        d = home / "plugins" / "cache" / "villavicencio-skills" / "dv" / version / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(skill_md(meta or version))
        return d

    def claude_home(self, installed: str | None, *loaded: str) -> Path:
        home = self.root / "claude"
        for v in loaded:
            self.skill(home, v)
        (home / "plugins").mkdir(parents=True, exist_ok=True)
        if installed is not None:
            manifest = {"version": 2, "plugins": {"dv@villavicencio-skills": [
                {"scope": "user", "version": installed,
                 "installPath": str(home / f"plugins/cache/villavicencio-skills/dv/{installed}")}]}}
            (home / "plugins" / "installed_plugins.json").write_text(json.dumps(manifest))
        return home

    def codex_home(self, *versions: str) -> Path:
        home = self.root / "codex"
        for v in versions:
            self.skill(home, v)
        return home

    def run(self, arg: str, mode: str = "", gh: bool = True, extra: dict | None = None,
            cwd: str | None = None):
        env = {"PATH": f"{self.bin}:/usr/bin:/bin" if gh else str(self.root / "empty"),
               "FAKE_GH_DIR": str(self.bin), "FAKE_GH_MODE": mode, "HOME": str(self.root)}
        for k, v in (extra or {}).items():
            env[k] = v.replace("{bin}", str(self.bin))
        run_dir = None
        if cwd:
            run_dir = Path(cwd.replace("{root}", str(self.root)))
            run_dir.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run([sys.executable, "-I", str(SCRIPT), arg], capture_output=True,
                              text=True, env=env, timeout=60, cwd=run_dir)
        return proc.returncode, proc.stdout, proc.stderr

    def gh_argv(self):
        return (self.bin / "argv").read_text().split("\n")

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


def skill_md(version: str | None) -> str:
    meta = f'metadata:\n  author: villavicencio\n  version: "{version}"\n' if version else ""
    return f"---\nname: pickup\ndescription: test\nlicense: Apache-2.0\n{meta}---\n\n# /pickup\n"


def expect(name: str, cond: bool, detail: str = ""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"\n     {detail}"))
    if not cond:
        FAILURES.append(name)


def case(name, arg_fn, code, first_word, contains=(), absent=(), mode="", gh=True, setup=None,
         env=None, cwd=None):
    sb = Sandbox()
    try:
        if setup:
            setup(sb)
        rc, out, err = sb.run(arg_fn(sb), mode=mode, gh=gh, extra=env, cwd=cwd)
        first = out.splitlines()[0] if out else ""
        ok = (rc == code and first.startswith(f"dv-latest-check: {first_word}")
              and all(c in first for c in contains) and not any(a in first for a in absent))
        expect(name, ok, f"exit {rc}, first line {first!r}, stderr {err.strip()!r}")
        return sb.gh_argv() if (sb.bin / "argv").exists() else []
    finally:
        sb.close()


def main() -> int:
    if not SCRIPT.is_file():
        print(f"FAIL script missing: {SCRIPT}")
        return 1

    # --- current -------------------------------------------------------------------------
    argv = case("current: Claude Code, loaded = latest = installed",
                lambda sb: str(sb.skill(sb.claude_home("0.51.0"), "0.51.0")),
                0, "current", ("loaded dv 0.51.0", "latest release 0.51.0", "installed 0.51.0"))
    expect("gh asked for stable releases of villavicencio/skills only",
           all(a in argv for a in ("release", "list", "villavicencio/skills", "--exclude-drafts",
                                   "--exclude-pre-releases")), repr(argv))
    case("current: Codex home, installed read from its cache directories",
         lambda sb: str(sb.skill(sb.codex_home("0.51.0"), "0.51.0")),
         0, "current", ("loaded dv 0.51.0", "installed 0.51.0"))
    case("current: a SKILL.md path is taken as its directory",
         lambda sb: str(sb.skill(sb.codex_home("0.51.0"), "0.51.0") / "SKILL.md"),
         0, "current", ("loaded dv 0.51.0",))
    case("current: a development copy is read by metadata.version",
         lambda sb: str(make_dev(sb, "0.51.0")),
         0, "current", ("loaded dv 0.51.0", "installed unknown"))
    case("current: loaded ahead of the latest release",
         lambda sb: str(make_dev(sb, "0.53.0")),
         0, "current", ("loaded dv 0.53.0 (development copy ahead of the latest release)",))
    case("not verified: an installed cache copy ahead of every stable release",
         lambda sb: str(sb.skill(sb.claude_home("0.53.0"), "0.53.0")),
         2, "not verified", ("loaded dv 0.53.0 is ahead of the latest stable release 0.51.0",
                             "installed 0.53.0"))

    case("not verified: loaded the latest release, but the install is ahead of every release",
         lambda sb: str(sb.skill(sb.claude_home("0.52.0", "0.52.0"), "0.51.0")),
         2, "not verified", ("installed dv 0.52.0 is ahead of the latest stable release 0.51.0",
                             "loaded dv 0.51.0"))
    case("not verified: loaded below the release, install ahead of every release (no fresh-session advice)",
         lambda sb: str(sb.skill(sb.codex_home("0.49.0", "0.52.0"), "0.49.0")),
         2, "not verified", ("installed dv 0.52.0 is ahead", "loaded dv 0.49.0"),
         ("fresh session",))
    case("current: a development copy at the release ignores the installed version",
         lambda sb: str(make_dev(sb, "0.51.0")), 0, "current", ("installed unknown",))

    # --- which Claude Code install applies ------------------------------------------------------
    case("installed: a project-scope entry for this directory wins over the user entry",
         lambda sb: str(scoped_home(sb, [user("0.51.0"), project("0.50.0", "{root}/proj")], "0.50.0")),
         1, "stale", ("loaded dv 0.50.0", "installed 0.50.0", "install itself is behind"),
         cwd="{root}/proj/sub")
    case("installed: a project-scope entry for another directory is ignored",
         lambda sb: str(scoped_home(sb, [user("0.51.0"), project("0.50.0", "{root}/other")], "0.50.0")),
         1, "stale", ("installed 0.51.0", "a fresh session picks up"), cwd="{root}/proj")
    case("installed: a non-user entry with no projectPath makes it unknown",
         lambda sb: str(scoped_home(sb, [user("0.51.0"), {"scope": "project", "version": "0.50.0"}], "0.50.0")),
         1, "stale", ("installed unknown",), cwd="{root}/proj")
    # A malformed dv@<marketplace> value is an unknown install, never a traceback or a guess.
    # (A bare string, a list holding a non-object, an object with no usable version.)
    for label, value in (("a number", 5), ("a string", "0.51.0"), ("true", True),
                         ("a list holding a non-object", [user("0.51.0"), "0.50.0"]),
                         ("a list holding null", [None, user("0.51.0")])):
        def malformed(sb, value=value):
            home = sb.claude_home(None)
            d = sb.skill(home, "0.50.0")
            (home / "plugins" / "installed_plugins.json").write_text(
                json.dumps({"version": 2, "plugins": {"dv@villavicencio-skills": value}}))
            return d
        case(f"installed: the dv entry is {label} -> unknown, no traceback",
             lambda sb, malformed=malformed: str(malformed(sb)),
             1, "stale", ("loaded dv 0.50.0", "installed unknown"), ("Traceback",))
    case("installed: an applicable project entry with an invalid version is unknown, not the user version",
         lambda sb: str(scoped_home(sb, [user("0.51.0"), project("not-a-version", "{root}/proj")], "0.50.0")),
         1, "stale", ("installed unknown",), ("installed 0.51.0", "a fresh session picks up"),
         cwd="{root}/proj/sub")
    case("installed: an applicable project entry with no version is unknown, not the user version",
         lambda sb: str(scoped_home(sb, [user("0.51.0"), {"scope": "local", "projectPath": "{root}/proj"}], "0.50.0")),
         1, "stale", ("installed unknown",), ("installed 0.51.0", "a fresh session picks up"),
         cwd="{root}/proj")
    case("installed: a project entry with an invalid version for another directory is ignored",
         lambda sb: str(scoped_home(sb, [user("0.51.0"), project("not-a-version", "{root}/other")], "0.50.0")),
         1, "stale", ("installed 0.51.0", "a fresh session picks up"), cwd="{root}/proj")
    # An entry whose applicability can't be decided makes the install unknown even when another
    # entry plainly applies: it might apply here too, and a known version would be a guess.
    case("installed: an applicable project entry plus a non-user entry with no projectPath is unknown",
         lambda sb: str(scoped_home(sb, [user("0.51.0"), project("0.51.0", "{root}/proj"),
                                         {"scope": "local", "version": "0.50.0"}], "0.50.0")),
         1, "stale", ("installed unknown",), ("installed 0.51.0", "a fresh session picks up"),
         cwd="{root}/proj/sub")
    case("installed: an applicable project entry plus a non-object item is unknown",
         lambda sb: str(scoped_home(sb, [user("0.51.0"), project("0.51.0", "{root}/proj"), "0.50.0"],
                                    "0.50.0")),
         1, "stale", ("installed unknown",), ("installed 0.51.0", "a fresh session picks up"),
         cwd="{root}/proj/sub")
    # Two applicable entries at the same depth with different versions: nothing says which one
    # Claude Code loads, so neither is taken (not the higher one).
    case("installed: two entries at the same path with different versions is unknown",
         lambda sb: str(scoped_home(sb, [project("0.50.0", "{root}/proj"),
                                         {"scope": "local", "version": "0.51.0",
                                          "projectPath": "{root}/proj"}], "0.50.0")),
         1, "stale", ("installed unknown",), ("installed 0.51.0", "a fresh session picks up"),
         cwd="{root}/proj/sub")
    case("installed: two entries at the same path with the same version is that version",
         lambda sb: str(scoped_home(sb, [project("0.51.0", "{root}/proj"),
                                         {"scope": "local", "version": "0.51.0",
                                          "projectPath": "{root}/proj"}], "0.50.0")),
         1, "stale", ("installed 0.51.0", "a fresh session picks up"), ("installed unknown",),
         cwd="{root}/proj/sub")
    case("installed: one unreadable version among the deepest entries is unknown, not the readable sibling",
         lambda sb: str(scoped_home(sb, [project("0.51.0", "{root}/proj"),
                                         {"scope": "local", "version": "not-a-version",
                                          "projectPath": "{root}/proj"}], "0.50.0")),
         1, "stale", ("installed unknown",), ("installed 0.51.0", "a fresh session picks up"),
         cwd="{root}/proj/sub")
    case("installed: a deeper entry wins over two disagreeing shallower ones",
         lambda sb: str(scoped_home(sb, [project("0.49.0", "{root}/proj"), project("0.51.0", "{root}/proj"),
                                         project("0.50.0", "{root}/proj/sub")], "0.50.0")),
         1, "stale", ("installed 0.50.0", "install itself is behind"), cwd="{root}/proj/sub")
    case("installed: a deeper valid project entry wins over a shallower invalid one",
         lambda sb: str(scoped_home(sb, [project("not-a-version", "{root}/proj"),
                                         project("0.50.0", "{root}/proj/sub")], "0.50.0")),
         1, "stale", ("installed 0.50.0", "install itself is behind"), cwd="{root}/proj/sub")
    case("installed: a user entry with an invalid version and no scoped entry is unknown",
         lambda sb: str(scoped_home(sb, [user("not-a-version")], "0.50.0")),
         1, "stale", ("installed unknown",), cwd="{root}/proj")

    # --- latest release selection ------------------------------------------------------------
    def noisy(sb):
        sb.set_releases(releases("other--v9.0.0", "dv--v0.52.0", "dv--v0.9.9", "dv--vbad",
                                 "dv--v0.52", drafts=("dv--v0.60.0",), pre=("dv--v0.61.0",)))
    case("latest: highest stable dv tag, ignoring drafts, pre-releases, other plugins, bad tags",
         lambda sb: str(sb.skill(sb.claude_home("0.52.0"), "0.51.0")),
         1, "stale", ("loaded dv 0.51.0", "latest release 0.52.0"), setup=noisy)
    case("latest: semver order, not string order (0.10.0 > 0.9.0)",
         lambda sb: str(sb.skill(sb.claude_home("0.10.0"), "0.9.0")),
         1, "stale", ("latest release 0.10.0",),
         setup=lambda sb: sb.set_releases(releases("dv--v0.9.0", "dv--v0.10.0")))

    # --- stale -----------------------------------------------------------------------------------
    case("stale: long-running session on an older dv, install current -> fresh session",
         lambda sb: str(sb.skill(sb.claude_home("0.51.0", "0.51.0"), "0.48.0")),
         1, "stale", ("loaded dv 0.48.0", "latest release 0.51.0", "installed 0.51.0",
                      "a fresh session picks up"), ("install itself is behind",))
    case("stale: install itself behind the release (Claude Code)",
         lambda sb: str(sb.skill(sb.claude_home("0.50.0"), "0.50.0")),
         1, "stale", ("loaded dv 0.50.0", "latest release 0.51.0", "installed 0.50.0",
                      "install itself is behind"), ("fresh session picks up",))
    case("stale: install itself behind the release (Codex)",
         lambda sb: str(sb.skill(sb.codex_home("0.49.0", "0.50.0"), "0.49.0")),
         1, "stale", ("loaded dv 0.49.0", "installed 0.50.0", "install itself is behind"))
    case("stale: Codex install current, older loaded copy still on disk",
         lambda sb: str(sb.skill(sb.codex_home("0.50.0", "0.51.0"), "0.50.0")),
         1, "stale", ("installed 0.51.0", "a fresh session picks up"))
    case("stale: installed version unreadable is named unknown",
         lambda sb: str(make_bad_manifest(sb)),
         1, "stale", ("loaded dv 0.50.0", "installed unknown"))
    case("stale: loaded copy removed by an update still names the loaded version (Codex)",
         lambda sb: str(sb.codex_home("0.53.0") / "plugins/cache/villavicencio-skills/dv/0.52.0/skills/pickup"),
         1, "stale", ("loaded dv 0.52.0", "latest release 0.54.0", "installed 0.53.0",
                      "install itself is behind"),
         setup=lambda sb: sb.set_releases(releases("dv--v0.54.0", "dv--v0.53.0")))
    case("current: cache-shaped path with no SKILL.md is read from the path",
         lambda sb: str(make_cache_dir_only(sb)), 0, "current", ("loaded dv 0.51.0",))
    case("stale: development copy below the release",
         lambda sb: str(make_dev(sb, "0.50.0")),
         1, "stale", ("loaded dv 0.50.0", "latest release 0.51.0"))

    # --- release unreadable -------------------------------------------------------------------
    for label, mode, extra in (("gh exits non-zero", "fail", "error connecting"),
                               ("gh prints non-JSON", "garbage", "did not return JSON")):
        case(f"not verified: {label}",
             lambda sb: str(sb.skill(sb.claude_home("0.51.0"), "0.51.0")),
             2, "not verified", ("loaded dv 0.51.0", "latest release unreadable", extra),
             mode=mode)
    case("not verified: no dv release in the list",
         lambda sb: str(sb.skill(sb.claude_home("0.51.0"), "0.51.0")),
         2, "not verified", ("no stable dv--v<version> release",),
         setup=lambda sb: sb.set_releases(releases("other--v1.0.0", drafts=("dv--v0.51.0",))))
    case("not verified: gh missing",
         lambda sb: str(sb.skill(sb.claude_home("0.51.0"), "0.51.0")),
         2, "not verified", ("gh is not installed",), gh=False)
    check_timeout()
    check_unknown_reasons()
    case("DV_LATEST_CHECK_GH names the gh to run when gh is not on PATH",
         lambda sb: str(sb.skill(sb.claude_home("0.51.0"), "0.51.0")),
         0, "current", ("latest release 0.51.0",), gh=False,
         env={"DV_LATEST_CHECK_GH": "{bin}/gh"})

    # --- base path unreadable or malformed ----------------------------------------------------------
    for label, fn, text in (
            ("missing directory", lambda sb: str(sb.root / "nope" / "skills" / "pickup"),
             "no readable SKILL.md"),
            ("relative path", lambda sb: "plugins/dv/skills/pickup", "not absolute"),
            ("empty argument", lambda sb: "", "no skill base directory"),
            ("unfilled placeholder", lambda sb: "<base directory>", "not absolute"),
            ("development copy with no metadata.version", lambda sb: str(make_dev(sb, None)),
             "no metadata.version")):
        case(f"not verified: base path {label}", fn, 2, "not verified",
             ("loaded dv version can't be read", text))

    check_skill_files()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: " + "; ".join(FAILURES))
        return 1
    print("all dv_latest_check tests passed")
    return 0


def user(version: str) -> dict:
    return {"scope": "user", "version": version}


def project(version: str, path: str) -> dict:
    return {"scope": "project", "version": version, "projectPath": path}


def scoped_home(sb: Sandbox, entries: list, loaded: str) -> Path:
    home = sb.claude_home(None)
    d = sb.skill(home, loaded)
    for e in entries:
        if "projectPath" in e:
            e["projectPath"] = e["projectPath"].replace("{root}", str(sb.root))
            Path(e["projectPath"]).mkdir(parents=True, exist_ok=True)
    manifest = {"version": 2, "plugins": {"dv@villavicencio-skills": entries}}
    (home / "plugins" / "installed_plugins.json").write_text(json.dumps(manifest))
    return d


def make_dev(sb: Sandbox, version: str | None) -> Path:
    d = sb.root / "worktree" / "plugins" / "dv" / "skills" / "pickup"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(skill_md(version))
    return d


def make_bad_manifest(sb: Sandbox) -> Path:
    home = sb.claude_home(None)
    d = sb.skill(home, "0.50.0")
    (home / "plugins" / "installed_plugins.json").write_text("{not json")
    return d


def make_cache_dir_only(sb: Sandbox) -> Path:
    d = sb.root / "claude" / "plugins" / "cache" / "villavicencio-skills" / "dv" / "0.51.0" / "skills" / "pickup"
    d.mkdir(parents=True)
    return d


def check_timeout():
    """In-process: a gh that outlives the timeout is 'not verified', not a hang."""
    sb = Sandbox()
    old_path = os.environ.get("PATH", "")
    try:
        spec = importlib.util.spec_from_file_location("dv_latest_check", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.GH_TIMEOUT_SECONDS = 1
        os.environ["PATH"] = f"{sb.bin}:/usr/bin:/bin"
        os.environ["FAKE_GH_DIR"] = str(sb.bin)
        os.environ["FAKE_GH_MODE"] = "sleep"
        code, lines = mod.check(str(sb.skill(sb.claude_home("0.51.0"), "0.51.0")))
        expect("not verified: gh times out", code == 2 and "did not answer within 1 s" in lines[0],
               repr((code, lines)))
    finally:
        os.environ["PATH"] = old_path
        os.environ.pop("FAKE_GH_MODE", None)
        os.environ.pop("FAKE_GH_DIR", None)
        sb.close()


def check_unknown_reasons():
    """In-process: each unknown install names its reason in the client text, and a known one does not."""
    spec = importlib.util.spec_from_file_location("dv_latest_check", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sb = Sandbox()
    try:
        proj = sb.root / "proj"
        (proj / "sub").mkdir(parents=True)
        applicable = {"scope": "project", "version": "0.51.0", "projectPath": str(proj)}
        for name, entries, reason in (
                ("an unplaced non-user entry", [applicable, {"scope": "local", "version": "0.50.0"}],
                 "has no projectPath"),
                ("a non-object item", [applicable, "0.50.0"], "is not an object"),
                ("disagreeing entries at one path",
                 [applicable, dict(applicable, scope="local", version="0.50.0")],
                 "entries for the same directory name different versions"),
                ("an applicable entry with no version",
                 [{"scope": "project", "projectPath": str(proj)}], "has no readable version")):
            version, client = mod.active_entry_version(entries, Path("m.json"), "mk", str(proj / "sub"))
            expect(f"installed reason: {name}", version is None and reason in client,
                   repr((version, client)))
        version, client = mod.active_entry_version([applicable, dict(applicable, scope="local")],
                                                   Path("m.json"), "mk", str(proj / "sub"))
        expect("installed reason: agreeing entries at one path are known",
               version == (0, 51, 0) and client == "Claude Code", repr((version, client)))
    finally:
        sb.close()


def check_skill_files():
    """Every dv SKILL.md runs the same first step, before its first section."""
    skills = sorted((REPO / "plugins" / "dv" / "skills").glob("*/SKILL.md"))
    expect("16 dv skills found", len(skills) == 16, f"{len(skills)}: {[s.parent.name for s in skills]}")
    blocks = {}
    for f in skills:
        lines = f.read_text(encoding="utf-8").split("\n")
        try:
            h1 = next(i for i, l in enumerate(lines) if l.startswith("# "))
            h2 = next(i for i, l in enumerate(lines) if i > h1 and l.startswith("## "))
        except StopIteration:
            expect(f"{f.parent.name}: has an H1 and a section", False)
            continue
        first = lines[h2]
        end = next((i for i, l in enumerate(lines) if i > h2 and l.startswith("## ")), len(lines))
        block = "\n".join(lines[h2:end]).strip()
        blocks[f.parent.name] = block
        expect(f"{f.parent.name}: first section is the dv-latest-check step",
               first == "## First step: dv-latest-check"
               and "scripts/dv_latest_check.py" in block, first)
    expect("the first step is identical in every dv skill", len(set(blocks.values())) == 1,
           ", ".join(sorted(blocks)))
    for mode in ("director-mode", "manager-mode"):
        text = (REPO / "plugins" / "dv" / "skills" / mode / "SKILL.md").read_text(encoding="utf-8")
        expect(f"{mode}: reruns the check before later dv-dependent actions",
               "Rerun dv-latest-check" in text)


if __name__ == "__main__":
    sys.exit(main())
