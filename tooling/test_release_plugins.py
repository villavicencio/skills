#!/usr/bin/env python3
"""Unit tests for tooling/release_plugins.py's decision logic (VIL-809).

Stdlib only, no network: GitHub state is passed in as sets.

    python3 tooling/test_release_plugins.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from release_plugins import (  # noqa: E402
    Plugin,
    ReleaseError,
    create_command,
    dispatch_command,
    plan,
    read_plugins,
)

DV = Plugin(name="dv", version="0.14.2", manifest="plugins/dv/.claude-plugin/plugin.json")
RELEASED = {"dv--v0.9.1", "dv--v0.14.1", "dv--v0.10.0", "pickup-handoff--v0.1.0"}
SHA = "a" * 40


def notes_ok(_path: str) -> None:
    return None


def notes_missing(path: str) -> str:
    return f"release notes file missing: {path}"


class PlanTest(unittest.TestCase):
    def test_already_released_does_nothing(self):
        p = Plugin("dv", "0.14.1", DV.manifest)
        self.assertEqual(plan([p], RELEASED, set(), set(), notes_missing), [])

    def test_new_version_gets_new_tag_and_latest(self):
        [r] = plan([DV], RELEASED, set(), set(), notes_ok)
        self.assertEqual(r.tag, "dv--v0.14.2")
        self.assertEqual(r.title, "dv v0.14.2")
        self.assertEqual(r.notes, "docs/release-notes/dv--v0.14.2.md")
        self.assertFalse(r.tag_exists)
        self.assertTrue(r.latest)

    def test_semver_compared_numerically_not_as_text(self):
        # "0.10.0" > "0.9.1" numerically; as text it would sort lower.
        [r] = plan([Plugin("dv", "0.10.1", DV.manifest)], {"dv--v0.9.1", "dv--v0.10.0"},
                   set(), set(), notes_ok)
        self.assertTrue(r.latest)

    def test_existing_tag_without_release_is_released_on_that_tag(self):
        [r] = plan([DV], RELEASED, set(), {"dv--v0.14.2"}, notes_ok)
        self.assertTrue(r.tag_exists)

    def test_older_version_on_existing_tag_is_released_but_not_latest(self):
        p = Plugin("dv", "0.7.2", DV.manifest)
        [r] = plan([p], RELEASED, set(), {"dv--v0.7.2"}, notes_ok)
        self.assertTrue(r.tag_exists)
        self.assertFalse(r.latest)

    def test_older_version_without_tag_is_refused(self):
        p = Plugin("dv", "0.9.0", DV.manifest)
        with self.assertRaises(ReleaseError) as cm:
            plan([p], RELEASED, set(), set(), notes_ok)
        self.assertIn("lower than the released dv 0.14.1", str(cm.exception))
        self.assertIn("main's tip", str(cm.exception))

    def test_older_version_off_tip_is_released_without_latest(self):
        # Two merges whose validate runs finished out of order: 0.14.1 already
        # released from the newer commit, this older commit carries 0.14.0.
        p = Plugin("dv", "0.14.0", DV.manifest)
        [r] = plan([p], {"dv--v0.14.1"}, set(), set(), notes_ok, is_tip=False)
        self.assertFalse(r.tag_exists)
        self.assertFalse(r.latest)

    def test_older_version_on_tip_is_still_refused(self):
        p = Plugin("dv", "0.14.0", DV.manifest)
        with self.assertRaises(ReleaseError):
            plan([p], {"dv--v0.14.1"}, set(), set(), notes_ok, is_tip=True)

    def test_missing_notes_names_the_path_and_plans_nothing(self):
        with self.assertRaises(ReleaseError) as cm:
            plan([DV], RELEASED, set(), set(), notes_missing)
        self.assertIn("docs/release-notes/dv--v0.14.2.md", str(cm.exception))

    def test_one_bad_plugin_blocks_every_release(self):
        other = Plugin("other", "1.0.0", "plugins/other/.claude-plugin/plugin.json")

        def notes(path: str):
            return notes_missing(path) if "other" in path else None

        with self.assertRaises(ReleaseError) as cm:
            plan([DV, other], RELEASED, set(), set(), notes)
        self.assertEqual(len(cm.exception.problems), 1)

    def test_draft_on_the_tag_is_refused(self):
        with self.assertRaises(ReleaseError) as cm:
            plan([DV], RELEASED, {"dv--v0.14.2"}, set(), notes_ok)
        self.assertIn("draft release", str(cm.exception))

    def test_first_release_of_a_plugin_is_latest(self):
        p = Plugin("newplug", "0.1.0", "plugins/newplug/.claude-plugin/plugin.json")
        [r] = plan([p], RELEASED, set(), set(), notes_ok)
        self.assertTrue(r.latest)

    def test_similar_plugin_names_do_not_share_history(self):
        # dv-extra's releases must not count as dv's (and vice versa).
        p = Plugin("dv", "0.1.0", DV.manifest)
        [r] = plan([p], {"dv-extra--v5.0.0"}, set(), set(), notes_ok)
        self.assertTrue(r.latest)


class CommandTest(unittest.TestCase):
    def test_new_tag_targets_the_commit(self):
        [r] = plan([DV], RELEASED, set(), set(), notes_ok)
        cmd = create_command(r, "o/r", SHA)
        self.assertEqual(cmd[:4], ["gh", "release", "create", "dv--v0.14.2"])
        self.assertIn("--latest=true", cmd)
        self.assertEqual(cmd[cmd.index("--target") + 1], SHA)
        self.assertEqual(cmd[cmd.index("--notes-file") + 1], "docs/release-notes/dv--v0.14.2.md")
        self.assertNotIn("--verify-tag", cmd)

    def test_existing_tag_is_verified_not_targeted(self):
        p = Plugin("dv", "0.7.2", DV.manifest)
        [r] = plan([p], RELEASED, set(), {"dv--v0.7.2"}, notes_ok)
        cmd = create_command(r, "o/r", SHA)
        self.assertIn("--verify-tag", cmd)
        self.assertNotIn("--target", cmd)
        self.assertIn("--latest=false", cmd)

    def test_dispatch_runs_validate_on_the_tag(self):
        [r] = plan([DV], RELEASED, set(), set(), notes_ok)
        self.assertEqual(dispatch_command(r, "o/r"),
                         ["gh", "workflow", "run", "validate.yml", "--repo", "o/r",
                          "--ref", "dv--v0.14.2"])


class ReadPluginsTest(unittest.TestCase):
    def write(self, root: Path, dir_name: str, data) -> None:
        d = root / "plugins" / dir_name / ".claude-plugin"
        d.mkdir(parents=True)
        (d / "plugin.json").write_text(json.dumps(data), encoding="utf-8")

    def read(self, dir_name: str, data):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(Path(tmp), dir_name, data)
            return read_plugins(Path(tmp))

    def test_valid_manifest(self):
        self.assertEqual(self.read("dv", {"name": "dv", "version": "1.2.3"}),
                         [Plugin("dv", "1.2.3", "plugins/dv/.claude-plugin/plugin.json")])

    def test_bad_versions_are_rejected(self):
        for v in ["1.2", "01.2.3", "1.2.3-rc.1", "1.2.3+b", "v1.2.3", "1.2.3; rm -rf /", 1, None]:
            with self.subTest(version=v), self.assertRaises(ReleaseError):
                self.read("dv", {"name": "dv", "version": v})

    def test_bad_names_are_rejected(self):
        for n in ["DV", "dv--x", "-dv", "dv;x", "$(x)", "", None]:
            with self.subTest(name=n), self.assertRaises(ReleaseError):
                self.read("dv", {"name": n, "version": "1.0.0"})

    def test_plugin_dir_without_manifest_is_a_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(Path(tmp), "dv", {"name": "dv", "version": "1.0.0"})
            (Path(tmp) / "plugins" / "other").mkdir()
            with self.assertRaises(ReleaseError) as cm:
                read_plugins(Path(tmp))
            self.assertIn("plugins/other/ has no .claude-plugin/plugin.json", str(cm.exception))

    def test_no_plugin_dirs_is_a_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ReleaseError):
                read_plugins(Path(tmp))
            (Path(tmp) / "plugins").mkdir()
            (Path(tmp) / "plugins" / "README.md").write_text("not a plugin", encoding="utf-8")
            with self.assertRaises(ReleaseError):
                read_plugins(Path(tmp))

    def test_name_must_match_directory(self):
        with self.assertRaises(ReleaseError):
            self.read("dv", {"name": "other", "version": "1.0.0"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
