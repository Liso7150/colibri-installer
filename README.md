# Colibri Installer

The whole-environment entry point. Detects your device (OS, arch, GPU, NPU, RAM,
disk), recommends a conservative inference config, and lets you choose which
features/apps to fetch and install. It bootstraps the
[environment setup](https://github.com/Liso7150/colibri-environment-setup) hub and
drives its plan/fetch/install pipeline.

## Features

- Device detection: OS, CPU/RAM, NVIDIA/Vulkan/Apple GPUs, Intel NPU, free disk and Python.
- Feature menu with dependency closure; unknown or cyclic features are rejected.
- Install destination selection (`--root` or interactive) — repos, venv, models, caches and config stay on the device.
- Plan / fetch / install / build actions; the installer never downloads models or starts a server.
- Termux on Android installs the local core + PWA on the phone; Android and iOS browsers are PWA clients.

## Run

```bash
python install.py                                          # interactive menu
python install.py --features inference,desktop --yes        # fetch sources only
python install.py --all --yes                               # fetch everything
python install.py --install --features inference,desktop --yes
python install.py --install --features inference --build --yes
python bootstrap.py --plan --all                            # read-only plan
```

`install.py` is the compatibility entry point: with no explicit mode it selects
`--fetch-only`, preserving the historical "download the repos" behavior.
`--plan`, `--fetch-only`, `--install` and `--build` always win. `--yes` confirms
an explicit action but never selects features; noninteractive runs must pass
`--features` or `--all`. Installing also creates the shared venv, installs the
selected dependencies and writes `~/.colibri/config.json` after all actions
succeed. No server is started by the installer.

## Install destination

On an interactive run the installer first asks where everything should live
(default `~/Colibri`) and shows the layout before anything is downloaded:

```
ROOT/engine   Colibri engine checkout and shared Python venv
ROOT/suite    suite sources: desktop, core, CLI, plugins, fine-tuning
ROOT/models   model weights you add later (nothing is downloaded here)
ROOT/cache    pip / npm / Hugging Face caches
ROOT/setup    environment setup hub used by this installer
```

Every repository, the venv, your model files and all caches stay under that
folder on this device. Only public GitHub sources are downloaded — no models
are fetched automatically and nothing is uploaded. The shared runtime config is
the one small file written outside it (`~/.colibri/config.json`), because every
Colibri app reads it. Pass `--root /path/to/destination` to skip the prompt;
`--yes` keeps the default roots (`~/Colibri`, `~/Colibri-Suite`,
`~/colibri-models`, `~/.cache/colibri` on a fresh machine) or any roots passed
explicitly.

## Device detection

Probes NVIDIA (`nvidia-smi`), Vulkan, Metal (macOS), Intel NPU (OpenVINO), RAM
and free disk. The recommendation is deliberately conservative: CPU decoding at
`policy=balanced` with a context window sized to the machine (for example an 8 GB
GPU + 16 GB RAM → `ctx=4096`). Seeing a GPU is not proof that a native
accelerator backend was compiled, so the plan keeps CPU until you verify an
engine build and switch `backend` yourself. The Intel NPU is an embedding
sidecar only, never a decoder.

Android in a browser and iOS are detected as client-only: the hub refuses
on-device engine installation and the plan points at a Windows/macOS/Linux host
serving the shared PWA. Termux on Android is treated as a local Linux userspace:
the `mobile` feature installs the core and PWA on the phone, and the engine
starts on demand there when a compatible small model and ARM build exist. A 35B
model is never expected to run on a phone.

## Ports

Windows / macOS / Linux run the installer directly. Android can run the core and
PWA locally in Termux (see [`android/`](android/README.md)); Android browsers and
iOS use the PWA as a client of a Colibri host. There is no APK build pipeline yet.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Credits

Built on [Colibri](https://github.com/JustVugg/colibri) and
[AirLLM](https://github.com/lyogavin/airllm).
