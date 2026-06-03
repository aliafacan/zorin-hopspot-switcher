#!/usr/bin/env bash
set -e
EXT_UUID="zorin-hotspot-toggle@local"
gnome-extensions disable "$EXT_UUID" || true
rm -rf "$HOME/.local/share/gnome-shell/extensions/$EXT_UUID"
sudo rm -f /usr/local/bin/zorin-hotspotctl
sudo rm -rf /var/lib/zorin-hotspot-switcher
# Config bilerek silinmiyor. Silmek istersen:
# sudo rm -f /etc/zorin-hotspot-switcher.conf
echo "Kaldırıldı. Oturumu kapatıp açman gerekebilir."
