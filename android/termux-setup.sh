#!/data/data/com.termux/files/usr/bin/bash
# Colibri Termux bootstrap (Android). Run inside Termux.
# Android is a PWA client: this fetches sources only. It does not install
# dependencies, write runtime config or start a server.
set -e
pkg update -y
pkg install -y python git clang make cmake
python -m pip install --upgrade pip
if [ ! -d "$HOME/colibri-installer" ]; then
  git clone https://github.com/Liso7150/colibri-installer "$HOME/colibri-installer"
fi
cd "$HOME/colibri-installer"
echo "Fetching inference sources (Android stays a PWA client)..."
python install.py --features inference --yes
echo
echo "Official path: run the core on a desktop host and open its PWA on this phone."
echo "CPU experiment only (small model, not validated by CI):"
echo "  make -C \"\$HOME/Colibri/c\" coli"
echo "  \"\$HOME/Colibri/c/coli\" serve --model <small-model> --ctx 2048 --policy balanced --port 8184"
