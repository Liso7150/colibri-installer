# Colibri on Android

Android is a **client** in this release: the model runs on a Windows/macOS/Linux
host and the phone uses the shared coding-agent PWA. The hub detects
`os=Android` as `client_only` and refuses on-device engine installation, because a
35B MoE and a desktop-sized KV cache do not fit a phone. This folder also ships a
Termux fetch script and a Kotlin WebView scaffold; neither builds an APK in CI.

## Path A — PWA client (recommended)

1. On the host, install the `coding-agent` or `desktop` feature and start the
   shared core (`colibri-agent serve`).
2. Open the host's PWA in Android Chrome and use "Add to Home screen".
3. A non-loopback host requires `COLIBRI_APP_TOKEN` plus TLS in front of the core
   (`COLIBRI_TLS_CERTFILE` / `COLIBRI_TLS_KEYFILE`); plain LAN HTTP is refused.
   The phone stores the token in session storage only.

No inference happens on the phone.

## Path B — Termux (fetch + manual CPU experiment)

Termux gives an Android phone a Linux-like userspace. The script installs
`python`/`git`/a C toolchain, clones this installer, and fetches the
`inference` sources. It deliberately does **not** install dependencies, write
runtime config or start a server, and the hub still reports client-only mode:

```bash
bash termux-setup.sh
```

A CPU-only engine build on Termux is **not validated** by CI. If you want to try
it with a small model you chose yourself:

```bash
make -C "$HOME/Colibri/c" coli
"$HOME/Colibri/c/coli" serve --model <small-model> --ctx 2048 --policy balanced --port 8184
```

Then open `http://127.0.0.1:8184` in the phone browser. Do not point this at the
35B model.

## Path C — native WebView wrapper (scaffold)

`webview/MainActivity.kt` is a minimal activity that loads a Colibri WebView. To
build it you need the Android SDK + Gradle; this repo ships source, not an APK:

1. Create an Android Studio project (Empty Activity, Kotlin).
2. Replace `MainActivity.kt` with the scaffold; add the `INTERNET` permission.
3. Point `COLIBRI_URL` at your host's HTTPS PWA URL (same-origin rules apply).
4. Build the APK yourself.

## Status

- PWA install: supported on the host and verified in desktop Chrome.
- Termux fetch script: provided; CPU engine build unverified.
- WebView activity: source scaffold provided.
- CI APK build / Play packaging: **not implemented** (roadmap).

Engine: [JustVugg/colibri](https://github.com/JustVugg/colibri). Setup:
[colibri-environment-setup](https://github.com/Liso7150/colibri-environment-setup).
Training: [AirLLM](https://github.com/lyogavin/airllm).
