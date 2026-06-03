#!/usr/bin/env bash
# Zorin Hotspot Switcher — .deb paketi oluşturma scripti
# Kullanım: bash build-deb.sh
set -euo pipefail

PKG_NAME="zorin-hotspot-switcher"
PKG_VERSION="1.0.0"
PKG_ARCH="all"
PKG_DIR="${PKG_NAME}_${PKG_VERSION}_${PKG_ARCH}"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
EXT_UUID="zorin-hotspot-toggle@local"
BIN_DIR="/usr/local/bin"
SHARE_DIR="/usr/local/share/zorin-hotspot-switcher"

echo "=== .deb paketi oluşturuluyor: ${PKG_DIR}.deb ==="

rm -rf "$PKG_DIR"

# ── Dizin yapısı ─────────────────────────────────────────────────────────────
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/local/share/zorin-hotspot-switcher/scripts"
mkdir -p "$PKG_DIR/usr/local/share/zorin-hotspot-switcher/gnome-extension/$EXT_UUID"
mkdir -p "$PKG_DIR/usr/local/share/icons/hicolor/scalable/apps"
mkdir -p "$PKG_DIR/usr/local/share/applications"
mkdir -p "$PKG_DIR/var/lib/zorin-hotspot-switcher"

# ── Dosyaları kopyala ─────────────────────────────────────────────────────────
cp "$SRC_DIR/scripts/hotspotctl.py" \
   "$PKG_DIR/usr/local/share/zorin-hotspot-switcher/scripts/hotspotctl.py"
cp "$SRC_DIR/app.py" \
   "$PKG_DIR/usr/local/share/zorin-hotspot-switcher/app.py"
cp "$SRC_DIR/gnome-extension/$EXT_UUID/extension.js" \
   "$PKG_DIR/usr/local/share/zorin-hotspot-switcher/gnome-extension/$EXT_UUID/"
cp "$SRC_DIR/gnome-extension/$EXT_UUID/metadata.json" \
   "$PKG_DIR/usr/local/share/zorin-hotspot-switcher/gnome-extension/$EXT_UUID/"
cp "$SRC_DIR/gnome-extension/$EXT_UUID/stylesheet.css" \
   "$PKG_DIR/usr/local/share/zorin-hotspot-switcher/gnome-extension/$EXT_UUID/"
cp "$SRC_DIR/icons/zorin-hotspot-switcher.svg" \
   "$PKG_DIR/usr/local/share/icons/hicolor/scalable/apps/"
cp "$SRC_DIR/zorin-hotspot-switcher.desktop" \
   "$PKG_DIR/usr/local/share/applications/"

# ── İzinler ───────────────────────────────────────────────────────────────────
chmod 755 "$PKG_DIR/usr/local/share/zorin-hotspot-switcher/scripts/hotspotctl.py"
chmod 755 "$PKG_DIR/usr/local/share/zorin-hotspot-switcher/app.py"
chmod 755 "$PKG_DIR/var/lib/zorin-hotspot-switcher"

# ── DEBIAN/control ────────────────────────────────────────────────────────────
cat > "$PKG_DIR/DEBIAN/control" <<EOF
Package: zorin-hotspot-switcher
Version: $PKG_VERSION
Architecture: all
Maintainer: Ali Afacan <aafacan1425@gmail.com>
Depends: python3 (>= 3.10), gir1.2-gtk-3.0, network-manager, iw, iptables
Recommends: hostapd, dnsmasq
Description: WiFi hotspot switcher for GNOME
 Share your internet connection as a WiFi hotspot while staying connected
 to any network on a single WiFi card. Features a GNOME Quick Settings
 toggle, GTK settings application, and connected device management
 (kick/block/unblock clients).
EOF

# ── DEBIAN/postinst ───────────────────────────────────────────────────────────
cat > "$PKG_DIR/DEBIAN/postinst" <<'POSTINST'
#!/usr/bin/env bash
set -e

BIN_DIR="/usr/local/bin"
SHARE_DIR="/usr/local/share/zorin-hotspot-switcher"
EXT_UUID="zorin-hotspot-toggle@local"

# Sembolik linkler
ln -sf "$SHARE_DIR/scripts/hotspotctl.py" "$BIN_DIR/zorin-hotspotctl"
ln -sf "$SHARE_DIR/app.py"                "$BIN_DIR/zorin-hotspot-switcher"

# Durum dizini
mkdir -p /var/lib/zorin-hotspot-switcher
chown root:root /var/lib/zorin-hotspot-switcher
chmod 755 /var/lib/zorin-hotspot-switcher

# Sistem config (yoksa oluştur)
if [ ! -f /etc/zorin-hotspot-switcher.conf ]; then
    cat > /etc/zorin-hotspot-switcher.conf <<'EOF'
# Zorin Hotspot Switcher — sistem ayarları
HOTSPOT_SSID="ZorinHotspot"
HOTSPOT_PASSWORD="12345678"
HOTSPOT_BACKEND="create_ap"
PREFER_24GHZ_ON_START="yes"
RETURN_TO_5GHZ_ON_STOP="yes"
PREFERRED_24GHZ_BSSID=""
PREFERRED_5GHZ_BSSID=""
EOF
    chmod 600 /etc/zorin-hotspot-switcher.conf
fi

# Sudoers — kurulumu yapan kullanıcıyı tespit et
INSTALL_USER="${SUDO_USER:-}"
if [ -z "$INSTALL_USER" ]; then
    INSTALL_USER="$(who | awk 'NR==1{print $1}')"
fi

if [ -n "$INSTALL_USER" ]; then
    SUDOERS_FILE="/etc/sudoers.d/zorin-hotspot-switcher"
    cat > "$SUDOERS_FILE" <<EOF
$INSTALL_USER ALL=(root) NOPASSWD: $BIN_DIR/zorin-hotspotctl start
$INSTALL_USER ALL=(root) NOPASSWD: $BIN_DIR/zorin-hotspotctl stop
$INSTALL_USER ALL=(root) NOPASSWD: $BIN_DIR/zorin-hotspotctl devices
$INSTALL_USER ALL=(root) NOPASSWD: $BIN_DIR/zorin-hotspotctl kick *
$INSTALL_USER ALL=(root) NOPASSWD: $BIN_DIR/zorin-hotspotctl block *
$INSTALL_USER ALL=(root) NOPASSWD: $BIN_DIR/zorin-hotspotctl unblock *
EOF
    chmod 440 "$SUDOERS_FILE"
    visudo -c -f "$SUDOERS_FILE" 2>/dev/null || rm -f "$SUDOERS_FILE"

    # GNOME extension — kullanıcının home dizinine kur
    USER_HOME="$(getent passwd "$INSTALL_USER" | cut -d: -f6)"
    EXT_DEST="$USER_HOME/.local/share/gnome-shell/extensions/$EXT_UUID"
    mkdir -p "$EXT_DEST"
    cp -r "$SHARE_DIR/gnome-extension/$EXT_UUID/." "$EXT_DEST/"
    chown -R "$INSTALL_USER" "$EXT_DEST"
fi

# İkon önbelleği ve uygulama veritabanı
command -v gtk-update-icon-cache &>/dev/null && \
    gtk-update-icon-cache -f /usr/local/share/icons/hicolor/ 2>/dev/null || true
command -v update-desktop-database &>/dev/null && \
    update-desktop-database /usr/local/share/applications 2>/dev/null || true

echo ""
echo "Zorin Hotspot Switcher kuruldu."
echo "GNOME Shell'i yeniden başlatın:"
echo "  X11:    Alt+F2 → r → Enter"
echo "  Wayland: oturumu kapatıp tekrar açın"
POSTINST

# ── DEBIAN/prerm ──────────────────────────────────────────────────────────────
cat > "$PKG_DIR/DEBIAN/prerm" <<'PRERM'
#!/usr/bin/env bash
set -e

BIN_DIR="/usr/local/bin"
EXT_UUID="zorin-hotspot-toggle@local"

# Çalışan hotspot varsa durdur
"$BIN_DIR/zorin-hotspotctl" status 2>/dev/null | grep -q running && \
    sudo "$BIN_DIR/zorin-hotspotctl" stop 2>/dev/null || true

# Sembolik linkler
rm -f "$BIN_DIR/zorin-hotspotctl" "$BIN_DIR/zorin-hotspot-switcher"

# Sudoers
rm -f /etc/sudoers.d/zorin-hotspot-switcher

# Durum dizini
rm -rf /var/lib/zorin-hotspot-switcher

# GNOME extension
INSTALL_USER="${SUDO_USER:-$(who | awk 'NR==1{print $1}')}"
if [ -n "$INSTALL_USER" ]; then
    USER_HOME="$(getent passwd "$INSTALL_USER" | cut -d: -f6)"
    rm -rf "$USER_HOME/.local/share/gnome-shell/extensions/$EXT_UUID"
fi

# İkon önbelleği ve uygulama veritabanı
command -v gtk-update-icon-cache &>/dev/null && \
    gtk-update-icon-cache -f /usr/local/share/icons/hicolor/ 2>/dev/null || true
command -v update-desktop-database &>/dev/null && \
    update-desktop-database /usr/local/share/applications 2>/dev/null || true
PRERM

chmod 755 "$PKG_DIR/DEBIAN/postinst" "$PKG_DIR/DEBIAN/prerm"

# ── Paketi oluştur ────────────────────────────────────────────────────────────
dpkg-deb --build --root-owner-group "$PKG_DIR"
rm -rf "$PKG_DIR"

echo ""
echo "=== Paket hazır: ${PKG_DIR}.deb ==="
echo ""
echo "Kurmak için:"
echo "  sudo dpkg -i ${PKG_DIR}.deb"
echo ""
echo "Kaldırmak için:"
echo "  sudo dpkg -r zorin-hotspot-switcher"
