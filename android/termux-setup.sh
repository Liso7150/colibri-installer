#!/data/data/com.termux/files/usr/bin/bash
# Fennec Termux bootstrap (Android). Runs the shared core and PWA on the phone
# itself; the engine starts on demand when the first message arrives.
set -e
ROOT="${FENNEC_ROOT:-$HOME/Fennec}"
PORT="${FENNEC_PORT:-8787}"

pkg update -y
pkg install -y python git clang make cmake rust binutils curl termux-tools

if [ ! -d "$HOME/fennec-installer" ]; then
  git clone https://github.com/Liso7150/fennec-installer "$HOME/fennec-installer"
fi

cd "$HOME/fennec-installer"
echo "Installing the phone-local core and PWA under $ROOT ..."
python install.py --install --features mobile --yes --root "$ROOT"

cat > "$ROOT/open-fennec.sh" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
# Start the local Fennec core, open the PWA, stop everything on Ctrl+C.
set -e
ROOT="$ROOT"
PORT="$PORT"
AGENT="\$ROOT/engine/.venv/bin/fennec-agent"
termux-wake-lock
"\$AGENT" serve --host 127.0.0.1 --port "\$PORT" &
CORE=\$!
cleanup() { kill "\$CORE" 2>/dev/null || true; termux-wake-unlock; }
trap cleanup EXIT INT TERM
for _ in \$(seq 1 100); do
  curl -fsS "http://127.0.0.1:\$PORT/api/health" >/dev/null 2>&1 && break
  sleep 0.2
done
termux-open-url "http://127.0.0.1:\$PORT/"
echo "Fennec is running at http://127.0.0.1:\$PORT/ - press Ctrl+C here to stop it."
echo "The engine starts when you send the first message and stops with this core."
wait "\$CORE"
EOF
chmod +x "$ROOT/open-fennec.sh"
ln -sf "$ROOT/open-fennec.sh" "$PREFIX/bin/fennec-open"

echo
echo "Done. Start Fennec with:  fennec-open"
echo "The local engine starts on demand; all files stay under $ROOT."
echo "On-device inference needs a compatible small model in $ROOT/models and an engine build."
echo "The 35B model does not fit on a phone."
