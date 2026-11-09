# Colibri Installer

The whole-environment entry point. Detects your device (OS, arch, GPU, NPU, RAM,
disk), recommends an inference config, and lets you choose which features/apps to
install. Bootstraps the [environment setup](https://github.com/Liso7150/colibri-environment-setup)
hub and fetches the selected repos.

## Run

```bash
python install.py                      # interactive, device-aware menu
python install.py --features inference,desktop,jetbrains
python install.py --all --yes          # unattended
```

## Device detection

Probes NVIDIA CUDA (`nvidia-smi`/torch), Vulkan, and Intel NPU (OpenVINO), and
recommends a tier policy + context window (e.g. an 8 GB GPU + 16 GB RAM gets
`policy=quality`, `ctx=32768`, auto-tier).

## Ports

Windows / macOS / Linux run the installer directly. Android uses the Termux +
WebView scaffold in `android/` (see its README).

## Credits

Built on [Colibri](https://github.com/JustVugg/colibri) and
[AirLLM](https://github.com/lyogavin/airllm).