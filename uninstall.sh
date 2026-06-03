#!/usr/bin/env bash
# Zorin Hotspot Switcher — kaldırma scripti
set -euo pipefail

EXT_UUID="zorin-hotspot-toggle@local"

echo "=== Zorin Hotspot Switcher kaldırılıyor ==="

# Çalışan hotspot varsa durdur
if /usr/local/bin/zorin-hotspotctl status 2>/dev/null | grep -q running; then
    echo "Çalışan hotspot durduruluyor..."
    sudo /usr/local/bin/zorin-hotspotctl stop 2>/dev/null || true
fi

echo "GNOME extension devre dışı bırakılıyor..."
gnome-extensions disable "$EXT_UUID" 2>/dev/null || true
rm -rf "$HOME/.local/share/gnome-shell/extensions/$EXT_UUID"

echo "Sistem dosyaları kaldırılıyor..."
sudo rm -f /usr/local/bin/zorin-hotspotctl
sudo rm -f /usr/local/bin/zorin-hotspot-switcher
sudo rm -rf /usr/local/share/zorin-hotspot-switcher
sudo rm -rf /var/lib/zorin-hotspot-switcher
sudo rm -f /etc/sudoers.d/zorin-hotspot-switcher

echo "İkon ve .desktop kaldırılıyor..."
sudo rm -f /usr/local/share/icons/hicolor/scalable/apps/zorin-hotspot-switcher.svg
sudo rm -f /usr/local/share/applications/zorin-hotspot-switcher.desktop
command -v gtk-update-icon-cache &>/dev/null && \
    sudo gtk-update-icon-cache -f /usr/local/share/icons/hicolor/ 2>/dev/null || true
command -v update-desktop-database &>/dev/null && \
    sudo update-desktop-database /usr/local/share/applications 2>/dev/null || true

echo ""
echo "Kaldırıldı."
echo ""
echo "Aşağıdaki dosyalar korundu (elle silebilirsin):"
echo "  /etc/zorin-hotspot-switcher.conf"
echo "  ~/.config/zorin-hotspot-switcher/"
echo ""
echo "Hepsini silmek için:"
echo "  sudo rm -f /etc/zorin-hotspot-switcher.conf"
echo "  rm -rf ~/.config/zorin-hotspot-switcher"
