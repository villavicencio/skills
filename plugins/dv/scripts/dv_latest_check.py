#!/usr/bin/env python3
"""dv-latest-check: is the dv this skill was loaded from the latest stable dv release?

    python3 -I dv_latest_check.py <skill base directory>

Every dv skill runs this as its first step, passing the directory the client gave when it loaded
the skill (Claude Code: "Base directory for this skill: ..."; Codex: the directory of the SKILL.md
it read). It reads three versions:

  loaded     from that path: <home>/plugins/cache/<marketplace>/dv/<version>/skills/<name>, even
             when an update has since removed that directory. A path outside a plugin cache (a
             development copy loaded with --plugin-dir) falls back to metadata.version in its
             SKILL.md.
  latest     the highest dv--v<version> tag among the stable releases of villavicencio/skills
             (drafts and pre-releases excluded, other plugins' tags ignored), read with `gh`.
  installed  Claude Code: <home>/plugins/installed_plugins.json, entry dv@<marketplace>.
             Codex: the highest version directory in <home>/plugins/cache/<marketplace>/dv/.

The first printed line starts with the outcome, and the exit code matches it:

  dv-latest-check: current ...        exit 0  go on
  dv-latest-check: stale ...          exit 1  hold dv-dependent actions (names loaded, latest
                                              and installed, and whether a fresh session is
                                              enough or the install itself is behind)
  dv-latest-check: not verified ...   exit 2  hold dv-dependent actions until a rerun says
                                              current (release or base path unreadable)

DV_LATEST_CHECK_GH, when set, names the gh binary to run instead of the one on PATH: a stand-in for
tests and live checks (a Codex shell rebuilds PATH from the login profile, so PATH alone can't).

Stdlib only; runs on Python 3.9 or later. Tests: tooling/evals/test_dv_latest_check.py.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = "villavicencio/skills"
PLUGIN = "dv"
GH_TIMEOUT_SECONDS = 30
SEMVER = r"(\d+)\.(\d+)\.(\d+)"
TAG_RE = re.compile(r"^dv--v" + SEMVER + r"$")
VERSION_RE = re.compile(r"^" + SEMVER + r"$")
CACHE_RE = re.compile(
    r"^(?P<home>.+)/plugins/cache/(?P<marketplace>[^/]+)/dv/(?P<version>" + SEMVER + r")"
    r"/skills/(?P<skill>[^/]+)$"
)
PREFIX = "dv-latest-check:"

EXIT_CURRENT, EXIT_STALE, EXIT_NOT_VERIFIED = 0, 1, 2


class CheckError(Exception):
    """A version that can't be read; the message says which and why."""


def parse_version(text: str) -> tuple:
    m = VERSION_RE.match(text.strip())
    if not m:
        raise ValueError(text)
    return tuple(int(part) for part in m.groups())


def fmt(version: tuple) -> str:
    return ".".join(str(part) for part in version)


def skill_md_version(skill_dir: Path) -> tuple:
    """metadata.version from the SKILL.md frontmatter, read without a YAML library."""
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise CheckError(f"{skill_dir / 'SKILL.md'} has no frontmatter")
    in_metadata = False
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if re.match(r"^metadata:\s*$", line):
            in_metadata = True
            continue
        if in_metadata:
            if line and not line[0].isspace():
                in_metadata = False
                continue
            m = re.match(r"^\s+version:\s*['\"]?([^'\"\s]+)['\"]?\s*$", line)
            if m:
                try:
                    return parse_version(m.group(1))
                except ValueError:
                    raise CheckError(f"metadata.version {m.group(1)!r} is not a version")
    raise CheckError(f"{skill_dir / 'SKILL.md'} has no metadata.version")


def read_loaded(arg: str) -> dict:
    """The loaded version and where to look for the installed one, from the base path."""
    if not arg.strip():
        raise CheckError("no skill base directory was given")
    path = Path(arg.strip()).expanduser()
    if path.name == "SKILL.md":
        path = path.parent
    if not path.is_absolute():
        raise CheckError(f"base path {arg!r} is not absolute")
    path = Path(os.path.normpath(str(path)))
    m = CACHE_RE.match(str(path))
    if m:
        # The version is in the path the client reported. An update can remove that copy while
        # a session still runs on it (Codex replaces the cache directory), so a missing
        # directory doesn't make the loaded version unknown.
        gone = not (path / "SKILL.md").is_file()
        return {
            "version": parse_version(m.group("version")),
            "home": Path(m.group("home")),
            "marketplace": m.group("marketplace"),
            "source": "plugin cache, no longer on disk" if gone else "plugin cache",
            "path": path,
        }
    if not (path / "SKILL.md").is_file():
        raise CheckError(f"base path {path} has no readable SKILL.md")
    try:
        version = skill_md_version(path)
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError(f"base path {path}: {exc}")
    return {"version": version, "home": None, "marketplace": None,
            "source": "development copy", "path": path}


def read_latest(repo: str = REPO) -> tuple:
    """The highest dv--v<version> tag among stable releases, via gh."""
    gh = os.environ.get("DV_LATEST_CHECK_GH") or "gh"
    cmd = [gh, "release", "list", "-R", repo, "--exclude-drafts", "--exclude-pre-releases",
           "--limit", "100", "--json", "tagName,isDraft,isPrerelease"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=GH_TIMEOUT_SECONDS)
    except FileNotFoundError:
        raise CheckError(f"{gh} is not installed or not on PATH")
    except subprocess.TimeoutExpired:
        raise CheckError(f"gh release list did not answer within {GH_TIMEOUT_SECONDS} s")
    except OSError as exc:
        raise CheckError(f"gh release list could not run: {exc}")
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        reason = detail[0] if detail else "no output"
        raise CheckError(f"gh release list exited {proc.returncode}: {reason}")
    try:
        releases = json.loads(proc.stdout)
    except ValueError:
        raise CheckError("gh release list did not return JSON")
    if not isinstance(releases, list):
        raise CheckError("gh release list did not return a list")
    best = None
    for rel in releases:
        if not isinstance(rel, dict) or rel.get("isDraft") or rel.get("isPrerelease"):
            continue
        m = TAG_RE.match(str(rel.get("tagName", "")))
        if m:
            version = tuple(int(part) for part in m.groups())
            if best is None or version > best:
                best = version
    if best is None:
        raise CheckError(f"no stable dv--v<version> release found in {repo}")
    return best


def read_installed(loaded: dict):
    """(version, client) for the install the loaded copy came from; version None if unknown."""
    home, marketplace = loaded["home"], loaded["marketplace"]
    if home is None:
        return None, "not an installed plugin"
    manifest = home / "plugins" / "installed_plugins.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            entries = (data.get("plugins", data) or {}).get(f"{PLUGIN}@{marketplace}") or []
            if isinstance(entries, dict):
                entries = [entries]
            versions = []
            for entry in entries:
                try:
                    versions.append((entry.get("scope") == "user", parse_version(entry["version"])))
                except (KeyError, TypeError, ValueError, AttributeError):
                    continue
            if not versions:
                return None, f"Claude Code ({manifest} has no dv@{marketplace} version)"
            user = [v for is_user, v in versions if is_user]
            return max(user or [v for _, v in versions]), "Claude Code"
        except (OSError, ValueError, AttributeError) as exc:
            return None, f"Claude Code ({manifest} unreadable: {exc})"
    cache = home / "plugins" / "cache" / marketplace / PLUGIN
    try:
        versions = []
        for child in cache.iterdir():
            if child.is_dir():
                try:
                    versions.append(parse_version(child.name))
                except ValueError:
                    continue
    except OSError as exc:
        return None, f"Codex ({cache} unreadable: {exc})"
    if not versions:
        return None, f"Codex (no version directory in {cache})"
    return max(versions), "Codex"


def check(arg: str, repo: str = REPO):
    """Returns (exit code, lines to print)."""
    try:
        loaded = read_loaded(arg)
    except CheckError as exc:
        return EXIT_NOT_VERIFIED, [
            f"{PREFIX} not verified: the loaded dv version can't be read ({exc}). Hold every "
            "dv-dependent action; rerun this check with the base directory the client gave "
            "when this skill loaded."]
    installed, client = read_installed(loaded)
    loaded_v = fmt(loaded["version"])
    installed_text = fmt(installed) if installed else "unknown"
    where = f"loaded from {loaded['path']} ({loaded['source']}; client: {client})"
    try:
        latest = read_latest(repo)
    except CheckError as exc:
        return EXIT_NOT_VERIFIED, [
            f"{PREFIX} not verified: loaded dv {loaded_v}, installed {installed_text}, latest "
            f"release unreadable ({exc}). Hold every dv-dependent action until a rerun of this "
            "check says current; work that doesn't depend on dv can continue.",
            where]
    latest_v = fmt(latest)
    if loaded["version"] >= latest:
        ahead = "" if loaded["version"] == latest else " (ahead of the latest release)"
        return EXIT_CURRENT, [
            f"{PREFIX} current: loaded dv {loaded_v}{ahead}, latest release {latest_v}, "
            f"installed {installed_text}.",
            where]
    if installed is not None and installed >= latest:
        fix = (f"The install is already at {installed_text}: a fresh session picks up the "
               "update (re-invoking the skill in this session does not).")
    elif installed is not None:
        fix = (f"The install itself is behind ({installed_text} < {latest_v}): update dv on "
               "this machine, then start a fresh session.")
    else:
        fix = ("The installed version is unknown: update dv on this machine if it is behind, "
               "then start a fresh session.")
    return EXIT_STALE, [
        f"{PREFIX} stale: loaded dv {loaded_v}, latest release {latest_v}, installed "
        f"{installed_text}. Hold every dv-dependent action. {fix}",
        where]


def main(argv) -> int:
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        if argv and argv[0] in ("-h", "--help"):
            print(__doc__)
            return EXIT_CURRENT
        print(f"{PREFIX} not verified: usage: dv_latest_check.py <skill base directory>. Hold "
              "every dv-dependent action.")
        return EXIT_NOT_VERIFIED
    code, lines = check(argv[0])
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
