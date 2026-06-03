#!/usr/bin/env bash
set -e
EXT_UUID="zorin-hotspot-toggle@local"
EXT_DIR="$HOME/.local/share/gnome-shell/extensions/$EXT_UUID"

mkdir -p "$EXT_DIR"
cp -r "gnome-extension/$EXT_UUID/"* "$EXT_DIR/"

sudo install -m 755 scripts/hotspotctl.py /usr/local/bin/zorin-hotspotctl

if [ ! -f /etc/zorin-hotspot-switcher.conf ]; then
  cat > /tmp/zorin-hotspot-switcher.conf <<'EOF'
HOTSPOT_SSID="ZorinHotspot"
HOTSPOT_PASSWORD="12345678"
EOF
  sudo install -m 600 /tmp/zorin-hotspot-switcher.conf /etc/zorin-hotspot-switcher.conf
  rm -f /tmp/zorin-hotspot-switcher.conf
fi

if command -v gnome-extensions >/dev/null 2>&1; then
  gnome-extensions enable "$EXT_UUID" || true
fi

echo "Kurulum tamam. Wayland kullanıyorsan oturumu kapatıp tekrar aç. X11 kullanıyorsan Alt+F2, r, Enter yapabilirsin."
echo "Hotspot adı/şifresi: sudo nano /etc/zorin-hotspot-switcher.conf"
