# Colibri Installer

The whole-environment entry point. Detects your device (OS, arch, GPU, NPU, RAM,
disk), recommends a conservative inference config, and lets you choose which
features/apps to fetch and install. It bootstraps the
[environment setup](https://github.com/Liso7150/colibri-environment-setup) hub and
drives its plan/fetch/install pipeline.

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

## Device detection

Probes NVIDIA (`nvidia-smi`), Vulkan, Metal (macOS), Intel NPU (OpenVINO), RAM
and free disk. The recommendation is deliberately conservative: CPU decoding at
`policy=balanced` with a context window sized to the machine (for example an 8 GB
GPU + 16 GB RAM → `ctx=4096`). Seeing a GPU is not proof that a native
accelerator backend was compiled, so the plan keeps CPU until you verify an
engine build and switch `backend` yourself. The Intel NPU is an embedding
sidecar only, never a decoder.

Android/iOS are detected as client-only: the hub refuses on-device engine
installation and the plan points at a Windows/macOS/Linux host serving the shared
PWA. The model is never executed on the phone.

## Ports

Windows / macOS / Linux run the installer directly. Android uses the PWA client
plus the Termux/WebView scaffold in [`android/`](android/README.md); there is no
APK build pipeline yet.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Credits

Built on [Colibri](https://github.com/JustVugg/colibri) and
[AirLLM](https://github.com/lyogavin/airllm).
