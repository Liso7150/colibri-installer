# Colibri on Android (scaffold)

Android is a **scaffold** in this release, not a finished native app. The Colibri
engine is native C + Vulkan and the apps are Python/Electron, so the practical
path on Android is **Termux** (a Linux-like userspace) running the same setup
hub, with a WebView front-end. A native Kotlin/WebView wrapper is sketched below.

## Path A — Termux (recommended, works today)

1. Install [Termux](https://termux.dev) (F-Droid build).
2. Run the bootstrap:

```bash
bash termux-setup.sh
```

It installs `python`/`git`, clones the installer, and runs device detection. On a
phone the engine runs CPU-only (no discrete GPU); pick a small model and the
`balanced` policy. The installer starts the Colibri server on `127.0.0.1:8184`.

3. Open `http://127.0.0.1:8184` in the browser, or the coding-agent UI.

## Path B — native WebView wrapper (scaffold)

`webview/MainActivity.kt` is a minimal Android activity that loads the local
Colibri server in a WebView. To build it you need the Android SDK + Gradle; this
repo ships the source scaffold, not a compiled APK. Steps:

1. Create an Android Studio project (Empty Activity, Kotlin).
2. Replace `MainActivity.kt` with the scaffold; add `INTERNET` permission.
3. Point `COLIBRI_URL` at the Termux-run server (or a LAN host).
4. Build the APK.

## Status

- Termux bootstrap: provided.
- WebView activity: source scaffold provided.
- CI APK build / Play packaging: **not yet implemented** (roadmap).

Engine: [JustVugg/colibri](https://github.com/JustVugg/colibri). Setup:
[colibri-environment-setup](https://github.com/Liso7150/colibri-environment-setup).