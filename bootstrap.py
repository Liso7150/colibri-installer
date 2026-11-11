"""Portable bootstrap orchestration; all mutations require an explicit mode."""
from __future__ import annotations

import argparse
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

SETUP_REPO = "https://github.com/Liso7150/fennec-environment-setup.git"
ROOT_SUBDIRS = ("engine", "suite", "models", "cache", "setup")
LAYOUT_HELP = {
    "engine": "Colibri engine checkout (upstream base idea)",
    "suite": "suite sources: desktop, core, CLI, plugins, fine-tuning",
    "models": "model weights you add later (nothing is downloaded here)",
    "cache": "pip / npm / Hugging Face caches",
    "setup": "environment setup hub used by this installer",
}


def default_destination(home=None):
    return Path(home or Path.home()) / "Fennec"


def available_volumes():
    """Writable fixed volumes, largest free space first (Windows only)."""
    if os.name != "nt":
        return []
    volumes = []
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        root = Path(f"{letter}:\\")
        try:
            if not root.is_dir():
                continue
            free = shutil.disk_usage(root).free / (1024 ** 3)
        except OSError:
            continue
        volumes.append((root, free))
    return sorted(volumes, key=lambda item: item[1], reverse=True)


def drive_destination(value, *, folder="Fennec", home=None):
    """Resolve a drive letter (`E`, `E:`, `E:/`) to the default folder on it."""
    raw = os.path.expandvars(str(value)).strip().rstrip("\\/")
    if not raw:
        raise ValueError("Choose a drive letter or a folder")
    if len(raw) == 1 and raw.isalpha():
        raw = f"{raw}:"
    if len(raw) == 2 and raw[1] == ":":
        return validate_destination(f"{raw}/{folder}", home=home)
    return validate_destination(raw, home=home)


def layout(root):
    root = Path(root)
    return {name: root / name for name in ROOT_SUBDIRS}


def validate_destination(value, *, home=None):
    """Expand, normalize and sanity-check an install destination."""
    raw = os.path.expandvars(str(value)).strip()
    if not raw:
        raise ValueError("Install destination cannot be empty")
    if raw == "~" or raw.startswith(("~/", "~\\")):
        raw = str(Path(home or Path.home())) + raw[1:]
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    if path.parent == path:
        raise ValueError("Choose an install folder, not a drive or filesystem root")
    if path.exists() and not path.is_dir():
        raise ValueError(f"Install destination is a file: {path}")
    anchor = path if path.exists() else path.parent
    while not anchor.exists() and anchor != anchor.parent:
        anchor = anchor.parent
    if not anchor.exists():
        raise ValueError(f"The destination volume does not exist: {path}")
    if not os.access(anchor, os.W_OK):
        raise ValueError(f"Install destination is not writable: {anchor}")
    return path


def _free_gib(path):
    anchor = path
    while not anchor.exists() and anchor != anchor.parent:
        anchor = anchor.parent
    try:
        return shutil.disk_usage(anchor).free / (1024 ** 3)
    except OSError:
        return None


def choose_destination(value=None, assume_yes=False, *, interactive=None, home=None,
                       ask=input, echo=print):
    """Return the chosen local root, or None when the caller should use defaults.

    The prompt only appears on an interactive terminal without --yes; explicit
    paths are validated but never re-prompted.
    """
    if value:
        return validate_destination(value, home=home)
    if assume_yes:
        return None
    if interactive is None:
        interactive = sys.stdin.isatty()
    if not interactive:
        return None
    default = default_destination(home)
    volumes = available_volumes()
    while True:
        if volumes:
            echo("\nWhere should Fennec be installed? Any drive or folder works:")
            echo(f"  [d] {default}  (default)")
            for index, (root, free) in enumerate(volumes, 1):
                echo(f"  [{index}] {root}Fennec  ({free:.1f} GiB free)")
            echo("  or type another folder, for example E:/Apps/Fennec")
            prompt = "Install destination [d]: "
        else:
            prompt = f"Install destination for Fennec [{default}]: "
        raw = ask(prompt).strip()
        try:
            if not raw or raw.lower() in ("d", "default"):
                chosen = validate_destination(default, home=home)
            elif raw.isdigit() and volumes and 1 <= int(raw) <= len(volumes):
                chosen = validate_destination(volumes[int(raw) - 1][0] / "Fennec", home=home)
            else:
                chosen = drive_destination(raw, home=home)
        except ValueError as exc:
            echo(f"  {exc}")
            continue
        parts = layout(chosen)
        if chosen.exists() and any(chosen.iterdir()) and not any(p.exists() for p in parts.values()):
            if ask(f"{chosen} is not empty and has no Fennec layout. Use it anyway? [y/N] ").strip().lower() not in ("y", "yes"):
                continue
        echo(f"\nEverything goes under {chosen} and stays on this device:")
        for name, path in parts.items():
            echo(f"  {name:<7} {path}  - {LAYOUT_HELP[name]}")
        free = _free_gib(chosen)
        if free is not None:
            echo(f"  free on this volume: {free:.1f} GiB")
        echo("Repositories are downloaded from GitHub; no models are downloaded and nothing is uploaded.\n")
        if ask("Use this destination? [Y/n] ").strip().lower() in ("", "y", "yes"):
            return chosen


def default_setup_home():
    if os.environ.get("FENNEC_SETUP_HOME"):
        return Path(os.environ["FENNEC_SETUP_HOME"]).expanduser().resolve()
    return Path.home() / "Fennec-Environment-Setup"


def _git(args, cwd=None):
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                                timeout=600, shell=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Git is required to bootstrap the setup hub: {exc}") from exc
    if result.returncode:
        raise RuntimeError(f"Setup hub git {args[0]} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def bootstrap_setup(home, *, allow_fetch=False):
    if globals().get("__loader__") and type(__loader__).__module__ == "zipimport":
        return importlib.import_module("fennec_setup")
    home = Path(home).expanduser().resolve()
    if home.exists() and any(home.iterdir()):
        if not (home / ".git").exists():
            raise RuntimeError(f"Unknown setup source at {home}; use a verified Git checkout or the bundled .pyz")
        origin = _git(["remote", "get-url", "--all", "origin"], cwd=home)
        if origin.startswith("git@github.com:"):
            origin = "https://github.com/" + origin[len("git@github.com:"):]
        parsed = urlsplit(origin)
        path = parsed.path.rstrip("/").removesuffix(".git")
        if (parsed.scheme not in ("https", "ssh") or parsed.hostname != "github.com" or
                parsed.password or parsed.query or parsed.fragment or
                (parsed.username and not (parsed.scheme == "ssh" and parsed.username == "git")) or
                parsed.port not in (None, 22 if parsed.scheme == "ssh" else 443) or
                path != "/Liso7150/fennec-environment-setup"):
            raise RuntimeError(f"Foreign setup origin at {home}; expected {SETUP_REPO}")
        branch = _git(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=home)
        if branch != "main":
            raise RuntimeError(f"Setup hub must be on main, not {branch}; no automatic reset/checkout")
    else:
        if not allow_fetch:
            raise RuntimeError("Read-only plan needs the setup hub. Use --setup-home /existing/verified/checkout or a bundled fennec-bootstrap.pyz; no clone was attempted.")
        home.parent.mkdir(parents=True, exist_ok=True)
        print(f"Fetching setup hub only -> {home}", flush=True)
        _git(["clone", "--branch", "main", "--", SETUP_REPO, str(home)])
    if not (home / "fennec_setup/provision.py").is_file():
        raise RuntimeError("Setup hub lacks the portable provisioning API; update that checkout explicitly after reviewing local changes")
    sys.path.insert(0, str(home))
    return importlib.import_module("fennec_setup")


def choose_features(cs, preselected, assume_yes, *, all_features=False, recommendations=()):
    manifest = cs.load_manifest()
    if preselected or all_features:
        from fennec_setup.provision import selected_features
        return selected_features(manifest, preselected, all_features)
    if assume_yes or not sys.stdin.isatty():
        raise ValueError("Noninteractive use requires --features or --all; --yes never selects everything")
    names = list(manifest["features"])
    print("\nInstallable features:")
    for number, name in enumerate(names, 1):
        print(f"  [{number}] {name}: {manifest['features'][name]['description']}")
    print("Recommendation: " + ", ".join(recommendations))
    raw = input("Select numbers/names comma-separated, or 'all' (no default): ").strip()
    if raw.lower() in ("a", "all"):
        return names
    chosen = []
    for token in raw.split(","):
        token = token.strip()
        if token.isdigit() and 1 <= int(token) <= len(names):
            token = names[int(token) - 1]
        if token not in names:
            raise ValueError(f"Invalid feature selection: {token!r}")
        chosen.append(token)
    return list(dict.fromkeys(chosen))


VERSION = "2.0.0"


def parser():
    ap = argparse.ArgumentParser(description="Portable Fennec environment bootstrap")
    ap.add_argument("--version", action="version", version=f"fennec-installer {VERSION}")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--plan", "--dry-run", action="store_true", help="read-only action plan")
    mode.add_argument("--fetch-only", action="store_true", help="sources only, no installs/config writes")
    mode.add_argument("--install", action="store_true", help="fetch and install selected dependencies")
    ap.add_argument("--build", action="store_true", help="install and build native target, or include build in --plan")
    selection = ap.add_mutually_exclusive_group()
    selection.add_argument("--features")
    selection.add_argument("--all", action="store_true")
    ap.add_argument("--yes", action="store_true", help="confirm explicit actions, never selects features")
    ap.add_argument("--setup-home", type=Path)
    ap.add_argument("--manifest", help="alternate trusted manifest")
    ap.add_argument("--root", help="install destination: ROOT/{engine,suite,models,cache,setup}; "
                                   "prompted on an interactive run when omitted (default ~/Colibri)")
    ap.add_argument("--drive", help="install into <DRIVE>/Fennec instead of ~/Colibri; "
                                     "accepts C, C: or E:/Apps/Fennec")
    ap.add_argument("--config")
    for key in ("engine-root", "suite-root", "models-root", "cache-root", "python", "model",
                "engine-url", "web-root", "workspace", "backend", "policy",
                "jev-root", "openbot-url"):
        ap.add_argument("--" + key)
    ap.add_argument("--ctx", type=int)
    ap.add_argument("--native-target", default="fennec")
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--json", action="store_true", help="JSON in --plan mode only")
    return ap


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.fetch_only and args.build:
            raise ValueError("--build cannot be combined with --fetch-only")
        if not (args.plan or args.fetch_only or args.install):
            if args.build:
                args.install = True
            elif args.update:
                args.fetch_only = True
            elif args.yes or not sys.stdin.isatty():
                args.plan = True
            else:
                choice = input("Action: [1] plan (default), [2] fetch only, [3] install: ").strip() or "1"
                if choice not in ("1", "2", "3"):
                    raise ValueError("Invalid action; choose 1, 2 or 3")
                args.plan, args.fetch_only, args.install = choice == "1", choice == "2", choice == "3"
        if args.json and not args.plan:
            raise ValueError("--json requires --plan")
        if args.plan and not (args.features or args.all) and args.json:
            raise ValueError("JSON planning requires --features or --all")
        explicit_roots = any(getattr(args, key, None) for key in
                             ("engine_root", "suite_root", "models_root", "cache_root"))
        if args.drive and args.root:
            raise ValueError("--drive and --root are alternatives; pass only one")
        if args.drive:
            args.root = str(drive_destination(args.drive))
        elif args.root or not explicit_roots:
            chosen = choose_destination(args.root, args.yes)
            if chosen is not None:
                args.root = str(chosen)
        if not args.plan and not args.yes:
            if not sys.stdin.isatty():
                raise ValueError("Noninteractive mutation requires --yes and an explicit mode/selection")
            if input("Allow source downloads (and selected install actions if requested)? [y/N] ").strip().lower() not in ("y", "yes"):
                print("Aborted; nothing ran.")
                return 0
        if not args.plan and args.yes and not (args.features or args.all or args.update):
            raise ValueError("--yes requires --features or --all (or --update for installed checkouts)")
        home = args.setup_home or (Path(args.root).expanduser() / "setup" if args.root else default_setup_home())
        cs = bootstrap_setup(home, allow_fetch=not args.plan)
        from fennec_setup.config import KEYS
        from fennec_setup.provision import plan_from_args, print_plan, execute_plan, selected_features, update_installed
        manifest = cs.load_manifest(args.manifest)
        if args.update and not (args.features or args.all):
            count = update_installed(manifest, root=args.root, config=args.config,
                                     overrides={key: getattr(args, key, None) for key in KEYS})
            print(f"Updated {count} checkout(s). Rebuild any artifacts you distribute; the engine checkout is never moved implicitly.")
            return 0
        if args.features or args.all:
            features = selected_features(manifest, args.features, args.all)
        else:
            class MenuSetup:
                @staticmethod
                def load_manifest():
                    return manifest
            features = choose_features(MenuSetup, None, args.yes,
                                       recommendations=cs.recommend(cs.detect())["features"])
        plan = plan_from_args(manifest, args, features)
        if args.root and not args.json:
            print(f"Destination: {args.root} - repositories, venv, models and caches stay on this device")
        print_plan(plan, machine=args.json)
        if not args.plan:
            execute_plan(plan, install=args.install)
        return 0
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
