#!/usr/bin/env python3
"""Colibri installer — the whole-environment entry point.

Detects your device (OS/arch/GPU/NPU/RAM/disk), recommends a config, and lets you
choose which features/apps to install. It bootstraps the colibri-environment-setup
hub and fetches the selected repos into the suite layout.

    python install.py                 # interactive device-aware menu
    python install.py --features inference,desktop
    python install.py --all --yes     # unattended, everything

Credits: Colibri engine (https://github.com/JustVugg/colibri) and
AirLLM (https://github.com/lyogavin/airllm).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

SETUP_REPO = "https://github.com/Liso7150/colibri-environment-setup.git"
DEFAULT_SETUP_HOME = Path(os.environ.get("COLIBRI_SETUP_HOME", r"D:/Colibri-Enviorment-Setup"))


def bootstrap_setup(home: Path):
    if not (home / "colibri_setup").exists():
        print(f"fetching setup hub -> {home}", flush=True)
        home.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["git", "clone", SETUP_REPO, str(home)], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"failed to clone setup hub: {r.stderr.strip()}")
    sys.path.insert(0, str(home))
    import colibri_setup  # noqa: E402
    return colibri_setup


def choose_features(cs, preselected, assume_yes):
    manifest = cs.load_manifest()
    names = list(manifest["features"])
    if preselected:
        chosen = [f.strip() for f in preselected.split(",") if f.strip()]
        bad = [f for f in chosen if f not in names]
        if bad:
            sys.exit(f"unknown features: {bad}; available: {names}")
        return chosen
    print("\nInstallable features:")
    for i, name in enumerate(names, 1):
        spec = manifest["features"][name]
        print(f"  [{i}] {name:14s} {spec['description']}")
    print("  [a] all of the above")
    if assume_yes:
        return names
    raw = input("\nSelect features (numbers/names comma-separated, or 'a'): ").strip()
    if raw.lower() in ("a", "all", ""):
        return names
    chosen = []
    for tok in raw.split(","):
        tok = tok.strip()
        if tok.isdigit() and 1 <= int(tok) <= len(names):
            chosen.append(names[int(tok) - 1])
        elif tok in names:
            chosen.append(tok)
    return chosen or names


def main():
    ap = argparse.ArgumentParser(description="Colibri whole-environment installer")
    ap.add_argument("--features", help="comma-separated features (skips the menu)")
    ap.add_argument("--all", action="store_true", help="select every feature")
    ap.add_argument("--yes", action="store_true", help="no prompts")
    ap.add_argument("--setup-home", type=Path, default=DEFAULT_SETUP_HOME)
    ap.add_argument("--update", action="store_true", help="git pull existing repos")
    args = ap.parse_args()

    cs = bootstrap_setup(args.setup_home)
    dev = cs.detect()
    rec = cs.recommend(dev)
    print("=" * 60)
    print("Colibri installer — device summary")
    print("=" * 60)
    print(f"  OS        : {dev.os} {dev.os_version} ({dev.arch})")
    print(f"  CPU/RAM   : {dev.cpu_cores} cores / {dev.ram_gb} GB")
    gpus = ", ".join(f"{g['name']} ({g['vram_mb']} MB)" for g in dev.gpu) or "none detected"
    print(f"  GPU       : {gpus}")
    print(f"  NPU       : {'yes (Intel OpenVINO)' if dev.npu else 'no'}")
    print(f"  Compute   : {dev.tier} (cuda={dev.cuda}, vulkan={dev.vulkan})")
    print(f"  Disk free : {dev.disk_free_gb} GB on {dev.disk_path}")
    print(f"  Recommend : policy={rec['policy']} ctx={rec['ctx']} auto_tier={rec['auto_tier']}")
    print(f"              {rec['note']}")

    manifest = cs.load_manifest()
    feats = list(manifest["features"]) if args.all else choose_features(cs, args.features, args.yes)
    print(f"\nInstalling features: {', '.join(feats)}")
    if not args.yes:
        if input("Proceed? [Y/n] ").strip().lower() in ("n", "no"):
            print("aborted.")
            return
    for line in cs.fetch(feats, manifest=manifest, update=args.update):
        print(" ", line, flush=True)

    print("\nDone. Next steps:")
    print("  inference : coli serve --model D:/colibri-models/qwen36-35b --auto-tier --port 8184")
    print("  desktop   : cd colibri-code && npm install && npm run dist:exe")
    print("  agent     : cd colibri-coding-agent && python -m agent.server")
    print("  jetbrains : cd colibri-jetbrains && ./build-plugin.sh")
    print("\nBuilt on Colibri (JustVugg/colibri) + AirLLM (lyogavin/airllm).")


if __name__ == "__main__":
    main()