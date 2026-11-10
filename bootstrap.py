"""Portable bootstrap orchestration; all mutations require an explicit mode."""
from __future__ import annotations

import argparse
import importlib
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

SETUP_REPO = "https://github.com/Liso7150/colibri-environment-setup.git"


def default_setup_home():
    if os.environ.get("COLIBRI_SETUP_HOME"):
        return Path(os.environ["COLIBRI_SETUP_HOME"]).expanduser().resolve()
    legacy = Path("D:/Colibri-Enviorment-Setup")
    return legacy if os.name == "nt" and legacy.exists() else Path.home() / "Colibri-Environment-Setup"


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
        return importlib.import_module("colibri_setup")
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
                path != "/Liso7150/colibri-environment-setup"):
            raise RuntimeError(f"Foreign setup origin at {home}; expected {SETUP_REPO}")
        branch = _git(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=home)
        if branch != "main":
            raise RuntimeError(f"Setup hub must be on main, not {branch}; no automatic reset/checkout")
    else:
        if not allow_fetch:
            raise RuntimeError("Read-only plan needs the setup hub. Use --setup-home /existing/verified/checkout or a bundled colibri-bootstrap.pyz; no clone was attempted.")
        home.parent.mkdir(parents=True, exist_ok=True)
        print(f"Fetching setup hub only -> {home}", flush=True)
        _git(["clone", "--branch", "main", "--", SETUP_REPO, str(home)])
    if not (home / "colibri_setup/provision.py").is_file():
        raise RuntimeError("Setup hub lacks the portable provisioning API; update that checkout explicitly after reviewing local changes")
    sys.path.insert(0, str(home))
    return importlib.import_module("colibri_setup")


def choose_features(cs, preselected, assume_yes, *, all_features=False, recommendations=()):
    manifest = cs.load_manifest()
    if preselected or all_features:
        from colibri_setup.provision import selected_features
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


def parser():
    ap = argparse.ArgumentParser(description="Portable Colibri environment bootstrap")
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
    ap.add_argument("--root", help="ROOT/{engine,suite,models,cache}; bootstrap hub at ROOT/setup")
    ap.add_argument("--config")
    for key in ("engine-root", "suite-root", "models-root", "cache-root", "python", "model",
                "engine-url", "web-root", "workspace", "backend", "policy"):
        ap.add_argument("--" + key)
    ap.add_argument("--ctx", type=int)
    ap.add_argument("--native-target", default="colibri")
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
        if not args.plan and not args.yes:
            if not sys.stdin.isatty():
                raise ValueError("Noninteractive mutation requires --yes and an explicit mode/selection")
            if input("Allow source downloads (and selected install actions if requested)? [y/N] ").strip().lower() not in ("y", "yes"):
                print("Aborted; nothing ran.")
                return 0
        if not args.plan and args.yes and not (args.features or args.all):
            raise ValueError("--yes requires --features or --all")
        home = args.setup_home or (Path(args.root).expanduser() / "setup" if args.root else default_setup_home())
        cs = bootstrap_setup(home, allow_fetch=not args.plan)
        from colibri_setup.provision import plan_from_args, print_plan, execute_plan, selected_features
        manifest = cs.load_manifest(args.manifest)
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
        print_plan(plan, machine=args.json)
        if not args.plan:
            execute_plan(plan, install=args.install)
        return 0
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
