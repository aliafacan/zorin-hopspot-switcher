#!/usr/bin/env bash
# Zorin Hotspot Switcher — kurulum scripti
# Kullanım: sudo bash install.sh
set -euo pipefail

SHARE_DIR="/usr/local/share/zorin-hotspot-switcher"
BIN_DIR="/usr/local/bin"
EXT_UUID="zorin-hotspot-toggle@local"
EXT_DEST="$HOME/.local/share/gnome-shell/extensions/$EXT_UUID"
STATE_DIR="/var/lib/zorin-hotspot-switcher"
ICON_DIR="/usr/local/share/icons/hicolor/scalable/apps"
APPS_DIR="/usr/local/share/applications"

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Zorin Hotspot Switcher kurulumu ==="

# ── 1. Paylaşılan dosyalar ────────────────────────────────────────────────────
echo "[1/8] Paylaşılan dosyalar kopyalanıyor..."
sudo mkdir -p "$SHARE_DIR/scripts" "$SHARE_DIR/gnome-extension"
sudo cp "$SRC_DIR/scripts/hotspotctl.py" "$SHARE_DIR/scripts/hotspotctl.py"
sudo chmod 755 "$SHARE_DIR/scripts/hotspotctl.py"
sudo cp "$SRC_DIR/app.py" "$SHARE_DIR/app.py"
sudo chmod 755 "$SHARE_DIR/app.py"
sudo cp -r "$SRC_DIR/gnome-extension/$EXT_UUID" "$SHARE_DIR/gnome-extension/"
[ -f "$SRC_DIR/README.md" ] && sudo cp "$SRC_DIR/README.md" "$SHARE_DIR/README.md" || true

# ── 2. Sembolik linkler ───────────────────────────────────────────────────────
echo "[2/8] Sembolik linkler oluşturuluyor..."
sudo ln -sf "$SHARE_DIR/scripts/hotspotctl.py"   "$BIN_DIR/zorin-hotspotctl"
sudo ln -sf "$SHARE_DIR/app.py"                  "$BIN_DIR/zorin-hotspot-switcher"

# ── 3. Durum dizini ───────────────────────────────────────────────────────────
echo "[3/8] Durum dizini hazırlanıyor..."
sudo mkdir -p "$STATE_DIR"
sudo chown root:root "$STATE_DIR"
sudo chmod 755 "$STATE_DIR"
sudo rm -f "$STATE_DIR/hotspotctl.log" /tmp/zorin-hotspotctl.log 2>/dev/null || true

# ── 4. Sistem config (yoksa oluştur) ─────────────────────────────────────────
echo "[4/8] Sistem config kontrol ediliyor..."
if [ ! -f /etc/zorin-hotspot-switcher.conf ]; then
    sudo tee /etc/zorin-hotspot-switcher.conf > /dev/null <<'EOF'
# Zorin Hotspot Switcher — sistem ayarları
# Kullanıcı ayarları ~/.config/zorin-hotspot-switcher/config.conf dosyasını geçersiz kılar.
HOTSPOT_SSID="ZorinHotspot"
HOTSPOT_PASSWORD="12345678"
HOTSPOT_BACKEND="create_ap"
PREFER_24GHZ_ON_START="yes"
RETURN_TO_5GHZ_ON_STOP="yes"
PREFERRED_24GHZ_BSSID=""
PREFERRED_5GHZ_BSSID=""
EOF
    sudo chmod 600 /etc/zorin-hotspot-switcher.conf
    echo "  → /etc/zorin-hotspot-switcher.conf oluşturuldu."
else
    echo "  → /etc/zorin-hotspot-switcher.conf zaten var, dokunulmadı."
fi

# ── 5. Sudoers kuralı ─────────────────────────────────────────────────────────
echo "[5/8] Sudoers kuralı ekleniyor..."
TARGET_USER="${SUDO_USER:-$USER}"
SUDOERS_FILE="/etc/sudoers.d/zorin-hotspot-switcher"
sudo tee "$SUDOERS_FILE" > /dev/null <<EOF
# zorin-hotspot-switcher — create_ap ve iw/iptables root gerektirir
$TARGET_USER ALL=(root) NOPASSWD: $BIN_DIR/zorin-hotspotctl start
$TARGET_USER ALL=(root) NOPASSWD: $BIN_DIR/zorin-hotspotctl stop
$TARGET_USER ALL=(root) NOPASSWD: $BIN_DIR/zorin-hotspotctl devices
$TARGET_USER ALL=(root) NOPASSWD: $BIN_DIR/zorin-hotspotctl kick *
$TARGET_USER ALL=(root) NOPASSWD: $BIN_DIR/zorin-hotspotctl block *
$TARGET_USER ALL=(root) NOPASSWD: $BIN_DIR/zorin-hotspotctl unblock *
EOF
sudo chmod 440 "$SUDOERS_FILE"
if ! sudo visudo -c -f "$SUDOERS_FILE" &>/dev/null; then
    echo "  UYARI: sudoers dosyası geçersiz, kaldırıldı." >&2
    sudo rm -f "$SUDOERS_FILE"
else
    echo "  → Sudoers kuralı eklendi ($TARGET_USER)."
fi

# ── 6. Uygulama ikonu + .desktop ─────────────────────────────────────────────
echo "[6/8] Uygulama ikonu ve .desktop dosyası kuruluyor..."
sudo mkdir -p "$ICON_DIR" "$APPS_DIR"
sudo cp "$SRC_DIR/icons/zorin-hotspot-switcher.svg" "$ICON_DIR/zorin-hotspot-switcher.svg"
sudo cp "$SRC_DIR/zorin-hotspot-switcher.desktop"   "$APPS_DIR/zorin-hotspot-switcher.desktop"
# İkon önbelleğini ve uygulama veritabanını güncelle
command -v gtk-update-icon-cache &>/dev/null && \
    sudo gtk-update-icon-cache -f /usr/local/share/icons/hicolor/ 2>/dev/null || true
command -v update-desktop-database &>/dev/null && \
    sudo update-desktop-database "$APPS_DIR" 2>/dev/null || true
echo "  → İkon: $ICON_DIR/zorin-hotspot-switcher.svg"
echo "  → .desktop: $APPS_DIR/zorin-hotspot-switcher.desktop"

# ── 7. GNOME extension kurulumu ───────────────────────────────────────────────
echo "[7/8] GNOME extension kuruluyor..."
mkdir -p "$EXT_DEST"
cp "$SRC_DIR/gnome-extension/$EXT_UUID/extension.js"  "$EXT_DEST/extension.js"
cp "$SRC_DIR/gnome-extension/$EXT_UUID/metadata.json" "$EXT_DEST/metadata.json"
cp "$SRC_DIR/gnome-extension/$EXT_UUID/stylesheet.css" "$EXT_DEST/stylesheet.css"

if command -v gnome-extensions &>/dev/null; then
    gnome-extensions disable "$EXT_UUID" 2>/dev/null || true
    sleep 0.5
    gnome-extensions enable "$EXT_UUID" 2>/dev/null && \
        echo "  → Extension etkinleştirildi: $EXT_UUID" || \
        echo "  → Extension etkinleştirilemedi (GNOME Shell yeniden başlatılınca aktif olur)."
fi

# ── 8. Özet ──────────────────────────────────────────────────────────────────
echo ""
echo "[8/8] Kurulum tamamlandı."
echo ""
echo "Komutlar:"
echo "  zorin-hotspotctl start|stop|status|devices"
echo "  zorin-hotspot-switcher              (GTK ayar arayüzü)"
echo ""
echo "GNOME Quick Settings toggle:"
echo "  Wayland  → Oturumu kapat ve yeniden giriş yap"
echo "  X11      → Alt+F2, 'r' yaz, Enter"
echo ""
echo "Uygulama menüsünde 'Zorin Hotspot Switcher' olarak görünür."
echo ""
echo "Ayar dosyaları:"
echo "  /etc/zorin-hotspot-switcher.conf"
echo "  ~/.config/zorin-hotspot-switcher/config.conf"
echo ""
echo "Sorun ayıklama:"
echo "  journalctl -f /usr/bin/gnome-shell | grep ZorinHotspot"
echo "  cat /var/lib/zorin-hotspot-switcher/hotspotctl.log"
