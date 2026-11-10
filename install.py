#!/usr/bin/env python3
"""Colibri installer — compatibility entry point for the portable bootstrap.

`python install.py ...` keeps the historical behavior of downloading the selected
repos; an explicit --plan/--fetch-only/--install/--build always wins. Use
`python bootstrap.py --install ...` when dependencies should also be installed
and the shared runtime config written.

    python install.py                                    # interactive menu
    python install.py --features inference,desktop --yes  # fetch sources
    python install.py --all --yes                         # fetch everything
    python install.py --install --features inference,desktop --yes

Credits: Colibri engine (https://github.com/JustVugg/colibri) and
AirLLM (https://github.com/lyogavin/airllm).
"""
import sys

from bootstrap import main

MODES = {"--plan", "--dry-run", "--fetch-only", "--install", "--build", "--help", "-h"}


def run(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not MODES.intersection(argv):
        argv.append("--fetch-only")
    return main(argv)


if __name__ == "__main__":
    sys.exit(run())
