import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "lib"))
sys.path.insert(0, str(REPO_ROOT))

import install_all  # noqa: E402
import skill_installer as si  # noqa: E402


def make_skill(root, name="demo", version="1.0.0", body="hello"):
    skill = root / name
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(f"---\nname: {name}\nversion: {version}\n---\n{body}\n", encoding="utf-8")
    (skill / "install.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    return skill


class InstallerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.skill = make_skill(self.root / "src")
        self.target = self.root / "global"

    def run_installer(self, *flags):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = si.run(self.skill, ["--json", "--target-dir", str(self.target), *flags])
        return code, json.loads(out.getvalue().strip().splitlines()[-1])


class VersionTests(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(si.parse_version("1.12.3"), (1, 12, 3))

    def test_versions_compare_numerically(self):
        self.assertGreater(si.parse_version("1.10.0"), si.parse_version("1.9.0"))

    def test_bad_version_rejected(self):
        with self.assertRaises(si.InstallerError):
            si.parse_version("1.0")

    def test_frontmatter_fields(self):
        fields = si.parse_frontmatter('---\nname: x\nversion: "2.0.1"\n---\nbody')
        self.assertEqual(fields, {"name": "x", "version": "2.0.1"})

    def test_decide_action_table(self):
        decide = si.decide_action
        self.assertEqual(decide("1.0.0", None, False)[0], si.ACTION_INSTALL)
        self.assertEqual(decide("1.1.0", "1.0.0", False)[0], si.ACTION_UPDATE)
        self.assertEqual(decide("1.0.0", "1.0.0", True)[0], si.ACTION_CURRENT)
        self.assertEqual(decide("1.0.0", "1.0.0", False)[0], si.ACTION_DRIFT)
        self.assertEqual(decide("1.0.0", "1.1.0", False)[0], si.ACTION_NEWER_INSTALLED)
        self.assertEqual(decide("1.0.0", "unversioned", False)[0], si.ACTION_UPDATE)


class InstallFlowTests(InstallerTestCase):
    def test_missing_skill_installs_with_metadata_and_without_installer_files(self):
        code, row = self.run_installer()
        self.assertEqual((code, row["action"], row["did_write"]), (0, "install", True))
        installed = self.target / "demo"
        self.assertTrue((installed / "SKILL.md").is_file())
        self.assertFalse((installed / "install.sh").exists())
        meta = json.loads((installed / si.META_FILE_NAME).read_text())
        self.assertEqual(meta["version"], "1.0.0")
        self.assertTrue(meta["installed_at"].endswith("+00:00"))

    def test_second_run_is_current_and_writes_nothing(self):
        self.run_installer()
        _, row = self.run_installer()
        self.assertEqual((row["action"], row["did_write"]), ("current", False))

    def test_version_bump_updates_and_backs_up(self):
        self.run_installer()
        make_skill(self.root / "src", version="1.1.0", body="changed")
        _, row = self.run_installer()
        self.assertEqual((row["action"], row["did_write"]), ("update", True))
        self.assertIsNotNone(row["backup"])
        self.assertTrue(pathlib.Path(row["backup"]).is_dir())
        self.assertIn("1.1.0", (self.target / "demo" / "SKILL.md").read_text())

    def test_drift_is_reported_and_not_overwritten_without_force(self):
        self.run_installer()
        (self.target / "demo" / "SKILL.md").write_text("---\nversion: 1.0.0\n---\nedited\n")
        _, row = self.run_installer()
        self.assertEqual((row["action"], row["did_write"]), ("drift", False))
        self.assertIn("edited", (self.target / "demo" / "SKILL.md").read_text())
        _, forced = self.run_installer("--force")
        self.assertTrue(forced["did_write"])
        self.assertIn("hello", (self.target / "demo" / "SKILL.md").read_text())

    def test_newer_installed_copy_is_kept(self):
        self.run_installer()
        (self.target / "demo" / "SKILL.md").write_text("---\nversion: 9.0.0\n---\nfuture\n")
        _, row = self.run_installer()
        self.assertEqual((row["action"], row["did_write"]), ("newer-installed", False))

    def test_check_exit_codes_and_no_writes(self):
        code, row = self.run_installer("--check")
        self.assertEqual((code, row["did_write"]), (1, False))
        self.assertFalse(self.target.exists())
        self.run_installer()
        self.assertEqual(self.run_installer("--check")[0], 0)

    def test_dry_run_writes_nothing(self):
        _, row = self.run_installer("--dry-run")
        self.assertEqual((row["action"], row["did_write"]), ("install", False))
        self.assertFalse(self.target.exists())

    def test_missing_version_is_an_error(self):
        (self.skill / "SKILL.md").write_text("---\nname: demo\n---\nbody\n")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(si.run(self.skill, ["--target-dir", str(self.target)]), si.EXIT_ERROR)


class InstallAllTests(unittest.TestCase):
    def test_discovers_only_folders_with_skill_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            make_skill(root, "b")
            make_skill(root, "a")
            (root / "notes").mkdir()
            self.assertEqual([p.name for p in install_all.find_skill_dirs(root)], ["a", "b"])

    def test_skill_without_installer_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(pathlib.Path(tmp), "solo")
            (skill / "install.sh").unlink()
            row = install_all.run_installer(skill, [], None)
            self.assertEqual(row["action"], "no-installer")

    def test_real_goal_skill_checks_against_empty_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = install_all.main(["--check", "--target-dir", tmp])
            self.assertEqual(code, install_all.EXIT_NOT_CURRENT)
            self.assertIn("goal", out.getvalue())


if __name__ == "__main__":
    unittest.main()
