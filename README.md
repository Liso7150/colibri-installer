# Fennec Installer

The whole-environment entry point. Detects your device (OS, arch, GPU, NPU, RAM,
disk), recommends a conservative inference config, and lets you choose which
features/apps to fetch and install. It bootstraps the
[environment setup](https://github.com/Liso7150/fennec-environment-setup) hub and
drives its plan/fetch/install pipeline.

## Features

- Device detection: OS, CPU/RAM, NVIDIA/Vulkan/Apple GPUs, Intel NPU, free disk and Python.
- Feature menu with dependency closure; unknown or cyclic features are rejected.
- Install destination selection: an interactive drive picker (`--drive E` -> `E:/Fennec`) or any folder (`--root`). — repos, models, caches and config stay on the device.
- Plan / fetch / install / build actions; the installer never downloads models or starts a server.
- `--update` fast-forwards every installed clean Fennec checkout from GitHub (local
  work is never reset, and the upstream engine, Jev and OpenBot checkouts are left
  for you to update deliberately).
- Termux on Android installs the local core + PWA on the phone; Android and iOS browsers are PWA clients.
- `browser-outlets` clones [Jev](https://github.com/browser-use/jev-ultrafast) and [OpenBot](https://github.com/CopilotKit/OpenBot) beside the suite and stops there: no dependencies installed, no patches, nothing started. The shared core drives both, and `--jev-root` / `--openbot-url` point at a checkout or server you already have.

## Run

```bash
python install.py                                          # interactive menu
python install.py --features inference,desktop --yes        # fetch sources only
python install.py --all --yes                               # fetch everything
python install.py --update --yes                            # update installed checkouts
python install.py --install --features inference,desktop --yes
python install.py --install --features inference --build --yes
python install.py --features browser-outlets --yes          # clone Jev + OpenBot only
python bootstrap.py --plan --all                            # read-only plan
```

`install.py` is the compatibility entry point: with no explicit mode it selects
`--fetch-only`, preserving the historical "download the repos" behavior.
`--plan`, `--fetch-only`, `--install` and `--build` always win. `--yes` confirms
an explicit action but never selects features; noninteractive runs must pass
`--features` or `--all` (or `--update` for installed checkouts). Installing also
provisions `python` on PATH with the selected dependencies and writes
`~/.fennec/config.json` after all actions succeed. No server is started by the
installer.

## Install destination

On an interactive run the installer first asks where everything should live: it
lists the drives it finds with their free space, offers the default (`~/Fennec`),
and accepts any drive letter or folder, then shows the layout before anything is downloaded:

```
ROOT/engine   Colibri engine checkout (upstream base idea)
ROOT/suite    suite sources: desktop, core, CLI, plugins, fine-tuning, optional outlets
ROOT/models   model weights you add later (nothing is downloaded here)
ROOT/cache    pip / npm / Hugging Face caches
ROOT/setup    environment setup hub used by this installer
```

Every repository, your model files and all caches stay under that
folder on this device. Only public GitHub sources are downloaded — no models
are fetched automatically and nothing is uploaded. The shared runtime config is
the one small file written outside it (`~/.fennec/config.json`), because every
Fennec app reads it. Pass `--drive E` to install into `E:/Fennec`, or `--root /path/to/destination`
to skip the prompt entirely;
`--yes` keeps the default roots (`~/Colibri`, `~/Fennec-Suite`,
`~/fennec-models`, `~/.cache/fennec` on a fresh machine) or any roots passed
explicitly.

## Device detection

Probes NVIDIA (`nvidia-smi`), Vulkan, Metal (macOS), Intel NPU (OpenVINO), RAM
and free disk. The recommendation is deliberately conservative: CPU decoding at
`policy=balanced` with a context window sized to the machine (for example an 8 GB
GPU + 16 GB RAM → `ctx=4096`). Seeing a GPU is not proof that a native
accelerator backend was compiled, so the plan keeps CPU until you verify an
engine build and switch `backend` yourself. The Intel NPU is an embedding
sidecar only, never a decoder. Selecting the `npu` feature installs what that
sidecar imports (`openvino`, `openvino-tokenizers`, `numpy`, `huggingface-hub`)
into the interpreter the apps resolve — `python` on PATH — and
fetches the prebuilt OpenVINO IR embedding model
(`OpenVINO/bge-base-en-v1.5-int8-ov`) into
`<models_root>/embed/bge-base-en-v1.5-int8-ov`, which is exactly where the
desktop app and the hub look for it. Nothing exports the model itself: the plan
never installs `optimum-intel`, so torch and nncf stay out of that interpreter.
Everything is cached under `<cache_root>` (`PIP_CACHE_DIR`, `HF_HOME`) and only
runs in `--install` mode after you allow downloads; `--plan` just lists the
commands.

Android in a browser and iOS are detected as client-only: the hub refuses
on-device engine installation and the plan points at a Windows/macOS/Linux host
serving the shared PWA. Termux on Android is treated as a local Linux userspace:
the `mobile` feature installs the core and PWA on the phone, and the engine
starts on demand there when a compatible small model and ARM build exist. A 35B
model is never expected to run on a phone.

## Ports

Windows / macOS / Linux run the installer directly. Android can run the core and
PWA locally in Termux (see [`android/`](android/README.md)); Android browsers and
iOS use the PWA as a client of a Fennec host. There is no APK build pipeline yet.

## Migrating an existing Colibri install

`migrate_rebrand.py` moves a pre-1.4 machine onto the Fennec names in one pass:
the suite/hub/models folders, `<root>/.cache/colibri-*`, `~/.colibri` → `~/.fennec`,
`~/.colibri-code` → `~/.fennec-desktop`, the roots inside `config.json`, the
legacy `acp.registry.colibri` records in Air's overlay and `installed.json`, the
`Colibri` picker entry, the `air.acp.registry.path` vmoption, and the model path
in the engine's local stack scripts.

```bash
python migrate_rebrand.py            # print the plan, change nothing
python migrate_rebrand.py --apply    # perform it
```

It is idempotent and stops at the first locked folder without rewriting any
config, so a failed run is safe to repeat. **Close Qoder and every JetBrains IDE
first**: Windows refuses to rename a directory while a process holds a file
inside it open (Qoder's indexer holds the desktop build's `release-*/app.asar`).

On Windows, copy `migrate-fennec.bat` **outside** the suite (a drive root or
`%USERPROFILE%` works) and run that. `cmd.exe` keeps a handle on the running
batch file, so a launcher left inside the suite would block the rename
it is trying to perform; the copy also stages the Python script in `%TEMP%`.

Deliberately untouched: the engine checkout (default `~/Colibri`, upstream
[JustVugg/colibri](https://github.com/JustVugg/colibri)), its `COLI_*`
variables and its `c/coli` entry point. Every edited file keeps a
`*.bak-fennec-rebrand` backup beside it, and the stale desktop code index is
retired rather than rewritten so the sidecar rebuilds it. Afterwards install
`FennecDesktop-2.0.0-x64.exe` and `Fennec-plugin-2.0.0.zip` and start the
IDE once so it republishes the Fennec Air card.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Credits

Engine base idea: [JustVugg/colibri](https://github.com/JustVugg/colibri) —
device-tiered MoE inference. Fine-tuning:
[AirLLM](https://github.com/lyogavin/airllm). Browser outlets:
[browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) and
[CopilotKit/OpenBot](https://github.com/CopilotKit/OpenBot), both used exactly as
upstream and never modified or vendored.
