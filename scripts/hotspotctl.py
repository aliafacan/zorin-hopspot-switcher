#!/usr/bin/env python3
"""
zorin-hotspotctl — Tek Wi-Fi kartıyla üniversite ağına bağlı kalıp hotspot açar.

Komutlar:
  start   — (gerekirse 2.4GHz'e geç) create_ap ile hotspot başlat
  stop    — hotspot kapat, (gerekirse) 5GHz BSSID'ye geri dön
  status  — "running" veya "stopped" yaz

Config dosyaları (öncelik sırasıyla):
  ~/.config/zorin-hotspot-switcher/config.conf  (kullanıcı)
  /etc/zorin-hotspot-switcher.conf              (sistem)
"""

import json
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import List, Optional

STATE_DIR = "/var/lib/zorin-hotspot-switcher"
STATE_FILE = os.path.join(STATE_DIR, "state.json")
BLOCKED_FILE = os.path.join(STATE_DIR, "blocked.json")
# Root olarak çalışırken (sudo ile) STATE_DIR'deki log dosyasını kullan;
# /tmp üzerindeki user-owned dosyaya root yazamayabilir (sistem kısıtlaması).
LOG_FILE = (
    os.path.join(STATE_DIR, "hotspotctl.log")
    if os.geteuid() == 0
    else "/tmp/zorin-hotspotctl.log"
)
SYSTEM_CONFIG = "/etc/zorin-hotspot-switcher.conf"
USER_CONFIG = os.path.join(os.path.expanduser("~"), ".config/zorin-hotspot-switcher/config.conf")

DEFAULTS = {
    "HOTSPOT_SSID": "ZorinHotspot",
    "HOTSPOT_PASSWORD": "12345678",
    "HOTSPOT_BACKEND": "create_ap",      # create_ap | nmcli
    "PREFER_24GHZ_ON_START": "yes",      # 5GHz'deyken 2.4GHz'e geç
    "RETURN_TO_5GHZ_ON_STOP": "yes",     # kapatırken 5GHz'e dön
    "PREFERRED_24GHZ_BSSID": "",         # boşsa en iyi sinyal seçilir
    "PREFERRED_5GHZ_BSSID": "",          # boşsa en iyi sinyal seçilir
}


@dataclass
class Net:
    in_use: bool
    ssid: str
    bssid: str
    chan: int
    freq: int
    signal: int

    @property
    def is_24(self) -> bool:
        return self.freq < 3000

    @property
    def is_5(self) -> bool:
        return self.freq >= 3000


def run(args, check=False):
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def log(msg: str):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("%F %T ") + msg + "\n")
    except OSError:
        # Log dosyasına yazılamadı — yalnızca stderr'e düş
        print(time.strftime("%F %T ") + "[LOG] " + msg, file=sys.stderr)


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    # Önce sistem config'i yükle, sonra kullanıcı config'i üzerine yaz
    for path in [SYSTEM_CONFIG, USER_CONFIG]:
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    v = v.strip().strip('"').strip("'")
                    cfg[k.strip()] = v
        except OSError as e:
            log(f"Config okunamadı ({path}): {e}")
    return cfg


def is_yes(val: str) -> bool:
    return val.strip().lower() in ("yes", "true", "1", "on")


def save_state(data: dict):
    os.makedirs(STATE_DIR, exist_ok=True)
    # Root olarak çalışırken de normal kullanıcı okuyabilsin diye 644
    old = os.umask(0o022)
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    finally:
        os.umask(old)


def load_blocked() -> list:
    if not os.path.exists(BLOCKED_FILE):
        return []
    try:
        with open(BLOCKED_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def save_blocked(macs: list):
    os.makedirs(STATE_DIR, exist_ok=True)
    old = os.umask(0o022)
    try:
        with open(BLOCKED_FILE, "w") as f:
            json.dump(macs, f)
    finally:
        os.umask(old)


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def detect_wifi_iface() -> Optional[str]:
    cp = run(["iw", "dev"])
    for line in cp.stdout.splitlines():
        m = re.search(r"^\s*Interface\s+(\S+)", line)
        if m:
            return m.group(1)
    return None


def active_profile(iface: str) -> Optional[str]:
    cp = run(["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"])
    for line in cp.stdout.splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[-1] == iface:
            return ":".join(parts[:-1]).replace("\\:", ":")
    return None


def parse_wifi(rescan: bool = False) -> List[Net]:
    # rescan=False: önbellekten hızlı okuma (~0.2sn); rescan=True: yeniden tara (~5-8sn)
    cp = run(["nmcli", "-t", "-f", "IN-USE,SSID,BSSID,CHAN,FREQ,SIGNAL",
              "dev", "wifi", "list", "--rescan", "yes" if rescan else "no"])
    nets = []
    for raw in cp.stdout.splitlines():
        parts = re.split(r"(?<!\\):", raw)
        parts = [p.replace("\\:", ":") for p in parts]
        if len(parts) < 6:
            continue
        try:
            freq = int(re.sub(r"\D", "", parts[4]))
            nets.append(Net(
                in_use=(parts[0].strip() == "*"),
                ssid=parts[1].strip(),
                bssid=parts[2].strip(),
                chan=int(parts[3].strip()),
                freq=freq,
                signal=int(parts[5].strip()),
            ))
        except Exception:
            continue
    return nets


def switch_bssid(profile: str, bssid: str, band: str):
    log(f"BSSID değiştiriliyor: profile={profile} bssid={bssid} band={band}")
    run(["nmcli", "connection", "modify", profile, "802-11-wireless.bssid", bssid])
    run(["nmcli", "connection", "modify", profile, "802-11-wireless.band", band])
    run(["nmcli", "connection", "down", profile])
    cp = run(["nmcli", "connection", "up", profile])
    log((cp.stdout or cp.stderr).strip())
    if cp.returncode != 0:
        raise RuntimeError((cp.stderr or cp.stdout).strip() or "nmcli connection up başarısız")


def validate_mac(mac: str) -> str:
    mac = mac.upper().strip()
    if not re.fullmatch(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", mac):
        raise ValueError(f"Geçersiz MAC adresi: {mac}")
    return mac


def parse_iw_stations(iface: str) -> list:
    cp = run(["iw", "dev", iface, "station", "dump"])
    stations, cur = [], None
    for line in cp.stdout.splitlines():
        m = re.match(r"Station\s+([0-9a-f:]{17})\s", line.strip(), re.IGNORECASE)
        if m:
            if cur:
                stations.append(cur)
            cur = {"mac": m.group(1).upper(), "signal": 0,
                   "tx_bytes": 0, "rx_bytes": 0, "ip": "", "hostname": "", "blocked": False}
        elif cur:
            s = line.strip()
            if s.startswith("signal:"):
                try:
                    cur["signal"] = int(re.search(r"-\d+", s).group())
                except Exception:
                    pass
            elif s.startswith("tx bytes:"):
                try:
                    cur["tx_bytes"] = int(s.split(":")[1].strip())
                except Exception:
                    pass
            elif s.startswith("rx bytes:"):
                try:
                    cur["rx_bytes"] = int(s.split(":")[1].strip())
                except Exception:
                    pass
    if cur:
        stations.append(cur)
    return stations


def enrich_with_leases(stations: list):
    by_mac = {s["mac"]: s for s in stations}
    for path in ["/var/lib/misc/dnsmasq.leases", "/tmp/dnsmasq.leases"]:
        if not os.path.exists(path):
            continue
        try:
            with open(path) as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        mac = parts[1].upper()
                        if mac in by_mac:
                            by_mac[mac]["ip"] = parts[2]
                            by_mac[mac]["hostname"] = parts[3] if parts[3] != "*" else ""
        except OSError:
            pass
    # Fallback: ARP tablosu (root gerektirmez)
    cp = run(["ip", "neigh", "show"])
    for line in cp.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3] == "lladdr":
            mac = parts[4].upper()
            if mac in by_mac and not by_mac[mac]["ip"]:
                by_mac[mac]["ip"] = parts[0]


def apply_block(mac: str, iface: str):
    run(["iw", "dev", iface, "station", "del", mac])
    run(["iptables", "-D", "FORWARD", "-m", "mac", "--mac-source", mac, "-j", "DROP"])
    run(["iptables", "-I", "FORWARD", "-m", "mac", "--mac-source", mac, "-j", "DROP"])
    log(f"iptables block eklendi: {mac}")


def remove_block(mac: str):
    run(["iptables", "-D", "FORWARD", "-m", "mac", "--mac-source", mac, "-j", "DROP"])
    log(f"iptables block kaldırıldı: {mac}")


def pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ─── status ───────────────────────────────────────────────────────────────────

def cmd_status() -> int:
    st = load_state()
    pid = st.get("pid")
    if pid and pid_running(int(pid)):
        print("running")
        return 0
    # Fallback: process adına göre kontrol
    backend = st.get("backend", "create_ap")
    if backend == "nmcli":
        cp = run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"])
        for line in cp.stdout.splitlines():
            if "802-11-wireless" in line.lower():
                name = line.split(":")[0]
                if "hotspot" in name.lower():
                    print("running")
                    return 0
    else:
        cp = run(["pgrep", "-f", "create_ap"])
        if cp.returncode == 0:
            print("running")
            return 0
    print("stopped")
    return 1


# ─── start ────────────────────────────────────────────────────────────────────

def cmd_start():
    cfg = load_config()
    hs_ssid = cfg["HOTSPOT_SSID"]
    hs_pass = cfg["HOTSPOT_PASSWORD"]
    backend = cfg["HOTSPOT_BACKEND"]
    prefer_24 = is_yes(cfg["PREFER_24GHZ_ON_START"])
    pref_24_bssid = cfg["PREFERRED_24GHZ_BSSID"]
    pref_5_bssid = cfg["PREFERRED_5GHZ_BSSID"]

    if len(hs_pass) < 8:
        raise RuntimeError("HOTSPOT_PASSWORD en az 8 karakter olmalı")

    iface = detect_wifi_iface()
    if not iface:
        raise RuntimeError("Wi-Fi arayüzü bulunamadı")

    profile = active_profile(iface)
    if not profile:
        raise RuntimeError("Aktif NetworkManager profili bulunamadı")

    # Tek tarama: önce hızlı önbellekli oku, gerekirse yeniden tara
    nets = parse_wifi(rescan=False)
    cur  = next((n for n in nets if n.in_use), None)
    if not cur:
        nets = parse_wifi(rescan=True)
        cur  = next((n for n in nets if n.in_use), None)
    if not cur:
        raise RuntimeError("Aktif Wi-Fi bağlantısı bulunamadı")

    same = [n for n in nets if n.ssid == cur.ssid]
    best_24 = sorted([n for n in same if n.is_24], key=lambda n: n.signal, reverse=True)
    best_5  = sorted([n for n in same if n.is_5],  key=lambda n: n.signal, reverse=True)

    # Tercih edilen BSSID varsa listenin başına al
    if pref_24_bssid:
        best_24 = sorted(best_24, key=lambda n: (n.bssid != pref_24_bssid))
    if pref_5_bssid:
        best_5 = sorted(best_5, key=lambda n: (n.bssid != pref_5_bssid))

    original_5_bssid = cur.bssid if cur.is_5 else (best_5[0].bssid if best_5 else None)
    target = cur

    if prefer_24 and cur.is_5:
        if not best_24:
            raise RuntimeError("Aynı SSID için 2.4GHz BSSID bulunamadı")
        target = best_24[0]
        switch_bssid(profile, target.bssid, "bg")
        time.sleep(1)  # nmcli connection up zaten bağlantı kurulunca dönüyor

    channel = target.chan
    os.makedirs(STATE_DIR, exist_ok=True)

    if backend == "nmcli":
        _start_nmcli(iface, hs_ssid, hs_pass, channel,
                     profile, cur, original_5_bssid, target)
    else:
        _start_create_ap(iface, hs_ssid, hs_pass, channel,
                         profile, cur, original_5_bssid, target, backend)

    # Kalıcı engelleri yeniden uygula
    for mac in load_blocked():
        log(f"Engel yeniden uygulanıyor: {mac}")
        try:
            apply_block(mac, iface)
        except Exception as e:
            log(f"Engel uygulanamadı ({mac}): {e}")


def _start_create_ap(iface, ssid, password, channel, profile, cur, original_5_bssid, target, backend):
    log_f = open(LOG_FILE, "a", encoding="utf-8")
    cmd = ["create_ap", "-c", str(channel), iface, iface, ssid, password]
    log("Başlatılıyor: " + " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT,
                            start_new_session=True)
    save_state({
        "pid": proc.pid,
        "backend": "create_ap",
        "iface": iface,
        "profile": profile,
        "hotspot_ssid": ssid,
        "wifi_ssid": cur.ssid,
        "original_5g_bssid": original_5_bssid,
        "target_24g_bssid": target.bssid,
        "target_channel": channel,
    })
    print(f"started pid={proc.pid} channel={channel}")


def _start_nmcli(iface, ssid, password, channel, profile, cur, original_5_bssid, target):
    cmd = [
        "nmcli", "device", "wifi", "hotspot",
        "ifname", iface,
        "ssid", ssid,
        "password", password,
        "band", "bg",
        "channel", str(channel),
    ]
    log("nmcli hotspot başlatılıyor: " + " ".join(cmd))
    cp = run(cmd)
    if cp.returncode != 0:
        raise RuntimeError(f"nmcli hotspot başarısız: {(cp.stderr or cp.stdout).strip()}")
    # nmcli hotspot bağlantı profilini bul
    cp2 = run(["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"])
    hotspot_profile = None
    for line in cp2.stdout.splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[-1] == iface:
            name = ":".join(parts[:-1])
            if "hotspot" in name.lower() or name == "Hotspot 1":
                hotspot_profile = name
                break
    save_state({
        "pid": None,
        "backend": "nmcli",
        "iface": iface,
        "profile": profile,
        "hotspot_profile": hotspot_profile,
        "hotspot_ssid": ssid,
        "wifi_ssid": cur.ssid,
        "original_5g_bssid": original_5_bssid,
        "target_24g_bssid": target.bssid,
        "target_channel": channel,
    })
    print(f"started (nmcli) channel={channel}")


# ─── stop ─────────────────────────────────────────────────────────────────────

def cmd_stop():
    cfg = load_config()
    return_5 = is_yes(cfg["RETURN_TO_5GHZ_ON_STOP"])
    st = load_state()
    backend = st.get("backend", "create_ap")

    # Backend durdurmadan önce iptables kurallarını temizle
    for mac in load_blocked():
        remove_block(mac)

    if backend == "nmcli":
        _stop_nmcli(st)
    else:
        _stop_create_ap(st)

    profile = st.get("profile")
    original_5 = st.get("original_5g_bssid")
    if return_5 and profile and original_5:
        try:
            switch_bssid(profile, original_5, "a")
        except Exception as e:
            log(f"5GHz'e geri dönülemedi: {e}")

    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    print("stopped")


def _stop_create_ap(st: dict):
    pid = st.get("pid")
    if pid:
        try:
            os.killpg(os.getpgid(int(pid)), signal.SIGINT)
            time.sleep(2)
        except Exception as e:
            log(f"SIGINT gönderilemedi: {e}")
    run(["pkill", "-f", "create_ap"])


def _stop_nmcli(st: dict):
    hotspot_profile = st.get("hotspot_profile")
    iface = st.get("iface")
    if hotspot_profile:
        run(["nmcli", "connection", "down", hotspot_profile])
        run(["nmcli", "connection", "delete", hotspot_profile])
    elif iface:
        run(["nmcli", "device", "disconnect", iface])


# ─── devices / kick / block / unblock ────────────────────────────────────────

def cmd_devices() -> int:
    st = load_state()
    iface = st.get("iface")
    if not iface:
        print("[]")
        return 0
    stations = parse_iw_stations(iface)
    enrich_with_leases(stations)
    blocked = load_blocked()
    for s in stations:
        s["blocked"] = s["mac"] in blocked
    print(json.dumps(stations, ensure_ascii=False))
    return 0


def cmd_kick(mac: str) -> int:
    try:
        mac = validate_mac(mac)
    except ValueError as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1
    st = load_state()
    iface = st.get("iface")
    if not iface:
        print("HATA: Aktif hotspot yok", file=sys.stderr)
        return 1
    log(f"Cihaz bağlantısı kesiliyor: {mac}")
    cp = run(["iw", "dev", iface, "station", "del", mac])
    if cp.returncode != 0:
        print(f"HATA: {(cp.stderr or cp.stdout).strip()}", file=sys.stderr)
        return 1
    print(f"kicked {mac}")
    return 0


def cmd_block(mac: str) -> int:
    try:
        mac = validate_mac(mac)
    except ValueError as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1
    st = load_state()
    iface = st.get("iface")
    if not iface:
        print("HATA: Aktif hotspot yok", file=sys.stderr)
        return 1
    log(f"Cihaz engelleniyor: {mac}")
    apply_block(mac, iface)
    blocked = load_blocked()
    if mac not in blocked:
        blocked.append(mac)
        save_blocked(blocked)
    print(f"blocked {mac}")
    return 0


def cmd_unblock(mac: str) -> int:
    try:
        mac = validate_mac(mac)
    except ValueError as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1
    log(f"Cihaz engeli kaldırılıyor: {mac}")
    remove_block(mac)
    save_blocked([m for m in load_blocked() if m != mac])
    print(f"unblocked {mac}")
    return 0


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    if len(sys.argv) < 2:
        print("kullanım: zorin-hotspotctl start|stop|status", file=sys.stderr)
        return 2
    action = sys.argv[1]
    try:
        if action == "start":
            cmd_start()
        elif action == "stop":
            cmd_stop()
        elif action == "status":
            return cmd_status()
        elif action == "devices":
            return cmd_devices()
        elif action in ("kick", "block", "unblock"):
            if len(sys.argv) < 3:
                print(f"kullanım: zorin-hotspotctl {action} <MAC>", file=sys.stderr)
                return 2
            mac_arg = sys.argv[2]
            if action == "kick":
                return cmd_kick(mac_arg)
            elif action == "block":
                return cmd_block(mac_arg)
            else:
                return cmd_unblock(mac_arg)
        else:
            print(f"bilinmeyen komut: {action}", file=sys.stderr)
            return 2
    except Exception as e:
        log("HATA: " + str(e))
        print("HATA: " + str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
