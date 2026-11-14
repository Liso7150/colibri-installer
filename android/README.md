![Fennec on Android 1.0.0 — two supported shapes: the core and PWA on the phone itself in Termux, or the phone as a PWA client of a desktop Fennec host. A 35B MoE model does not fit on a phone. On-phone Termux, PWA client, WebView scaffold, no APK build, engine on demand.](docs/hero.png)

Android has two supported shapes:

* **On the phone itself (Termux)** — the shared core and PWA run in a Linux
  userspace on the phone. The engine starts on demand when you send a message
  and stops with the core. No desktop host is required.
* **PWA client of a desktop host** — the phone opens a desktop Fennec PWA over
  a trusted connection. The desktop engine starts on demand there.

A 35B MoE model does not fit on a phone. On-device inference is only meaningful
with a small, compatible model and an engine build for ARM; that build is not
validated by CI. Everything else — workspace files, the PWA, the agent loop —
runs fine locally.

## Path A — on the phone (Termux, recommended for a self-contained setup)

Termux gives Android a Linux userspace with Python and a Rust toolchain. The
script installs a phone-local core and PWA under `~/Fennec` and installs a single
`fennec-open` command:

```bash
bash termux-setup.sh
fennec-open
```

`fennec-open` starts `fennec-agent serve` on `127.0.0.1:8787`, opens the PWA
in your browser, and keeps the phone awake while it runs. Ctrl+C stops the core;
an engine that the core started is stopped with it. Add the page to your home
screen for an app-like shell.

What lands on the phone, and nowhere else:

```
~/Fennec/engine     Fennec engine checkout (Rust)
~/Fennec/suite      fennec-core + coding-agent PWA
~/Fennec/models     your models (none are downloaded)
~/Fennec/cache      pip cache
~/Fennec/setup      setup hub
~/.fennec/config.json
```

The first send starts the local engine. Without a model the PWA reports that the
engine could not start; the rest of the workspace still works. To try on-device
inference with a small model you already have:

```bash
# 1. place a model the engine supports under ~/Fennec/models/<name>
# 2. point the shared config at it
python - <<'PY'
import json, pathlib
p = pathlib.Path.home() / ".fennec" / "config.json"
data = json.loads(p.read_text())
data["model"] = str(pathlib.Path.home() / "Fennec" / "models" / "<name>")
p.write_text(json.dumps(data, indent=2))
PY
# 3. fetch the engine sources, then build Fennec for that model (ARM build, unverified)
python ~/fennec-installer/install.py --fetch-only --features inference --yes --root ~/Fennec
cargo build --release --manifest-path ~/Fennec/engine/Cargo.toml
# the binary lands in ~/Fennec/engine/target/release/fennec and is launched directly
```

Do not point this at the 35B model.

## Path B — PWA client of a desktop host

1. On the host, install the `coding-agent` or `desktop` feature and start the
   shared core (`fennec-agent serve`).
2. Open the host's PWA in Android Chrome and use "Add to Home screen".
3. A non-loopback host requires `FENNEC_APP_TOKEN` plus TLS in front of the core
   (`FENNEC_TLS_CERTFILE` / `FENNEC_TLS_KEYFILE`); plain LAN HTTP is refused.
   The phone stores the token in session storage only.

The engine is started on demand by the same PWA code, on the host.

## Path C — native WebView wrapper (scaffold)

`webview/MainActivity.kt` is a minimal activity that loads a Fennec WebView. To
build it you need the Android SDK + Gradle; this repo ships source, not an APK:

1. Create an Android Studio project (Empty Activity, Kotlin).
2. Replace `MainActivity.kt` with the scaffold; add the `INTERNET` permission.
3. Point `FENNEC_URL` at your host's HTTPS PWA URL (same-origin rules apply).
4. Build the APK yourself.

## Status

- Termux phone-local core + PWA: script provided; core install validated by
  unit tests, not on a physical phone in CI.
- On-device engine inference: unverified ARM build; small models only.
- PWA install: supported and verified in desktop Chrome; engine auto-start on
  send is covered by the core API.
- WebView activity: source scaffold provided.
- CI APK build / Play packaging: **not implemented** (roadmap).

Engine: [Liso7150/fennec](https://github.com/Liso7150/fennec) (native Rust,
`cargo build --release`). Engine base idea:
[JustVugg/colibri](https://github.com/JustVugg/colibri), whose `c/coli` launcher
remains the legacy fallback. Setup:
[fennec-environment-setup](https://github.com/Liso7150/fennec-environment-setup).
Training: [AirLLM](https://github.com/lyogavin/airllm).
