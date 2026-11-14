import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import migrate_rebrand as migrate  # noqa: E402


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class LayoutCase(unittest.TestCase):
    def setUp(self):
        self._cwd = Path.cwd()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(lambda: os.chdir(self._cwd))
        self.base = Path(self._tmp.name).resolve()
        self.home = self.base / "home"
        self.suite = self.base / "Colibri-Suite"
        self.hub = self.base / "Colibri-Enviorment-Setup"
        self.models = self.base / "colibri-models"
        self.cache = self.base / ".cache"
        self.engine = self.base / "Colibri"
        self.roots = migrate.Roots(
            suite=self.suite, new_suite=self.base / "Fennec-Suite",
            models=self.models, new_models=self.base / "fennec-models",
            cache=self.cache, engine=self.engine, home=self.home,
            roaming=self.home / "AppData/Roaming/JetBrains",
            local=self.home / "AppData/Local/JetBrains",
            hub=self.hub, new_hub=self.base / "Fennec-Environment-Setup",
        )
        self.build()

    def build(self):
        (self.suite / "colibri-code/electron").mkdir(parents=True)
        (self.suite / "fennec-core").mkdir(parents=True)
        (self.hub / "fennec_setup").mkdir(parents=True)
        (self.models / "qwen36-35b").mkdir(parents=True)
        (self.engine / "scripts").mkdir(parents=True)
        (self.engine / ".venv/Scripts").mkdir(parents=True)
        for name in migrate.CACHE_DIRS:
            (self.cache / name).mkdir(parents=True)
        write_json(self.home / ".colibri/config.json", {
            "engine_root": "D:/Colibri",
            "suite_root": "D:/Colibri-Suite",
            "models_root": "D:/colibri-models",
            "cache_root": "D:/.cache",
            "model": "D:/colibri-models/qwen36-35b",
            "python": "D:/Colibri/.venv/Scripts/python.exe",
            "workspace": "D:/Colibri-Suite",
            "web_root": "D:/Colibri-Suite/colibri-coding-agent/web",
        })
        write_json(self.home / ".colibri/air/registry.json", {
            "version": "1.0.0",
            "agents": [{"id": "qoder"}, {"id": "colibri", "name": "Colibri Code"}],
        })
        (self.home / ".colibri/air/colibri-acp.py").write_text("# bridge\n", encoding="utf-8")
        write_json(self.home / ".colibri-code/index/workspace.json",
                   {"root": "D:/Colibri-Suite/colibri-code/electron", "docs": []})
        write_json(self.home / ".jetbrains/acp-registry-installed-overlay.json", {
            "agents": {migrate.LEGACY_INSTALL_KEY: {"agent": {"distribution": {"local": {
                "command": "D:\\Colibri\\.venv\\Scripts\\python.exe",
                "args": ["C:\\Users\\test\\.colibri\\air\\colibri-acp.py"]}}}}},
        })
        write_json(self.home / ".jetbrains/acp.json", {
            "agent_servers": {"Colibri": {"command": "python",
                                          "args": [str(self.home / ".colibri/air/colibri-acp.py")]}},
        })
        shared = self.roots.roaming / "acp-agents/installed.json"
        write_json(shared, {"agents": {
            migrate.LEGACY_INSTALL_KEY: {"agent": {"id": "colibri"}},
            "acp.registry.qoder": {"agent": {"id": "qoder"}},
        }, "disabledAgents": []})
        config = self.roots.roaming / "IntelliJIdea2026.3"
        config.mkdir(parents=True)
        (config / "idea64.exe.vmoptions").write_text(
            "-Dair.acp.registry.path=C:/Users/test/.colibri/air/registry.json\n", encoding="utf-8")
        (self.engine / "scripts/start_stack.pyw").write_text(
            '"--model", "D:/colibri-models/qwen36-35b",\n', encoding="utf-8")

    def run_migration(self, apply):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = migrate.Migration(self.roots, apply=apply).run()
        return code, out.getvalue()


class DryRunTests(LayoutCase):
    def test_dry_run_changes_nothing(self):
        code, output = self.run_migration(apply=False)
        self.assertEqual(code, 0)
        self.assertIn("dry run", output)
        self.assertTrue((self.suite / "colibri-code").is_dir())
        self.assertTrue((self.home / ".colibri/config.json").is_file())
        self.assertFalse((self.home / ".fennec").exists())
        self.assertFalse(self.roots.new_suite.exists())
        data = json.loads((self.home / ".colibri/config.json").read_text(encoding="utf-8"))
        self.assertEqual(data["suite_root"], "D:/Colibri-Suite")


class ApplyTests(LayoutCase):
    def test_folders_are_renamed(self):
        code, _ = self.run_migration(apply=True)
        self.assertEqual(code, 0)
        self.assertFalse(self.suite.exists())
        self.assertTrue((self.roots.new_suite / "fennec-desktop/electron").is_dir())
        self.assertTrue((self.roots.new_suite / "fennec-core").is_dir())
        self.assertTrue((self.base / "Fennec-Environment-Setup/fennec_setup").is_dir())
        self.assertTrue((self.base / "fennec-models/qwen36-35b").is_dir())
        self.assertTrue((self.cache / "fennec").is_dir())
        self.assertTrue((self.cache / "fennec-desktop").is_dir())
        self.assertTrue((self.home / ".fennec/air/fennec-acp.py").is_file())
        self.assertTrue((self.home / ".fennec-desktop").is_dir())

    def test_engine_checkout_is_left_alone(self):
        self.run_migration(apply=True)
        self.assertTrue(self.engine.is_dir())
        self.assertTrue((self.engine / ".venv/Scripts").is_dir())

    def test_config_roots_move_but_engine_and_python_stay(self):
        self.run_migration(apply=True)
        data = json.loads((self.home / ".fennec/config.json").read_text(encoding="utf-8"))
        self.assertEqual(data["engine_root"], "D:/Colibri")
        self.assertEqual(data["python"], "D:/Colibri/.venv/Scripts/python.exe")
        self.assertEqual(data["cache_root"], "D:/.cache")
        self.assertEqual(data["suite_root"], "D:/Fennec-Suite")
        self.assertEqual(data["models_root"], "D:/fennec-models")
        self.assertEqual(data["model"], "D:/fennec-models/qwen36-35b")
        self.assertEqual(data["web_root"], "D:/Fennec-Suite/fennec-coding-agent/web")
        self.assertTrue((self.home / ".fennec/config.json.bak-fennec-rebrand").is_file())

    def test_legacy_air_records_are_dropped(self):
        self.run_migration(apply=True)
        registry = json.loads((self.home / ".fennec/air/registry.json").read_text(encoding="utf-8"))
        self.assertEqual([a["id"] for a in registry["agents"]], ["qoder"])
        overlay = json.loads((self.home / ".jetbrains/acp-registry-installed-overlay.json")
                             .read_text(encoding="utf-8"))
        self.assertEqual(overlay["agents"], {})
        installed = json.loads((self.roots.roaming / "acp-agents/installed.json")
                               .read_text(encoding="utf-8"))
        self.assertEqual(list(installed["agents"]), ["acp.registry.qoder"])
        picker = json.loads((self.home / ".jetbrains/acp.json").read_text(encoding="utf-8"))
        self.assertEqual(picker["agent_servers"], {})

    def test_existing_fennec_registration_survives(self):
        installed = self.roots.roaming / "acp-agents/installed.json"
        data = json.loads(installed.read_text(encoding="utf-8"))
        data["agents"]["acp.registry.fennec"] = {"agent": {"id": "fennec", "version": "1.4.0"}}
        write_json(installed, data)
        self.run_migration(apply=True)
        after = json.loads(installed.read_text(encoding="utf-8"))
        self.assertIn("acp.registry.fennec", after["agents"])
        self.assertNotIn(migrate.LEGACY_INSTALL_KEY, after["agents"])

    def test_vmoptions_points_at_the_new_registry(self):
        self.run_migration(apply=True)
        options = (self.roots.roaming / "IntelliJIdea2026.3/idea64.exe.vmoptions").read_text(
            encoding="utf-8")
        self.assertEqual(options, "-Dair.acp.registry.path=C:/Users/test/.fennec/air/registry.json\n")

    def test_stale_code_index_is_retired_not_rewritten(self):
        self.run_migration(apply=True)
        index = self.home / ".fennec-desktop/index/workspace.json"
        self.assertFalse(index.exists())
        retired = json.loads((index.parent / "workspace.json.bak-fennec-rebrand")
                             .read_text(encoding="utf-8"))
        self.assertEqual(retired["root"], "D:/Colibri-Suite/colibri-code/electron")

    def test_engine_script_follows_the_models_rename(self):
        self.run_migration(apply=True)
        script = (self.engine / "scripts/start_stack.pyw").read_text(encoding="utf-8")
        self.assertIn("D:/fennec-models/qwen36-35b", script)
        self.assertNotIn("colibri-models", script)

    def test_second_run_is_a_no_op(self):
        self.run_migration(apply=True)
        before = {p: p.read_bytes() for p in self.base.rglob("*") if p.is_file()}
        code, output = self.run_migration(apply=True)
        self.assertEqual(code, 0)
        self.assertNotIn("FAILED", output)
        after = {p: p.read_bytes() for p in self.base.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


class SafetyTests(LayoutCase):
    def test_locked_folder_stops_before_any_rewrite(self):
        real_rename = Path.rename

        def guarded(path, target):
            if path == self.suite:
                raise OSError("Device or resource busy")
            return real_rename(path, target)

        with mock.patch.object(Path, "rename", guarded):
            code, output = self.run_migration(apply=True)
        self.assertEqual(code, 1)
        self.assertIn("Close Qoder", output)
        self.assertTrue((self.home / ".colibri/config.json").is_file())
        self.assertFalse((self.home / ".fennec").exists())
        self.assertTrue(self.hub.is_dir())
        self.assertTrue(self.models.is_dir())
        self.assertTrue((self.roots.roaming / "acp-agents/installed.json").is_file())

    def test_existing_destination_is_never_overwritten(self):
        (self.base / "fennec-models/marker").mkdir(parents=True)
        (self.base / "fennec-models/marker/keep.txt").write_text("precious", encoding="utf-8")
        code, output = self.run_migration(apply=True)
        self.assertEqual(code, 0)
        self.assertIn("destination already exists", output)
        self.assertTrue((self.models / "qwen36-35b").is_dir())
        self.assertEqual((self.base / "fennec-models/marker/keep.txt").read_text(), "precious")

    def test_unmanaged_picker_entry_is_kept(self):
        write_json(self.home / ".jetbrains/acp.json",
                   {"agent_servers": {"Colibri": {"command": "my-own-tool", "args": ["--serve"]}}})
        _, output = self.run_migration(apply=True)
        self.assertIn("not the managed bridge", output)
        picker = json.loads((self.home / ".jetbrains/acp.json").read_text(encoding="utf-8"))
        self.assertIn("Colibri", picker["agent_servers"])


class FennecEngineTests(unittest.TestCase):
    """A Fennec-based install migrates too, and its engine root is preserved."""

    def setUp(self):
        self._cwd = Path.cwd()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(lambda: os.chdir(self._cwd))
        self.base = Path(self._tmp.name).resolve()
        self.home = self.base / "home"
        self.suite = self.base / "Colibri-Suite"
        self.models = self.base / "colibri-models"
        self.engine = self.base / "Fennec"
        self.roots = migrate.Roots(
            suite=self.suite, new_suite=self.base / "Fennec-Suite",
            models=self.models, new_models=self.base / "fennec-models",
            cache=self.base / ".cache", engine=self.engine, home=self.home,
            roaming=self.home / "AppData/Roaming/JetBrains",
            local=self.home / "AppData/Local/JetBrains",
        )
        (self.suite / "colibri-code").mkdir(parents=True)
        (self.models / "qwen36-35b").mkdir(parents=True)
        (self.engine / "target/release").mkdir(parents=True)
        (self.engine / "Cargo.toml").write_text("[package]\nname = 'fennec'\n", encoding="utf-8")
        (self.engine / "target/release/fennec.exe").write_bytes(b"")
        (self.engine / "scripts").mkdir(parents=True)
        (self.engine / "scripts/start_stack.pyw").write_text(
            '"--model", "D:/colibri-models/qwen36-35b",\n', encoding="utf-8")
        write_json(self.home / ".colibri/config.json", {
            "engine_root": "D:/Fennec",
            "suite_root": "D:/Colibri-Suite",
            "models_root": "D:/colibri-models",
            "model": "D:/colibri-models/qwen36-35b",
            "engine_url": "http://127.0.0.1:8184",
        })

    def run_migration(self, apply=True):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = migrate.Migration(self.roots, apply=apply).run()
        return code, out.getvalue()

    def test_fennec_root_is_recognised_and_never_renamed(self):
        code, output = self.run_migration()
        self.assertEqual(code, 0)
        self.assertIn("fennec; kept", output)
        self.assertTrue((self.engine / "Cargo.toml").is_file())
        self.assertTrue((self.engine / "target/release/fennec.exe").is_file())
        data = json.loads((self.home / ".fennec/config.json").read_text(encoding="utf-8"))
        self.assertEqual(data["engine_root"], "D:/Fennec")
        self.assertEqual(data["engine_url"], "http://127.0.0.1:8184")
        self.assertEqual(data["suite_root"], "D:/Fennec-Suite")
        self.assertEqual(data["model"], "D:/fennec-models/qwen36-35b")

    def test_fennec_identities_survive_the_rewrite(self):
        pairs = migrate.replacements(self.roots)
        for value in ("D:/Fennec", "D:/Fennec/target/release/fennec.exe", "D:\\Fennec",
                      "~/Fennec", "FENNEC_API_KEY", "COLI_API_KEY", "FENNEC_HOME",
                      "Cargo.toml", "cargo build --release", "c/coli",
                      "https://github.com/Liso7150/fennec"):
            self.assertEqual(migrate.rewrite(value, pairs), value, value)

    def test_fennec_stack_scripts_follow_the_models_rename(self):
        self.run_migration()
        script = (self.engine / "scripts/start_stack.pyw").read_text(encoding="utf-8")
        self.assertIn("D:/fennec-models/qwen36-35b", script)
        self.assertNotIn("colibri-models", script)

    def test_engine_kind_detection(self):
        self.assertEqual(migrate.engine_kind(self.engine), "fennec")
        legacy = self.base / "Colibri"
        (legacy / "c").mkdir(parents=True)
        (legacy / "c/coli").write_text("# launcher\n", encoding="utf-8")
        self.assertEqual(migrate.engine_kind(legacy), "colibri")

    def test_discover_prefers_fennec_and_falls_back_to_colibri(self):
        legacy = self.base / "Colibri"
        legacy.mkdir()
        self.assertEqual(migrate.discover(str(self.suite)).engine, self.engine)
        with tempfile.TemporaryDirectory() as other:
            base = Path(other).resolve()
            suite = base / "Colibri-Suite"
            (suite / "colibri-code").mkdir(parents=True)
            (base / "Colibri").mkdir()
            self.assertEqual(migrate.discover(str(suite)).engine, base / "Colibri")

    def test_a_fennec_engine_root_in_a_clean_layout_is_preserved(self):
        roots = migrate.Roots(
            suite=self.suite, new_suite=self.base / "Fennec-Suite",
            models=self.models, new_models=self.base / "fennec-models",
            cache=self.base / ".cache", engine=self.base / "Fennec" / "engine",
            home=self.home, roaming=self.roots.roaming, local=self.roots.local,
        )
        pairs = migrate.replacements(roots)
        for value in (str(roots.engine), str(roots.engine / "target/release/fennec.exe"),
                      str(roots.engine / "Cargo.toml")):
            self.assertEqual(migrate.rewrite(value, pairs), value, value)
        # The suite around the engine still migrates.
        self.assertEqual(migrate.rewrite(str(self.suite / "colibri-code"), pairs),
                         str(roots.new_suite / "fennec-desktop"))


class ReplacementTests(unittest.TestCase):
    def setUp(self):
        self.roots = migrate.Roots(
            suite=Path("D:/Colibri-Suite"), new_suite=Path("D:/Fennec-Suite"),
            models=Path("D:/colibri-models"), new_models=Path("D:/fennec-models"),
            cache=Path("D:/.cache"), engine=Path("D:/Colibri"), home=Path("C:/Users/test"),
            roaming=Path("C:/Users/test/AppData/Roaming/JetBrains"),
            local=Path("C:/Users/test/AppData/Local/JetBrains"),
            hub=Path("D:/Colibri-Enviorment-Setup"),
            new_hub=Path("D:/Fennec-Environment-Setup"),
        )
        self.pairs = migrate.replacements(self.roots)

    def test_upstream_engine_identities_survive(self):
        for value in ("D:/Colibri", "D:/Colibri/.venv/Scripts/python.exe", "D:\\Colibri",
                      "~/Colibri", "COLI_MODEL", "COLI_VULKAN", "c/coli", "colibri/cli.py",
                      "https://github.com/JustVugg/colibri", "Colibri engine"):
            self.assertEqual(migrate.rewrite(value, self.pairs), value, value)

    def test_suite_paths_move(self):
        self.assertEqual(migrate.rewrite("D:/Colibri-Suite/colibri-code/electron", self.pairs),
                         "D:/Fennec-Suite/fennec-desktop/electron")
        self.assertEqual(migrate.rewrite("D:\\Colibri-Suite\\colibri-coding-agent\\web", self.pairs),
                         "D:\\Fennec-Suite\\fennec-coding-agent\\web")
        self.assertEqual(migrate.rewrite("D:/Colibri-Enviorment-Setup/setup.py", self.pairs),
                         "D:/Fennec-Environment-Setup/setup.py")

    def test_home_dot_dirs_move(self):
        self.assertEqual(migrate.rewrite("C:/Users/test/.colibri/air/colibri-acp.py", self.pairs),
                         "C:/Users/test/.fennec/air/fennec-acp.py")
        self.assertEqual(migrate.rewrite("C:\\Users\\test\\.colibri-code\\index", self.pairs),
                         "C:\\Users\\test\\.fennec-desktop\\index")
        self.assertEqual(migrate.rewrite("~/.colibri/config.json", self.pairs),
                         "~/.fennec/config.json")

    def test_models_move(self):
        self.assertEqual(migrate.rewrite("D:/colibri-models/qwen36-35b", self.pairs),
                         "D:/fennec-models/qwen36-35b")


if __name__ == "__main__":
    unittest.main()