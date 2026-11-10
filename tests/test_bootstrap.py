import builtins
import contextlib
import io
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import bootstrap  # noqa: E402
import install  # noqa: E402


class SetupHomeTests(unittest.TestCase):
    def test_environment_override(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"COLIBRI_SETUP_HOME": directory}):
                self.assertEqual(bootstrap.default_setup_home(), Path(directory).resolve())


@unittest.skipUnless(shutil.which("git"), "git is required for checkout guards")
class BootstrapGuardTests(unittest.TestCase):
    def test_foreign_origin_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            subprocess.run(["git", "init", "-q", str(home)], check=True)
            subprocess.run(["git", "-C", str(home), "remote", "add", "origin",
                            "https://github.com/evil/colibri-environment-setup.git"], check=True)
            with self.assertRaises(RuntimeError) as caught:
                bootstrap.bootstrap_setup(home, allow_fetch=False)
            self.assertIn("Foreign setup origin", str(caught.exception))

    def test_unknown_non_git_source_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / "notes.txt").write_text("user data", encoding="utf-8")
            with self.assertRaises(RuntimeError) as caught:
                bootstrap.bootstrap_setup(home, allow_fetch=False)
            self.assertIn("Unknown setup source", str(caught.exception))

    def test_read_only_plan_never_clones(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "setup"
            with self.assertRaises(RuntimeError) as caught:
                bootstrap.bootstrap_setup(home, allow_fetch=False)
            self.assertIn("no clone was attempted", str(caught.exception))
            self.assertFalse(home.exists())


class FeatureSelectionTests(unittest.TestCase):
    def cs(self):
        class FakeSetup:
            @staticmethod
            def load_manifest():
                return {"repos": [], "features": {
                    "inference": {"description": "run the engine"},
                    "installer": {"description": "download the bootstrap"},
                }}
        return FakeSetup()

    def test_noninteractive_requires_selection(self):
        with mock.patch.object(sys.stdin, "isatty", return_value=False):
            with self.assertRaises(ValueError):
                bootstrap.choose_features(self.cs(), None, False)

    def test_yes_never_selects_everything(self):
        with mock.patch.object(sys.stdin, "isatty", return_value=False):
            with self.assertRaises(ValueError):
                bootstrap.choose_features(self.cs(), None, True)

    def test_invalid_selection_rejected(self):
        with mock.patch.object(sys.stdin, "isatty", return_value=True), \
                mock.patch.object(builtins, "input", return_value="99"):
            with self.assertRaises(ValueError):
                bootstrap.choose_features(self.cs(), None, False)

    def test_all_selection(self):
        package = types.ModuleType("colibri_setup")
        package.__path__ = []
        provision = types.ModuleType("colibri_setup.provision")
        provision.selected_features = lambda manifest, features, all_features: list(manifest["features"])
        with mock.patch.dict(sys.modules, {"colibri_setup": package,
                                           "colibri_setup.provision": provision}):
            selected = bootstrap.choose_features(self.cs(), None, True, all_features=True)
        self.assertEqual(selected, ["inference", "installer"])


class BootstrapEntryTests(unittest.TestCase):
    def test_direct_execution_reaches_the_cli(self):
        with mock.patch.object(sys, "argv", ["bootstrap.py", "--help"]), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                runpy.run_path(str(ROOT / "bootstrap.py"), run_name="__main__")
        self.assertEqual(caught.exception.code, 0)


class InstallEntryTests(unittest.TestCase):
    def test_implicit_mode_downloads_sources_only(self):
        with mock.patch.object(install, "main", return_value=0) as called:
            self.assertEqual(install.run(["--features", "inference"]), 0)
        self.assertIn("--fetch-only", called.call_args.args[0])

    def test_explicit_modes_are_not_rewritten(self):
        for argv in (["--plan"], ["--dry-run"], ["--install"], ["--fetch-only"],
                     ["--build", "--all"], ["--help"]):
            with self.subTest(argv=argv), \
                    mock.patch.object(install, "main", return_value=0) as called:
                install.run(argv)
            self.assertEqual(called.call_args.args[0], argv)

    def test_exit_code_propagates(self):
        with mock.patch.object(install, "main", return_value=1):
            self.assertEqual(install.run(["--install", "--features", "inference"]), 1)


if __name__ == "__main__":
    unittest.main()
