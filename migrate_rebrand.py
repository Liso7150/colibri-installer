#!/usr/bin/env python3
"""One-shot local migration for the Colibri -> Fennec rebrand.

    python migrate_rebrand.py            # print the plan, change nothing
    python migrate_rebrand.py --apply    # perform it

Idempotent: if a folder is locked (Qoder's indexer holds the desktop build's
release-*/app.asar, the IDE holds its plugin jar) the rename is reported and the
run stops before any config is rewritten. Close Qoder and every JetBrains IDE,
then re-run --apply to finish.

The engine checkout D:/Colibri is upstream JustVugg/colibri and keeps its name,
its COLI_* variables and its c/coli entry point. Only the model path inside its
local stack scripts follows the models folder rename.

Run the companion migrate-fennec.bat from OUTSIDE the suite (copy it to D:\\):
a batch file inside a directory being renamed holds a handle that blocks it.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

REPO_DIRS = {
    "colibri-coding-agent": "fennec-coding-agent",
    "colibri-finetune": "fennec-finetune",
    "colibri-installer": "fennec-installer",
    "colibri-jetbrains": "fennec-jetbrains",
    "colibri-code": "fennec-desktop",
    "colibri-core": "fennec-core",
    "colibri-cli": "fennec-cli",
    "colibri-patch": "fennec-patch",
}
PACKAGE_DIRS = {
    "colibri_setup": "fennec_setup",
    "colibri_cli": "fennec_cli",
    "colibri_core": "fennec_core",
}
CACHE_DIRS = {
    "colibri-code": "fennec-desktop",
    "colibri-core-serve.log": "fennec-core-serve.log",
    "colibri-patches": "fennec-patches",
    "colibri-unpublished-backup": "fennec-unpublished-backup",
    "colibri-workspace-docs": "fennec-workspace-docs",
    "colibri": "fennec",
}
HUB_NAMES = ("Colibri-Enviorment-Setup", "Colibri-Environment-Setup")
BACKUP_SUFFIX = ".bak-fennec-rebrand"
LEGACY_AGENT_ID = "colibri"
LEGACY_INSTALL_KEY = "acp.registry.colibri"


@dataclass
class Roots:
    suite: Path
    new_suite: Path
    models: Path
    new_models: Path
    cache: Path
    engine: Path
    home: Path
    roaming: Path
    local: Path
    hub: Path | None = None
    new_hub: Path | None = None


def discover(suite: str | None = None) -> Roots:
    """Locate the current layout, preferring an explicit --suite."""
    candidates = []
    if suite:
        candidates.append(Path(suite).expanduser().resolve())
    here = Path(__file__).resolve().parent.parent
    if (here / "fennec-installer").is_dir() or (here / "colibri-code").is_dir():
        candidates.append(here)
    candidates += [Path("D:/Fennec-Suite"), Path("D:/Colibri-Suite")]
    current = next((p for p in candidates if p.is_dir()), None)
    if current is None:
        raise SystemExit("migrate_rebrand: no suite checkout found; pass --suite <dir>")

    drive = current.parent
    home = Path.home()
    appdata = Path(os.environ.get("APPDATA", home / "AppData/Roaming"))
    local = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local"))
    hub = next((drive / name for name in HUB_NAMES if (drive / name).is_dir()), None)
    models = next((p for p in (drive / "fennec-models", drive / "colibri-models") if p.is_dir()),
                  drive / "colibri-models")
    return Roots(
        suite=current,
        new_suite=drive / "Fennec-Suite",
        models=models,
        new_models=drive / "fennec-models",
        cache=drive / ".cache",
        engine=drive / "Colibri",
        home=home,
        roaming=appdata / "JetBrains",
        local=local / "JetBrains",
        hub=hub,
        new_hub=drive / "Fennec-Environment-Setup" if hub else None,
    )


def replacements(roots: Roots) -> list[tuple[str, str]]:
    """Ordered longest-first so D:/Colibri (the engine) is never rewritten."""
    pairs: list[tuple[str, str]] = []

    def add(old: str, new: str) -> None:
        if old == new:
            return
        pairs.append((old.replace("/", "\\"), new.replace("/", "\\")))
        pairs.append((old, new))

    if roots.hub and roots.new_hub:
        add(str(roots.hub), str(roots.new_hub))
    add(str(roots.suite), str(roots.new_suite))
    add(str(roots.models), str(roots.new_models))
    add(str(roots.home / ".colibri-code"), str(roots.home / ".fennec-desktop"))
    add(str(roots.home / ".colibri"), str(roots.home / ".fennec"))
    # CACHE_DIRS is deliberately excluded: its bare "colibri" key would rewrite
    # github.com/JustVugg/colibri, which is upstream and must survive.
    for mapping in (REPO_DIRS, PACKAGE_DIRS):
        for old, new in mapping.items():
            add(old, new)
    add("colibri-acp.py", "fennec-acp.py")
    add("colibri-models", "fennec-models")
    add("Colibri-Suite", "Fennec-Suite")
    for name in HUB_NAMES:
        add(name, "Fennec-Environment-Setup")
    add(".colibri", ".fennec")
    return pairs


def rewrite(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def rewrite_json(value, pairs: list[tuple[str, str]]):
    if isinstance(value, str):
        return rewrite(value, pairs)
    if isinstance(value, list):
        return [rewrite_json(item, pairs) for item in value]
    if isinstance(value, dict):
        return {key: rewrite_json(item, pairs) for key, item in value.items()}
    return value


@dataclass
class Migration:
    roots: Roots
    apply: bool = False
    lines: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    renames: list[tuple[Path, Path]] = field(default_factory=list)

    def say(self, message: str) -> None:
        self.lines.append(message)
        print(message)

    def resolve(self, path: Path) -> Path:
        """A dry run reads through the renames it has planned but not performed."""
        if self.apply:
            return path
        for src, dst in reversed(self.renames):
            try:
                return src / path.relative_to(dst)
            except ValueError:
                continue
        return path

    def rename(self, src: Path, dst: Path) -> bool:
        if src == dst:
            return True
        if not self.resolve(src).exists():
            return True
        if self.resolve(dst).exists():
            self.say(f"  skip   {src} -> {dst} (destination already exists)")
            return True
        self.say(f"  rename {src} -> {dst}")
        self.renames.append((src, dst))
        if not self.apply:
            return True
        try:
            src.rename(dst)
        except OSError as exc:
            self.failures.append(f"{src}: {exc}")
            self.say(f"  FAILED {src}: {exc}")
            return False
        return True

    def backup(self, path: Path) -> None:
        backup = path.with_name(path.name + BACKUP_SUFFIX)
        if not backup.exists():
            shutil.copy2(path, backup)

    def edit_text(self, path: Path, pairs: list[tuple[str, str]]) -> None:
        actual = self.resolve(path)
        if not actual.is_file():
            return
        try:
            original = actual.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            self.say(f"  skip   {path}: {exc}")
            return
        updated = rewrite(original, pairs)
        if updated == original:
            return
        self.say(f"  edit   {path}")
        if self.apply:
            self.backup(path)
            path.write_text(updated, encoding="utf-8", newline="")

    def edit_json(self, path: Path, change) -> None:
        """change(data) -> True when the document was modified."""
        actual = self.resolve(path)
        if not actual.is_file():
            return
        try:
            data = json.loads(actual.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            self.say(f"  skip   {path}: {exc}")
            return
        if not change(data):
            return
        self.say(f"  edit   {path}")
        if self.apply:
            self.backup(path)
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8", newline="")

    # -- phase 1: folders ---------------------------------------------------

    def rename_folders(self) -> bool:
        self.say("Folders")
        steps = [(self.roots.suite / "colibri-code", self.roots.suite / "fennec-desktop"),
                 (self.roots.suite, self.roots.new_suite)]
        if self.roots.hub and self.roots.new_hub:
            steps.append((self.roots.hub, self.roots.new_hub))
        steps.append((self.roots.models, self.roots.new_models))
        steps += [(self.roots.cache / old, self.roots.cache / new)
                  for old, new in CACHE_DIRS.items()]
        steps += [(self.roots.home / ".colibri", self.roots.home / ".fennec"),
                  (self.roots.home / ".colibri-code", self.roots.home / ".fennec-desktop"),
                  (self.roots.home / ".fennec/air/colibri-acp.py",
                   self.roots.home / ".fennec/air/fennec-acp.py")]
        for src, dst in steps:
            if not self.rename(src, dst):
                return False
        return True

    # -- phase 2: contents --------------------------------------------------

    def rewrite_config(self) -> None:
        self.say("Configuration")
        pairs = replacements(self.roots)
        config = self.roots.home / ".fennec/config.json"

        def update(data):
            if not isinstance(data, dict):
                return False
            updated = rewrite_json(data, pairs)
            if updated == data:
                return False
            data.clear()
            data.update(updated)
            return True

        self.edit_json(config, update)
        # The index caches pre-rebrand source text; retire it so the sidecar rebuilds.
        index = self.roots.home / ".fennec-desktop/index/workspace.json"
        if self.resolve(index).is_file():
            self.say(f"  retire {index} (stale code index)")
            if self.apply:
                retired = index.with_name(index.name + BACKUP_SUFFIX)
                if not retired.exists():
                    index.rename(retired)

    def jetbrains_dirs(self) -> list[Path]:
        dirs = []
        for base in (self.roots.roaming, self.roots.local):
            if base.is_dir():
                dirs.extend(sorted(p for p in base.iterdir() if p.is_dir()))
        return dirs

    def rewrite_air(self) -> None:
        self.say("Air registration")
        home = self.roots.home
        pairs = replacements(self.roots)

        def drop_legacy_agent(data):
            agents = data.get("agents") if isinstance(data, dict) else None
            changed = False
            if isinstance(agents, list):
                keep = [a for a in agents
                        if not (isinstance(a, dict) and a.get("id") == LEGACY_AGENT_ID)]
                changed = len(keep) != len(agents)
                if changed:
                    data["agents"] = keep
            elif isinstance(agents, dict):
                for key in (LEGACY_INSTALL_KEY, LEGACY_AGENT_ID):
                    if key in agents:
                        del agents[key]
                        changed = True
            return changed

        def drop_and_relocate(data):
            changed = drop_legacy_agent(data)
            relocated = rewrite_json(data, pairs)
            if relocated != data:
                data.clear()
                data.update(relocated)
                changed = True
            return changed

        self.edit_json(home / ".fennec/air/registry.json", drop_legacy_agent)
        self.edit_json(home / ".jetbrains/acp-registry-installed-overlay.json", drop_and_relocate)

        for base in [self.roots.roaming, *self.jetbrains_dirs()]:
            self.edit_json(base / "acp-agents/installed.json", drop_legacy_agent)

        def drop_picker(data):
            servers = data.get("agent_servers") if isinstance(data, dict) else None
            if not isinstance(servers, dict) or "Colibri" not in servers:
                return False
            entry = servers["Colibri"]
            args = entry.get("args", []) if isinstance(entry, dict) else []
            managed = any("colibri-acp.py" in str(a) or "fennec-acp.py" in str(a) for a in args)
            if not managed:
                self.say("  keep   ~/.jetbrains/acp.json 'Colibri' (not the managed bridge)")
                return False
            del servers["Colibri"]
            return True

        self.edit_json(home / ".jetbrains/acp.json", drop_picker)

        for directory in self.jetbrains_dirs():
            for options in sorted(directory.glob("*.vmoptions")):
                self.edit_text(options, pairs)

    def rewrite_engine_scripts(self) -> None:
        self.say("Engine stack scripts (model path only)")
        scripts = self.roots.engine / "scripts"
        if not scripts.is_dir():
            return
        pairs = [(str(self.roots.models).replace("/", "\\"), str(self.roots.new_models).replace("/", "\\")),
                 (str(self.roots.models), str(self.roots.new_models)),
                 ("colibri-models", "fennec-models")]
        for path in sorted([*scripts.glob("*.py"), *scripts.glob("*.pyw")]):
            self.edit_text(path, pairs)

    def run(self) -> int:
        # A cwd inside the suite holds a handle that blocks renaming it.
        os.chdir(tempfile.gettempdir())
        self.say(f"Fennec rebrand migration ({'apply' if self.apply else 'dry run'})")
        self.say(f"  suite  {self.roots.suite} -> {self.roots.new_suite}")
        if not self.rename_folders():
            self.say("")
            self.say("Stopped: a folder is locked. Close Qoder and every JetBrains IDE,")
            self.say("then re-run with --apply. Nothing below this point was changed.")
            return 1
        self.rewrite_config()
        self.rewrite_air()
        self.rewrite_engine_scripts()
        self.say("")
        if self.apply:
            self.say("Done. Next: install FennecDesktop-1.4.0-x64.exe and FennecDesktop-plugin-1.4.0.zip,")
            self.say("then start the IDE once so it republishes the Fennec Air card.")
            self.say(f"Backups of every edited file sit next to it as *{BACKUP_SUFFIX}.")
        else:
            self.say("Dry run only. Re-run with --apply to perform these changes.")
        return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Migrate local Colibri paths and Air records to Fennec.")
    parser.add_argument("--apply", action="store_true", help="perform the changes (default: dry run)")
    parser.add_argument("--suite", help="suite checkout to migrate (default: auto-detect)")
    args = parser.parse_args(argv)
    return Migration(discover(args.suite), apply=args.apply).run()


if __name__ == "__main__":
    sys.exit(main())