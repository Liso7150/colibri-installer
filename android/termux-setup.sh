#!/data/data/com.termux/files/usr/bin/bash
# Colibri Termux bootstrap (Android). Run inside Termux.
set -e
pkg update -y
pkg install -y python git clang make cmake
python -m pip install --upgrade pip
if [ ! -d "$HOME/colibri-installer" ]; then
  git clone https://github.com/Liso7150/colibri-installer "$HOME/colibri-installer"
fi
cd "$HOME/colibri-installer"
echo "Detecting device and selecting features (CPU-only on phones)..."
python install.py --features inference --yes
echo
echo "Start the engine with a small model, e.g.:"
echo "  coli serve --model <small-model> --policy balanced --ctx 8192 --port 8184"
echo "Then open http://127.0.0.1:8184 in your browser."