#!/usr/bin/env python3
"""Publish a GitHub release for each plugin whose version has none yet.

`.github/workflows/release.yml` runs this after `validate` passes on a push to
`main` (VIL-809), checked out at that push's commit, which it passes in as
RELEASE_SHA. For each `plugins/<dir>/.claude-plugin/plugin.json` it checks whether a GitHub
release exists for the tag `<name>--v<version>`. If none does, it publishes one
with

    gh release create <tag> --title "<name> v<version>" \\
        --notes-file docs/release-notes/<tag>.md --latest=<true|false> \\
        (--target <sha> | --verify-tag)

and then starts `validate` on the tag with `gh workflow run validate.yml --ref
<tag>`, because a tag made with the workflow's GITHUB_TOKEN does not start other
workflows on its own (`workflow_dispatch` is the exception).

Rules:

- A version that already has a published release: nothing happens.
- A tag with no release: the release is published on the existing tag
  (`--verify-tag`, no `--target`), so the tag stays where it is.
- No tag and no release: the tag is created at the checked-out commit
  (`--target <sha>`).
- A version lower than the plugin's highest release, with no tag of its own:
  if the commit is no longer main's tip (two merges whose `validate` runs
  finished out of order, so the newer version released first), it is released
  at its own commit without Latest; if the commit is main's tip (say, a revert
  of plugin.json), the run refuses and names it.
- All checks run before anything is created. A plugin directory without a
  readable plugin.json, a missing or empty notes file, a draft release on the
  tag, a malformed name or version, or a lower version on main's tip (above)
  all exit 1, naming the problem, with nothing tagged or released.
- "Latest" goes only to a version higher than every release the plugin already
  has, so it ends on the plugin's highest version. GitHub keeps one Latest per
  repo, so with several plugins it ends on the last plugin to publish a new
  high; this repo has one plugin (`dv`).
- If starting `validate` fails after a release is published, the run still
  publishes the other due releases, then exits 1 naming the command to run by
  hand (a re-run won't retry it: the release exists by then).

`--dry-run` makes the same checks (it reads releases and tags from GitHub) and
prints what it would publish; it creates nothing; it treats the commit as the
tip-to-be of main. Publishing for real only runs inside GitHub Actions on
`refs/heads/main` with RELEASE_SHA set, so a local run cannot tag a branch.

Stdlib only; needs `git` and an authenticated `gh` (GH_TOKEN in Actions).

    python3 tooling/release_plugins.py [--dry-run] [--repo OWNER/NAME] [--root DIR]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

# Strict MAJOR.MINOR.PATCH, no leading zeros, no pre-release or build suffix.
SEMVER_RE = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
# Lowercase words joined by single hyphens, so `--v` in a tag is unambiguous.
NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SHA_RE = re.compile(r"[0-9a-f]{40}")
REPO_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")

NOTES_DIR = "docs/release-notes"


class ReleaseError(Exception):
    """One or more problems that stop the run before anything is created."""

    def __init__(self, problems: list[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class Plugin:
    name: str
    version: str
    manifest: str  # repo-relative path to plugin.json


@dataclass(frozen=True)
class Release:
    plugin: str
    version: str
    tag: str
    title: str
    notes: str  # repo-relative path
    tag_exists: bool
    latest: bool


def tag_for(name: str, version: str) -> str:
    return f"{name}--v{version}"


def parse_version(version: str) -> tuple[int, int, int] | None:
    m = SEMVER_RE.fullmatch(version)
    return (int(m[1]), int(m[2]), int(m[3])) if m else None


def read_plugins(root: Path) -> list[Plugin]:
    """Read and validate the manifest of each directory under plugins/.

    A plugin directory without `.claude-plugin/plugin.json`, or no plugin
    directory at all, is a problem, so a missing manifest can't make the run
    report "nothing to publish".
    """
    plugins: list[Plugin] = []
    problems: list[str] = []
    plugins_root = root / "plugins"
    dirs = sorted(d for d in plugins_root.iterdir() if d.is_dir()) if plugins_root.is_dir() else []
    if not dirs:
        raise ReleaseError(["no plugin directories under plugins/"])
    for plugin_dir in dirs:
        dir_name = plugin_dir.name
        manifest = plugin_dir / ".claude-plugin" / "plugin.json"
        rel = manifest.relative_to(root).as_posix()
        if not manifest.is_file():
            problems.append(f"plugins/{dir_name}/ has no .claude-plugin/plugin.json")
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(f"{rel}: cannot read JSON ({exc})")
            continue
        name = data.get("name") if isinstance(data, dict) else None
        version = data.get("version") if isinstance(data, dict) else None
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            problems.append(
                f"{rel}: name {name!r} must be lowercase letters and digits "
                "joined by single hyphens"
            )
            continue
        if name != dir_name:
            problems.append(f"{rel}: name {name!r} does not match its directory {dir_name!r}")
            continue
        if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
            problems.append(
                f"{rel}: version {version!r} must be MAJOR.MINOR.PATCH "
                "(digits only, no leading zeros, no suffix)"
            )
            continue
        plugins.append(Plugin(name=name, version=version, manifest=rel))
    if problems:
        raise ReleaseError(problems)
    return plugins


def notes_problem(root: Path, notes: str) -> str | None:
    """Return why the notes file can't be used, or None if it can."""
    path = root / notes
    if not path.is_file():
        return f"release notes file missing: {notes}"
    if not path.read_text(encoding="utf-8").strip():
        return f"release notes file is empty: {notes}"
    return None


def plan(
    plugins: Iterable[Plugin],
    published_tags: set[str],
    draft_tags: set[str],
    existing_tags: set[str],
    notes_check: Callable[[str], str | None],
    is_tip: bool = True,
) -> list[Release]:
    """Decide what to publish. Pure: all GitHub state comes in as arguments.

    published_tags: tags of every non-draft release (prereleases included).
    draft_tags: tags named by draft releases.
    existing_tags: which of the candidate tags already exist on the remote.
    notes_check: notes path -> problem string, or None when the file is usable.
    is_tip: whether the commit being released is main's current tip.

    Raises ReleaseError listing every problem; returns [] when nothing is due.
    """
    releases: list[Release] = []
    problems: list[str] = []
    for p in plugins:
        tag = tag_for(p.name, p.version)
        if tag in published_tags:
            continue
        where = f"{p.name} {p.version} ({p.manifest}) has no release yet"
        if tag in draft_tags:
            problems.append(
                f"{where}, and a draft release already uses tag {tag}; "
                "publish or delete that draft by hand"
            )
            continue
        prefix = f"{p.name}--v"
        released = [
            v
            for v in (parse_version(t[len(prefix):]) for t in published_tags if t.startswith(prefix))
            if v is not None
        ]
        highest = max(released, default=None)
        mine = parse_version(p.version)
        tag_exists = tag in existing_tags
        if highest is not None and mine is not None and mine < highest and not tag_exists and is_tip:
            problems.append(
                f"{where}, but it is lower than the released "
                f"{p.name} {'.'.join(map(str, highest))}; refusing to tag main's "
                "tip with an older version. Set plugin.json to a new version"
            )
            continue
        notes = f"{NOTES_DIR}/{tag}.md"
        problem = notes_check(notes)
        if problem:
            problems.append(f"{problem} ({where}). Write it and merge it to main")
            continue
        releases.append(
            Release(
                plugin=p.name,
                version=p.version,
                tag=tag,
                title=f"{p.name} v{p.version}",
                notes=notes,
                tag_exists=tag_exists,
                latest=highest is None or (mine is not None and mine > highest),
            )
        )
    if problems:
        raise ReleaseError(problems)
    return releases


def create_command(release: Release, repo: str, sha: str) -> list[str]:
    cmd = [
        "gh", "release", "create", release.tag,
        "--repo", repo,
        "--title", release.title,
        "--notes-file", release.notes,
        f"--latest={'true' if release.latest else 'false'}",
    ]
    if release.tag_exists:
        # Publish on the tag as it is; abort if it vanished since we looked.
        cmd.append("--verify-tag")
    else:
        cmd += ["--target", sha]
    return cmd


def dispatch_command(release: Release, repo: str) -> list[str]:
    return ["gh", "workflow", "run", "validate.yml", "--repo", repo, "--ref", release.tag]


# --- GitHub and git access (not unit-tested; kept thin) ----------------------


def run(cmd: list[str], cwd: Path | None = None) -> str:
    out = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
    return out.stdout


def fetch_releases(repo: str) -> tuple[set[str], set[str]]:
    """Return (published tags, draft tags) across every page of releases."""
    out = run([
        "gh", "api", "--paginate", f"repos/{repo}/releases?per_page=100",
        "--jq", ".[] | {tag_name, draft}",
    ])
    published: set[str] = set()
    drafts: set[str] = set()
    for line in out.splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        (drafts if item["draft"] else published).add(item["tag_name"])
    return published, drafts


def tag_exists(repo: str, tag: str) -> bool:
    out = run(["gh", "api", f"repos/{repo}/git/matching-refs/tags/{tag}"])
    return any(ref.get("ref") == f"refs/tags/{tag}" for ref in json.loads(out))


def main_tip(repo: str) -> str:
    return run(["gh", "api", f"repos/{repo}/git/ref/heads/main", "--jq", ".object.sha"]).strip()


def detect_repo(root: Path) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY") or run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], cwd=root
    ).strip()
    return repo


def say_error(message: str) -> None:
    prefix = "::error::" if os.environ.get("GITHUB_ACTIONS") == "true" else "error: "
    print(f"{prefix}{message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="print what would be published; change nothing")
    ap.add_argument("--repo", help="OWNER/NAME (default: GITHUB_REPOSITORY, else the gh default)")
    ap.add_argument("--root", default=".", help="repo checkout to read (default: .)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    try:
        repo = args.repo or detect_repo(root)
        if not REPO_RE.fullmatch(repo):
            raise ReleaseError([f"repo {repo!r} is not OWNER/NAME"])
        sha = run(["git", "rev-parse", "HEAD"], cwd=root).strip()
        if not SHA_RE.fullmatch(sha):
            raise ReleaseError([f"git rev-parse HEAD gave {sha!r}, not a commit SHA"])
        # On workflow_run, GITHUB_SHA is main's tip, not the validated commit,
        # so the workflow passes that commit as RELEASE_SHA.
        env_var = "RELEASE_SHA" if os.environ.get("RELEASE_SHA") else "GITHUB_SHA"
        env_sha = os.environ.get(env_var)
        if env_sha and env_sha != sha:
            raise ReleaseError([f"checkout is at {sha} but {env_var} is {env_sha}"])
        if not args.dry_run and not (
            os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("GITHUB_REF") == "refs/heads/main"
            and os.environ.get("RELEASE_SHA")
        ):
            raise ReleaseError([
                "publishing runs only in GitHub Actions on refs/heads/main with RELEASE_SHA "
                "set; use --dry-run to see what would be published"
            ])

        plugins = read_plugins(root)
        published, drafts = fetch_releases(repo)
        candidates = {tag_for(p.name, p.version) for p in plugins} - published
        existing = {t for t in candidates if tag_exists(repo, t)}
        is_tip = args.dry_run or main_tip(repo) == sha
        releases = plan(plugins, published, drafts, existing,
                        lambda n: notes_problem(root, n), is_tip=is_tip)
    except ReleaseError as exc:
        for problem in exc.problems:
            say_error(problem)
        print("Nothing was tagged or released.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        say_error(f"{' '.join(exc.cmd)} failed ({exc.returncode}): {exc.stderr.strip()}")
        print("Nothing was tagged or released.", file=sys.stderr)
        return 1

    if not releases:
        for p in plugins:
            print(f"{p.name} {p.version}: already released as {tag_for(p.name, p.version)}")
        print("Nothing to publish.")
        return 0

    for r in releases:
        if r.tag_exists:
            where = f"on existing tag {r.tag}"
        elif args.dry_run:
            # On a pull request HEAD is GitHub's test merge, not the commit that will land.
            where = f"as new tag {r.tag} at the commit pushed to main (HEAD here: {sha})"
        else:
            where = f"as new tag {r.tag} at {sha}"
        verb = "Would publish" if args.dry_run else "Publishing"
        print(f"{verb} {r.title} {where} (notes {r.notes}, latest={str(r.latest).lower()})")
    if args.dry_run:
        return 0

    rc = 0
    for r in releases:
        try:
            print(run(create_command(r, repo, sha), cwd=root).strip())
        except subprocess.CalledProcessError as exc:
            # Stop here: whatever is left is retried by the next push or a re-run.
            say_error(f"gh release create {r.tag} failed ({exc.returncode}): {exc.stderr.strip()}")
            return 1
        try:
            run(dispatch_command(r, repo), cwd=root)
            print(f"Started validate on {r.tag}.")
        except subprocess.CalledProcessError as exc:
            say_error(
                f"{r.tag} is released, but starting validate on it failed: {exc.stderr.strip()}. "
                f"Run: gh workflow run validate.yml --repo {repo} --ref {r.tag}"
            )
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
