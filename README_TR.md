# Zorin Hotspot Switcher

**Tek WiFi kartıyla herhangi bir ağa bağlı kalırken internet bağlantını hotspot olarak paylaş.**

> 🇬🇧 [English README](README.md)

[![Sürüm](https://img.shields.io/badge/sürüm-1.0.0-brightgreen)](https://github.com/aliafacan/zorin-hopspot-switcher/releases/tag/v1.0.0)
[![Lisans: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GNOME Shell](https://img.shields.io/badge/GNOME%20Shell-45%2F46-informational)](https://extensions.gnome.org)
[![Platform](https://img.shields.io/badge/Platform-Zorin%20OS%2017%2F18-orange)](https://zoringroup.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green)](https://python.org)

---

## Ekran Görüntüleri

| GNOME Hızlı Ayarlar | Ayarlar Uygulaması (Koyu Tema) |
|:---:|:---:|
| ![Hızlı Ayarlar](screenshots/quick-settings-open.png) | ![Ayarlar](screenshots/app-settings-dark.png) |

| Bağlı Cihazlar | Durum & Kontrol |
|:---:|:---:|
| ![Bağlı Cihazlar](screenshots/app-devices.png) | ![Kontrol](screenshots/app-control.png) |

---

## Özellikler

### GNOME Hızlı Ayarlar Paneli
- **Tek tıkla aç/kapat** — doğrudan sistem tepsisinden, uygulama açmaya gerek yok
- **Yerinde SSID ve şifre düzenleme** — tam uygulamayı açmadan değiştir
- **Canlı durum altyazısı** — "Açık — AğAdın" veya "Kapalı" gösterir
- Şifreyi görmek için göz ikonu

### GTK Ayarlar Uygulaması
- **4 sekme:** Ayarlar · Durum & Kontrol · BSSID Tarama · Bağlı Cihazlar
- **Koyu / Açık tema** geçişi — anında uygulanır, tercihler kaydedilir
- **Türkçe / İngilizce** dil desteği — yeniden başlatmaya gerek yok
- **Backend seçimi:** `create_ap` (önerilir) veya `nmcli hotspot`
- **Bant yönetimi:** başlatırken otomatik 2.4GHz'e geç, kapatırken 5GHz'e dön
- **BSSID tarama:** yakın ağları tara, tercih edilen BSSID'yi çift tıkla kopyala

### Bağlı Cihaz Yönetimi
- Bağlı cihazları görüntüle: hostname, IP, MAC, sinyal, TX/RX veri
- **Bağlantıyı Kes** — geçici olarak deauth et
- **Engelle** — deauth + iptables DROP (hotspot yeniden başlasa bile kalıcı)
- **Engeli Kaldır** — iptables kuralını ve kalıcı listeden kaldır
- Her 10 saniyede otomatik yenileme

### Arka Plan ve Sistem
- GNOME Shell'i dondurmayan async subprocess çağrıları
- Start/stop sırasında polling timer duraklar (race condition önlenir)
- Engellenmiş MAC listesi hotspot durdurma/başlatma döngülerinde korunur
- UID bazlı log dosyaları (root `/var/lib/...` yazar, kullanıcı `/tmp/`)

---

## Nasıl Çalışır

Modern WiFi kartlarının çoğu **eş zamanlı STA+AP modunu** destekler — mevcut bir ağa bağlı kalırken (Station) aynı anda hotspot yayını yapabilir (Access Point). Ancak, düzenleyici kısıtlamalar 5GHz kanalların AP modunda kullanımını genellikle engeller.

**Zorin Hotspot Switcher bu sorunu çözer:**

```
1. Şu an bağlı olunan SSID'nin mevcut BSSID'lerini tara
2. 5GHz üzerindeysen → aynı SSID'nin 2.4GHz BSSID'sine geç
3. O 2.4GHz kanalında create_ap başlat (eş zamanlı STA+AP)
4. Durdurulunca → create_ap'i kapat, orijinal 5GHz BSSID'ye dön
```

Sonuç: Mevcut ağa tam hızda bağlı kalırken telefonuna, tabletine veya başka cihazlara internet paylaşırsın.

---

## Gereksinimler

### Sistem
| Gereksinim | Minimum | Notlar |
|---|---|---|
| İşletim Sistemi | Ubuntu 22.04 / Zorin OS 17 | GNOME 45/46 olan herhangi bir distro |
| GNOME Shell | 45 veya 46 | Hızlı Ayarlar extension için |
| Python | 3.10+ | Genellikle kurulu gelir |
| GTK | 3.0 | `gir1.2-gtk-3.0` |
| NetworkManager | herhangi | WiFi bağlantılarını yönetir |
| `iw` | herhangi | WiFi arayüzü tespiti |
| `iptables` | herhangi | Cihaz engelleme özelliği |

### WiFi Kartı
Kartın **aynı kanalda eş zamanlı managed + AP modunu** desteklemesi gerekir.  
Şu komutla kontrol et:
```bash
iw list | grep -A 10 "valid interface combinations"
```
Çıktıda şuna benzer bir şey olmalı: `managed, AP, #channels <= 1`

### Hotspot Backend (birini seç)

**Seçenek A — `create_ap` (önerilir)**
```bash
# Bağımlılıklar
sudo apt install hostapd dnsmasq util-linux procps iw

# create_ap'i GitHub'dan kur
git clone https://github.com/oblique/create_ap
cd create_ap && sudo make install
```

**Seçenek B — `nmcli hotspot`** (yerleşik, ancak bazı donanımlarda ana bağlantıyı kesebilir)  
Ek kurulum gerekmez — NetworkManager halleder.

---

## Kurulum

### Seçenek A — .deb Paketi (önerilir)

```bash
# Releases sayfasından .deb dosyasını indir, ardından:
sudo dpkg -i zorin-hotspot-switcher_1.0.0_all.deb
```

Ya da kendin oluştur:

```bash
git clone https://github.com/aliafacan/zorin-hopspot-switcher.git
cd zorin-hopspot-switcher
bash build-deb.sh
sudo dpkg -i zorin-hotspot-switcher_1.0.0_all.deb
```

Kaldırmak için:
```bash
sudo dpkg -r zorin-hotspot-switcher
```

### Seçenek B — Kurulum Scripti

```bash
# 1. Repoyu klonla
git clone https://github.com/aliafacan/zorin-hopspot-switcher.git
cd zorin-hopspot-switcher

# 2. Kurulum scriptini çalıştır (sudo gerekli)
sudo bash install.sh
```

Kurulum scripti:
- Scriptleri `/usr/local/share/zorin-hotspot-switcher/` konumuna kopyalar
- `/usr/local/bin/` içinde sembolik link oluşturur
- `/var/lib/zorin-hotspot-switcher/` (durum dizini) hazırlar
- `/etc/zorin-hotspot-switcher.conf` oluşturur (yoksa)
- `start`, `stop`, `devices`, `kick`, `block`, `unblock` için `NOPASSWD` sudoers kuralı ekler
- Uygulama ikonunu ve `.desktop` dosyasını kurar
- GNOME Shell extension'ı kurar ve etkinleştirir

### Kurulum Sonrası

**X11 (Zorin OS'ta en yaygın):**
`Alt + F2` → `r` yazıp Enter — GNOME Shell yeniden başlar.

**Wayland:**
Oturumu kapatıp tekrar aç.

**Hotspot** toggle'ı Hızlı Ayarlar panelinde (sağ üst sistem tepsisi) görünecektir.

---

## Kullanım

### GNOME Hızlı Ayarlar (önerilen)
Sistem tepsisine tıkla → **Hotspot** toggle'ını bul.
- **Aç/Kapat** butonuyla hotspot başlat/durdur
- **▶ oku**na tıklayarak yerinde SSID/şifre düzenle

### GTK Uygulaması
```bash
zorin-hotspot-switcher
```
Veya uygulama menüsünde **"Zorin Hotspot Switcher"** ara.

### Komut Satırı
```bash
sudo zorin-hotspotctl start    # hotspot başlat
sudo zorin-hotspotctl stop     # hotspot durdur
zorin-hotspotctl status        # durum kontrol (running/stopped)
sudo zorin-hotspotctl devices  # bağlı cihazları listele (JSON)
sudo zorin-hotspotctl kick  AA:BB:CC:DD:EE:FF   # cihazı at
sudo zorin-hotspotctl block AA:BB:CC:DD:EE:FF   # cihazı engelle
sudo zorin-hotspotctl unblock AA:BB:CC:DD:EE:FF # engeli kaldır
```

---

## Yapılandırma

### Kullanıcı config (sistem config'i geçersiz kılar)
```
~/.config/zorin-hotspot-switcher/config.conf
```

### Sistem config (kurulumda oluşturulur)
```
/etc/zorin-hotspot-switcher.conf
```

### Mevcut seçenekler
```bash
HOTSPOT_SSID="ZorinHotspot"        # Hotspot ağ adı
HOTSPOT_PASSWORD="12345678"         # Şifre (en az 8 karakter)
HOTSPOT_BACKEND="create_ap"         # create_ap | nmcli
PREFER_24GHZ_ON_START="yes"         # Başlatırken 2.4GHz'e geç
RETURN_TO_5GHZ_ON_STOP="yes"        # Durdurulunca 5GHz'e dön
PREFERRED_24GHZ_BSSID=""            # Tercih edilen 2.4GHz BSSID (boş = otomatik)
PREFERRED_5GHZ_BSSID=""             # Tercih edilen 5GHz BSSID (boş = otomatik)
```

### Uygulama tercihleri
```
~/.config/zorin-hotspot-switcher/prefs.json
```
```json
{ "lang": "tr", "dark": false }
```

---

## Desteklenen Sistemler

| Dağıtım | Sürüm | Durum |
|---|---|---|
| Zorin OS | 17, 18.1 | ✅ Birincil hedef |
| Ubuntu | 22.04 LTS, 24.04 LTS | ✅ Test edildi |
| Linux Mint | 21.x | ✅ Uyumlu |
| Debian | 12 (Bookworm) | ✅ Uyumlu |
| Fedora | 38, 39, 40 | ⚠️ Uyumlu (GNOME 45/46 gerekli) |
| Arch Linux | güncel | ⚠️ Uyumlu (AUR: `create_ap`) |
| Pop!_OS | 22.04 | ✅ Uyumlu |

> **Not:** GNOME Shell extension **GNOME 45 veya 46** gerektirir. GTK uygulaması ve CLI, Python 3.10+ ve NetworkManager olan herhangi bir sistemde çalışır.

---

## Sorun Giderme

### Quick Settings'te Hotspot toggle'ı görünmüyor
```bash
gnome-extensions info zorin-hotspot-toggle@local
# Durum: INACTIVE ise GNOME Shell'i yeniden başlat:
# X11: Alt+F2 → r → Enter
# Wayland: oturumu kapatıp aç
```

### `create_ap: You must run it as root`
Sudoers kuralı uygulanmamış olabilir. Yeniden çalıştır:
```bash
sudo bash install.sh
```

### Hotspot başlıyor ama bağlanan cihazlara internet gitmiyor
IP yönlendirmesinin açık olduğunu kontrol et:
```bash
cat /proc/sys/net/ipv4/ip_forward   # 1 olmalı
```
`create_ap` bunu otomatik etkinleştirir. `nmcli` kullanıyorsan masquerading'i kontrol et:
```bash
iptables -t nat -L POSTROUTING -n -v
```

### Log dosyaları
```bash
# Sistem logu (root olarak çalışırken)
cat /var/lib/zorin-hotspot-switcher/hotspotctl.log

# GNOME Shell extension logu
journalctl -b 0 -g "ZorinHotspot" --no-pager
```

---

## Kaldırma

```bash
sudo bash uninstall.sh
```

Korunan dosyalar (istersen elle sil):
```bash
sudo rm -f /etc/zorin-hotspot-switcher.conf
rm -rf ~/.config/zorin-hotspot-switcher
```

---

## Katkıda Bulunma

Pull request'ler memnuniyetle kabul edilir! Lütfen:
1. Repoyu fork'la
2. Özellik dalı oluştur (`git checkout -b feature/ozelligim`)
3. Değişikliklerini commit'le
4. Pull request aç

---

## Lisans

MIT Lisansı — ayrıntılar için [LICENSE](LICENSE) dosyasına bakın.

---

*İkinci bir WiFi adaptörüne gerek kalmadan internet bağlantısını hotspot olarak paylaşmak isteyen Zorin OS kullanıcıları için yapıldı.*
