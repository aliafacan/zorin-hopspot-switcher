#!/usr/bin/env python3
"""
Zorin Hotspot Switcher — GTK 3 ayar ve kontrol arayüzü
Dil: Türkçe / English  |  Tema: Açık / Koyu
"""

import gi
import json
import os
import re
import subprocess
import threading

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

USER_CONFIG_DIR  = os.path.expanduser("~/.config/zorin-hotspot-switcher")
USER_CONFIG_FILE = os.path.join(USER_CONFIG_DIR, "config.conf")
PREFS_FILE       = os.path.join(USER_CONFIG_DIR, "prefs.json")
SYSTEM_CONFIG    = "/etc/zorin-hotspot-switcher.conf"
HOTSPOTCTL       = "/usr/local/bin/zorin-hotspotctl"

DEFAULTS = {
    "HOTSPOT_SSID":          "ZorinHotspot",
    "HOTSPOT_PASSWORD":      "12345678",
    "HOTSPOT_BACKEND":       "create_ap",
    "PREFER_24GHZ_ON_START": "yes",
    "RETURN_TO_5GHZ_ON_STOP":"yes",
    "PREFERRED_24GHZ_BSSID": "",
    "PREFERRED_5GHZ_BSSID":  "",
}

# ─── I18N ─────────────────────────────────────────────────────────────────────

STRINGS = {
    'tr': {
        'app_title':      'Zorin Hotspot Switcher',
        'lang_label':     'Dil',
        'theme_label':    'Koyu tema',
        'sec_prefs':      'Tercihler',
        'tab_settings':   'Ayarlar',
        'tab_control':    'Durum & Kontrol',
        'tab_bssid':      'BSSID Tarama',
        'tab_devices':    'Bağlı Cihazlar',
        # Ayarlar
        'sec_identity':   'Hotspot Kimliği',
        'lbl_ssid':       'Hotspot adı (SSID)',
        'lbl_pass':       'Şifre (≥8 karakter)',
        'show_pass':      'Göster',
        'sec_backend':    'Hotspot Motoru',
        'lbl_backend':    'Backend',
        'be_create_ap':   'create_ap  (önerilir — eş zamanlı STA+AP)',
        'be_nmcli':       'nmcli hotspot  (uyarı: mevcut bağlantıyı kesebilir)',
        'sec_band':       'Bant Yönetimi',
        'lbl_prefer24':   'Başlatırken 2.4GHz\'e geç\n(5GHz kanal kısıtlaması aşmak için)',
        'lbl_return5':    'Kapatırken 5GHz\'e geri dön',
        'sec_bssid_pref': 'Tercih Edilen BSSID\'ler  (boş → en iyi sinyal seçilir)',
        'lbl_bssid24':    '2.4GHz BSSID',
        'lbl_bssid5':     '5GHz BSSID',
        'ph_bssid':       'Örn: E8:26:89:47:62:41',
        'btn_save':       'Ayarları Kaydet',
        'save_ok':        'Kaydedildi → {path}',
        'save_err':       'Kayıt hatası: {err}',
        'err_ssid_empty': 'Hotspot adı boş olamaz.',
        'err_pass_short': 'Şifre en az 8 karakter olmalı.',
        # Kontrol
        'frm_status':     'Hotspot Durumu',
        'status_query':   'Sorgulanıyor...',
        'status_running': '● Çalışıyor',
        'status_stopped': '○ Durduruldu',
        'btn_refresh':    'Yenile',
        'frm_ctrl':       'Kontrol',
        'btn_start':      'Hotspot Başlat',
        'btn_stop':       'Hotspot Durdur',
        'frm_output':     'Çıktı',
        'log_starting':   '→ zorin-hotspotctl start çalıştırılıyor...',
        'log_stopping':   '→ zorin-hotspotctl stop çalıştırılıyor...',
        'log_no_output':  '(çıktı yok)',
        'log_exit':       '[Çıkış kodu: {code}]',
        # BSSID
        'btn_scan':       'Tara',
        'scanning':       'Taranıyor...',
        'scan_found':     '{n} ağ bulundu.',
        'col_active':     'Bağlı',
        'col_ssid':       'SSID',
        'col_bssid':      'BSSID',
        'col_band':       'Bant',
        'col_chan':        'Kanal',
        'col_signal':     'Sinyal',
        'bssid_hint':     'BSSID\'yi Ayarlar sekmesine kopyalamak için çift tıklayın.',
        'dlg_bssid_txt':  'BSSID: {bssid}  ({band})',
        'dlg_bssid_sec':  'Bu BSSID\'yi tercih edilen {band} BSSID alanına kopyalamak ister misiniz?',
        # Cihazlar
        'col_devname':    'Cihaz Adı',
        'col_ip':         'IP Adresi',
        'col_mac':        'MAC',
        'col_sigdbm':     'Sinyal',
        'col_rx':         'İndirilen',
        'col_tx':         'Yüklenen',
        'col_blocked':    'Engelli',
        'btn_kick':       'Bağlantıyı Kes',
        'btn_block':      'Engelle',
        'btn_unblock':    'Engeli Kaldır',
        'dev_none':       'Bağlı cihaz yok.',
        'dev_count':      '{n} cihaz bağlı.',
        'dev_error':      'Cihaz listesi alınamadı.',
        'dev_parse_err':  'Yanıt ayrıştırılamadı.',
        'dev_select':     'Önce bir cihaz seçin.',
    },
    'en': {
        'app_title':      'Zorin Hotspot Switcher',
        'lang_label':     'Language',
        'theme_label':    'Dark theme',
        'sec_prefs':      'Preferences',
        'tab_settings':   'Settings',
        'tab_control':    'Status & Control',
        'tab_bssid':      'BSSID Scan',
        'tab_devices':    'Connected Devices',
        # Settings
        'sec_identity':   'Hotspot Identity',
        'lbl_ssid':       'Hotspot name (SSID)',
        'lbl_pass':       'Password (≥8 chars)',
        'show_pass':      'Show',
        'sec_backend':    'Hotspot Engine',
        'lbl_backend':    'Backend',
        'be_create_ap':   'create_ap  (recommended — simultaneous STA+AP)',
        'be_nmcli':       'nmcli hotspot  (warning: may disconnect current connection)',
        'sec_band':       'Band Management',
        'lbl_prefer24':   'Switch to 2.4GHz on start\n(to bypass 5GHz channel restriction)',
        'lbl_return5':    'Return to 5GHz on stop',
        'sec_bssid_pref': 'Preferred BSSIDs  (blank → auto-select best signal)',
        'lbl_bssid24':    '2.4GHz BSSID',
        'lbl_bssid5':     '5GHz BSSID',
        'ph_bssid':       'e.g. E8:26:89:47:62:41',
        'btn_save':       'Save Settings',
        'save_ok':        'Saved → {path}',
        'save_err':       'Save error: {err}',
        'err_ssid_empty': 'Hotspot name cannot be empty.',
        'err_pass_short': 'Password must be at least 8 characters.',
        # Control
        'frm_status':     'Hotspot Status',
        'status_query':   'Querying...',
        'status_running': '● Running',
        'status_stopped': '○ Stopped',
        'btn_refresh':    'Refresh',
        'frm_ctrl':       'Control',
        'btn_start':      'Start Hotspot',
        'btn_stop':       'Stop Hotspot',
        'frm_output':     'Output',
        'log_starting':   '→ Running zorin-hotspotctl start...',
        'log_stopping':   '→ Running zorin-hotspotctl stop...',
        'log_no_output':  '(no output)',
        'log_exit':       '[Exit code: {code}]',
        # BSSID
        'btn_scan':       'Scan',
        'scanning':       'Scanning...',
        'scan_found':     '{n} networks found.',
        'col_active':     'Active',
        'col_ssid':       'SSID',
        'col_bssid':      'BSSID',
        'col_band':       'Band',
        'col_chan':        'Channel',
        'col_signal':     'Signal',
        'bssid_hint':     'Double-click to copy BSSID to the Settings tab.',
        'dlg_bssid_txt':  'BSSID: {bssid}  ({band})',
        'dlg_bssid_sec':  'Copy this BSSID to the preferred {band} BSSID field?',
        # Devices
        'col_devname':    'Device Name',
        'col_ip':         'IP Address',
        'col_mac':        'MAC',
        'col_sigdbm':     'Signal',
        'col_rx':         'Downloaded',
        'col_tx':         'Uploaded',
        'col_blocked':    'Blocked',
        'btn_kick':       'Disconnect',
        'btn_block':      'Block',
        'btn_unblock':    'Unblock',
        'dev_none':       'No connected devices.',
        'dev_count':      '{n} device(s) connected.',
        'dev_error':      'Cannot get device list.',
        'dev_parse_err':  'Failed to parse response.',
        'dev_select':     'Select a device first.',
    },
}

_LANG = 'tr'


def t(key, **kw):
    s = STRINGS.get(_LANG, STRINGS['tr']).get(key, STRINGS['tr'].get(key, key))
    return s.format(**kw) if kw else s


# ─── Prefs I/O ────────────────────────────────────────────────────────────────

def load_prefs() -> dict:
    d = {'lang': 'tr', 'dark': False}
    try:
        with open(PREFS_FILE) as f:
            d.update(json.load(f))
    except Exception:
        pass
    return d


def save_prefs(p: dict):
    os.makedirs(USER_CONFIG_DIR, exist_ok=True)
    with open(PREFS_FILE, 'w') as f:
        json.dump(p, f, indent=2)


# ─── Config I/O ───────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg = dict(DEFAULTS)
    for path in [SYSTEM_CONFIG, USER_CONFIG_FILE]:
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    v = v.strip().strip('"').strip("'")
                    cfg[k.strip()] = v
        except OSError:
            pass
    return cfg


def save_config(cfg: dict):
    os.makedirs(USER_CONFIG_DIR, exist_ok=True)
    lines = [
        '# Zorin Hotspot Switcher — kullanıcı ayarları\n',
        '# Bu dosyayı elle veya uygulama arayüzüyle düzenleyebilirsiniz.\n\n',
    ]
    for k, v in cfg.items():
        lines.append(f'{k}="{v}"\n')
    with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
        f.writelines(lines)


# ─── Tema ────────────────────────────────────────────────────────────────────

def _set_dark(dark: bool):
    s = Gtk.Settings.get_default()
    s.props.gtk_application_prefer_dark_theme = dark
    # Zorin / Yaru gibi -Light/-Dark çift temalı sistemlerde adı da değiştir
    theme = s.props.gtk_theme_name
    if dark and '-Light' in theme:
        s.props.gtk_theme_name = theme.replace('-Light', '-Dark')
    elif not dark and '-Dark' in theme:
        s.props.gtk_theme_name = theme.replace('-Dark', '-Light')


# ─── Yardımcılar ─────────────────────────────────────────────────────────────

def run_cmd(args: list) -> subprocess.CompletedProcess:
    return subprocess.run(args, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def scan_bssids(ssid_filter: str = '') -> list:
    cp = run_cmd(['nmcli', '-t', '-f', 'IN-USE,SSID,BSSID,CHAN,FREQ,SIGNAL',
                  'dev', 'wifi', 'list', '--rescan', 'yes'])
    results = []
    for raw in cp.stdout.splitlines():
        parts = re.split(r'(?<!\\):', raw)
        parts = [p.replace('\\:', ':') for p in parts]
        if len(parts) < 6:
            continue
        try:
            ssid   = parts[1].strip()
            bssid  = parts[2].strip()
            chan   = int(parts[3].strip())
            freq   = int(re.sub(r'\D', '', parts[4]))
            sig    = int(parts[5].strip())
            in_use = parts[0].strip() == '*'
        except (ValueError, IndexError):
            continue
        if not bssid:
            continue
        if ssid_filter and ssid != ssid_filter:
            continue
        results.append({
            'in_use': in_use, 'ssid': ssid, 'bssid': bssid,
            'chan': chan, 'freq': freq, 'signal': sig,
            'band': '2.4GHz' if freq < 3000 else '5GHz',
        })
    return results


# ─── Ana pencere ─────────────────────────────────────────────────────────────

class App(Gtk.Window):
    def __init__(self):
        super().__init__()
        self._devices_timer = None
        self._cfg = load_config()
        self._root = None
        self._notebook = None

        GLib.set_prgname('zorin-hotspot-switcher')
        GLib.set_application_name('Zorin Hotspot Switcher')

        prefs = load_prefs()
        global _LANG
        _LANG = prefs.get('lang', 'tr')
        _set_dark(prefs.get('dark', False))

        self.set_title(t('app_title'))
        self.set_icon_name('zorin-hotspot-switcher')
        self.set_default_size(720, 640)
        self.connect('destroy', self._on_destroy)

        self._build_ui()
        self.show_all()

        GLib.idle_add(self._refresh_status)
        self._devices_timer = GLib.timeout_add_seconds(10, self._auto_refresh_devices)

    # ── UI yapısı ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        if self._root:
            self.remove(self._root)

        self._root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self._root)

        self._notebook = Gtk.Notebook()
        self._notebook.set_vexpand(True)
        self._root.pack_start(self._notebook, True, True, 0)
        self._fill_notebook()

    def _fill_notebook(self):
        self._notebook.append_page(
            self._build_settings_tab(), Gtk.Label(label=t('tab_settings')))
        self._notebook.append_page(
            self._build_control_tab(),  Gtk.Label(label=t('tab_control')))
        self._notebook.append_page(
            self._build_bssid_tab(),    Gtk.Label(label=t('tab_bssid')))
        self._notebook.append_page(
            self._build_devices_tab(),  Gtk.Label(label=t('tab_devices')))
        self._notebook.connect('switch-page', self._on_tab_switch)

    def _rebuild_ui(self):
        old = self._root
        self._build_ui()
        if old:
            old.destroy()
        self.set_title(t('app_title'))
        self._root.show_all()
        self._refresh_status()
        return False  # idle_add: tek seferlik

    def _on_lang_changed(self, combo):
        global _LANG
        new = combo.get_active_id()
        if not new or new == _LANG:
            return
        _LANG = new
        p = load_prefs()
        p['lang'] = new
        save_prefs(p)
        GLib.idle_add(self._rebuild_ui)

    def _on_theme_changed(self, sw, _p):
        dark = sw.get_active()
        _set_dark(dark)
        p = load_prefs()
        p['dark'] = dark
        save_prefs(p)

    def _on_tab_switch(self, _nb, _page, page_num):
        if page_num == 3:
            self._refresh_devices()

    def _on_destroy(self, *_):
        if self._devices_timer:
            GLib.Source.remove(self._devices_timer)
            self._devices_timer = None
        Gtk.main_quit()

    # ── Ayarlar sekmesi ───────────────────────────────────────────────────────

    def _build_settings_tab(self) -> Gtk.Widget:
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_border_width(16)
        scroll.add(outer)

        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(8)
        grid.set_hexpand(True)
        outer.pack_start(grid, False, True, 0)

        r = [0]

        def section(key):
            lbl = Gtk.Label(xalign=0)
            lbl.set_markup(f'<b>{t(key)}</b>')
            lbl.set_margin_top(12)
            grid.attach(lbl, 0, r[0], 2, 1)
            r[0] += 1

        def row(key, widget):
            lbl = Gtk.Label(label=t(key), xalign=0)
            lbl.set_hexpand(False)
            lbl.set_line_wrap(True)
            widget.set_hexpand(True)
            grid.attach(lbl, 0, r[0], 1, 1)
            grid.attach(widget, 1, r[0], 1, 1)
            r[0] += 1

        # ── Tercihler ────────────────────────────────────────────────────────
        section('sec_prefs')

        lang_combo = Gtk.ComboBoxText()
        lang_combo.append('tr', 'Türkçe')
        lang_combo.append('en', 'English')
        lang_combo.set_active_id(_LANG)
        lang_combo.connect('changed', self._on_lang_changed)
        row('lang_label', lang_combo)

        theme_sw = Gtk.Switch(halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        theme_sw.set_active(load_prefs().get('dark', False))
        theme_sw.connect('notify::active', self._on_theme_changed)
        row('theme_label', theme_sw)

        # ── Kimlik ──────────────────────────────────────────────────────────
        section('sec_identity')

        self._ssid_entry = Gtk.Entry()
        self._ssid_entry.set_text(self._cfg['HOTSPOT_SSID'])
        row('lbl_ssid', self._ssid_entry)

        self._pass_entry = Gtk.Entry()
        self._pass_entry.set_text(self._cfg['HOTSPOT_PASSWORD'])
        self._pass_entry.set_visibility(False)
        self._pass_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        pass_box = Gtk.Box(spacing=4)
        pass_box.set_hexpand(True)
        pass_box.pack_start(self._pass_entry, True, True, 0)
        show_btn = Gtk.CheckButton(label=t('show_pass'))
        show_btn.connect('toggled', lambda b: self._pass_entry.set_visibility(b.get_active()))
        pass_box.pack_start(show_btn, False, False, 0)
        row('lbl_pass', pass_box)

        # ── Backend ─────────────────────────────────────────────────────────
        section('sec_backend')

        self._backend_combo = Gtk.ComboBoxText()
        self._backend_combo.append('create_ap', t('be_create_ap'))
        self._backend_combo.append('nmcli',     t('be_nmcli'))
        active_id = self._cfg.get('HOTSPOT_BACKEND', 'create_ap')
        self._backend_combo.set_active_id(
            active_id if active_id in ('create_ap', 'nmcli') else 'create_ap')
        row('lbl_backend', self._backend_combo)

        # ── Bant yönetimi ────────────────────────────────────────────────────
        section('sec_band')

        self._prefer24_sw = Gtk.Switch(halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        self._prefer24_sw.set_active(
            self._cfg['PREFER_24GHZ_ON_START'].lower() in ('yes', 'true', '1'))
        row('lbl_prefer24', self._prefer24_sw)

        self._return5_sw = Gtk.Switch(halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        self._return5_sw.set_active(
            self._cfg['RETURN_TO_5GHZ_ON_STOP'].lower() in ('yes', 'true', '1'))
        row('lbl_return5', self._return5_sw)

        # ── Tercih BSSID ─────────────────────────────────────────────────────
        section('sec_bssid_pref')

        self._bssid24_entry = Gtk.Entry()
        self._bssid24_entry.set_placeholder_text(t('ph_bssid'))
        self._bssid24_entry.set_text(self._cfg['PREFERRED_24GHZ_BSSID'])
        row('lbl_bssid24', self._bssid24_entry)

        self._bssid5_entry = Gtk.Entry()
        self._bssid5_entry.set_placeholder_text(t('ph_bssid'))
        self._bssid5_entry.set_text(self._cfg['PREFERRED_5GHZ_BSSID'])
        row('lbl_bssid5', self._bssid5_entry)

        save_btn = Gtk.Button(label=t('btn_save'))
        save_btn.get_style_context().add_class('suggested-action')
        save_btn.set_margin_top(16)
        save_btn.connect('clicked', self._on_save)
        outer.pack_start(save_btn, False, False, 0)

        self._save_result = Gtk.Label(xalign=0)
        outer.pack_start(self._save_result, False, False, 4)

        return scroll

    def _on_save(self, _btn):
        ssid = self._ssid_entry.get_text().strip()
        pwd  = self._pass_entry.get_text().strip()
        if not ssid:
            self._save_result.set_markup(
                f"<span color='red'>{t('err_ssid_empty')}</span>")
            return
        if len(pwd) < 8:
            self._save_result.set_markup(
                f"<span color='red'>{t('err_pass_short')}</span>")
            return
        cfg = {
            'HOTSPOT_SSID':          ssid,
            'HOTSPOT_PASSWORD':      pwd,
            'HOTSPOT_BACKEND':       self._backend_combo.get_active_id() or 'create_ap',
            'PREFER_24GHZ_ON_START': 'yes' if self._prefer24_sw.get_active() else 'no',
            'RETURN_TO_5GHZ_ON_STOP':'yes' if self._return5_sw.get_active() else 'no',
            'PREFERRED_24GHZ_BSSID': self._bssid24_entry.get_text().strip(),
            'PREFERRED_5GHZ_BSSID':  self._bssid5_entry.get_text().strip(),
        }
        try:
            save_config(cfg)
            self._cfg = cfg
            self._save_result.set_markup(
                f"<span color='green'>{t('save_ok', path=USER_CONFIG_FILE)}</span>")
        except OSError as e:
            self._save_result.set_markup(
                f"<span color='red'>{t('save_err', err=e)}</span>")

    # ── Durum & Kontrol sekmesi ───────────────────────────────────────────────

    def _build_control_tab(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(16)

        sf = Gtk.Frame(label=f' {t("frm_status")} ')
        sb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sb.set_border_width(10)
        sf.add(sb)
        self._status_label = Gtk.Label(label=t('status_query'), xalign=0)
        self._status_label.set_line_wrap(True)
        sb.pack_start(self._status_label, False, False, 0)
        rb = Gtk.Button(label=t('btn_refresh'))
        rb.connect('clicked', lambda _: self._refresh_status())
        sb.pack_start(rb, False, False, 0)
        box.pack_start(sf, False, False, 0)

        cf = Gtk.Frame(label=f' {t("frm_ctrl")} ')
        cb = Gtk.Box(spacing=10)
        cb.set_border_width(10)
        cf.add(cb)
        self._start_btn = Gtk.Button(label=t('btn_start'))
        self._start_btn.get_style_context().add_class('suggested-action')
        self._start_btn.connect('clicked', lambda _: self._on_start())
        cb.pack_start(self._start_btn, True, True, 0)
        self._stop_btn = Gtk.Button(label=t('btn_stop'))
        self._stop_btn.get_style_context().add_class('destructive-action')
        self._stop_btn.connect('clicked', lambda _: self._on_stop())
        cb.pack_start(self._stop_btn, True, True, 0)
        box.pack_start(cf, False, False, 0)

        lf = Gtk.Frame(label=f' {t("frm_output")} ')
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        self._log_view = Gtk.TextView(editable=False, monospace=True,
                                      wrap_mode=Gtk.WrapMode.WORD_CHAR)
        scroll.add(self._log_view)
        lf.add(scroll)
        box.pack_start(lf, True, True, 0)

        return box

    def _append_log(self, text: str):
        buf = self._log_view.get_buffer()
        buf.insert(buf.get_end_iter(), text + '\n')
        mark = buf.create_mark(None, buf.get_end_iter(), False)
        self._log_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

    def _refresh_status(self):
        def work():
            cp = run_cmd([HOTSPOTCTL, 'status'])
            out = (cp.stdout or cp.stderr or '').strip()
            GLib.idle_add(self._update_status_label, out)
        threading.Thread(target=work, daemon=True).start()

    def _update_status_label(self, status: str):
        running = bool(re.search(r'running|started|active', status))
        if running:
            self._status_label.set_markup(
                f"<span color='green'><b>{t('status_running')}</b></span>")
        else:
            self._status_label.set_markup(
                f"<span color='gray'><b>{t('status_stopped')}</b></span>")
        self._start_btn.set_sensitive(not running)
        self._stop_btn.set_sensitive(running)

    def _on_start(self):
        self._set_ctrl(False)
        self._append_log(t('log_starting'))
        def work():
            cp = subprocess.run([HOTSPOTCTL, 'start'], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            GLib.idle_add(self._on_cmd_done, (cp.stdout or '').strip(), cp.returncode)
        threading.Thread(target=work, daemon=True).start()

    def _on_stop(self):
        self._set_ctrl(False)
        self._append_log(t('log_stopping'))
        def work():
            cp = subprocess.run([HOTSPOTCTL, 'stop'], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            GLib.idle_add(self._on_cmd_done, (cp.stdout or '').strip(), cp.returncode)
        threading.Thread(target=work, daemon=True).start()

    def _on_cmd_done(self, output: str, returncode: int):
        self._append_log(output or t('log_no_output'))
        if returncode != 0:
            self._append_log(t('log_exit', code=returncode))
        self._set_ctrl(True)
        self._refresh_status()

    def _set_ctrl(self, s: bool):
        self._start_btn.set_sensitive(s)
        self._stop_btn.set_sensitive(s)

    # ── BSSID Tarama sekmesi ──────────────────────────────────────────────────

    def _build_bssid_tab(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_border_width(12)

        top = Gtk.Box(spacing=8)
        scan_btn = Gtk.Button(label=t('btn_scan'))
        scan_btn.connect('clicked', lambda _: self._on_scan())
        top.pack_start(scan_btn, False, False, 0)
        self._scan_status = Gtk.Label(label='', xalign=0)
        top.pack_start(self._scan_status, True, True, 0)
        box.pack_start(top, False, False, 0)

        self._bssid_store = Gtk.ListStore(bool, str, str, str, int, int)
        tv = Gtk.TreeView(model=self._bssid_store)
        tv.set_rules_hint(True)
        self._bssid_tv = tv

        def tcol(title, idx, is_bool=False):
            if is_bool:
                r = Gtk.CellRendererToggle()
                c = Gtk.TreeViewColumn(title, r, active=idx)
            else:
                r = Gtk.CellRendererText()
                c = Gtk.TreeViewColumn(title, r, text=idx)
            c.set_sort_column_id(idx)
            c.set_resizable(True)
            tv.append_column(c)

        tcol(t('col_active'), 0, True)
        tcol(t('col_ssid'),   1)
        tcol(t('col_bssid'),  2)
        tcol(t('col_band'),   3)
        tcol(t('col_chan'),   4)
        tcol(t('col_signal'), 5)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.add(tv)
        box.pack_start(scroll, True, True, 0)

        hint = Gtk.Label(label=t('bssid_hint'), xalign=0)
        hint.set_line_wrap(True)
        box.pack_start(hint, False, False, 0)
        tv.connect('row-activated', self._on_bssid_activated)

        return box

    def _on_scan(self):
        self._scan_status.set_text(t('scanning'))
        self._bssid_store.clear()
        def work():
            GLib.idle_add(self._populate_bssid, scan_bssids())
        threading.Thread(target=work, daemon=True).start()

    def _populate_bssid(self, nets: list):
        self._bssid_store.clear()
        for n in sorted(nets, key=lambda x: -x['signal']):
            self._bssid_store.append([n['in_use'], n['ssid'], n['bssid'],
                                       n['band'], n['chan'], n['signal']])
        self._scan_status.set_text(t('scan_found', n=len(nets)))

    def _on_bssid_activated(self, tv, path, _col):
        row  = tv.get_model()[path]
        bssid, band = row[2], row[3]
        dlg = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=t('dlg_bssid_txt', bssid=bssid, band=band),
        )
        dlg.format_secondary_text(t('dlg_bssid_sec', band=band))
        resp = dlg.run()
        dlg.destroy()
        if resp == Gtk.ResponseType.YES:
            if band == '2.4GHz':
                self._bssid24_entry.set_text(bssid)
            else:
                self._bssid5_entry.set_text(bssid)

    # ── Bağlı Cihazlar sekmesi ────────────────────────────────────────────────

    def _build_devices_tab(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_border_width(12)

        top = Gtk.Box(spacing=8)
        rb = Gtk.Button(label=t('btn_refresh'))
        rb.connect('clicked', lambda _: self._refresh_devices())
        top.pack_start(rb, False, False, 0)
        self._devices_status = Gtk.Label(label='', xalign=0)
        top.pack_start(self._devices_status, True, True, 0)
        box.pack_start(top, False, False, 0)

        # Cihaz adı, IP, MAC, Sinyal, İndirilen, Yüklenen, Engelli
        self._devices_store = Gtk.ListStore(str, str, str, str, str, str, bool)
        tv = Gtk.TreeView(model=self._devices_store)
        tv.set_rules_hint(True)
        self._devices_tv = tv

        for title, idx in [(t('col_devname'), 0), (t('col_ip'), 1), (t('col_mac'), 2),
                           (t('col_sigdbm'), 3), (t('col_rx'), 4), (t('col_tx'), 5)]:
            r = Gtk.CellRendererText()
            c = Gtk.TreeViewColumn(title, r, text=idx)
            c.set_resizable(True)
            c.set_sort_column_id(idx)
            tv.append_column(c)

        r_bl = Gtk.CellRendererToggle()
        c_bl = Gtk.TreeViewColumn(t('col_blocked'), r_bl, active=6)
        tv.append_column(c_bl)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.add(tv)
        box.pack_start(scroll, True, True, 0)

        btn_box = Gtk.Box(spacing=8)
        for key, action in [('btn_kick', 'kick'), ('btn_block', 'block'),
                             ('btn_unblock', 'unblock')]:
            btn = Gtk.Button(label=t(key))
            if action == 'block':
                btn.get_style_context().add_class('destructive-action')
            btn.connect('clicked', lambda _, a=action: self._on_device_action(a))
            btn_box.pack_start(btn, True, True, 0)
        box.pack_start(btn_box, False, False, 0)

        return box

    def _auto_refresh_devices(self):
        self._refresh_devices()
        return GLib.SOURCE_CONTINUE

    def _refresh_devices(self):
        def work():
            cp = run_cmd(['sudo', HOTSPOTCTL, 'devices'])
            GLib.idle_add(self._populate_devices,
                          (cp.stdout or '').strip(), cp.returncode)
        threading.Thread(target=work, daemon=True).start()

    def _populate_devices(self, output: str, returncode: int):
        self._devices_store.clear()
        if returncode != 0 or not output:
            self._devices_status.set_text(t('dev_error'))
            return
        try:
            devices = json.loads(output)
        except Exception:
            self._devices_status.set_text(t('dev_parse_err'))
            return

        def fmt(b):
            if b < 1024:    return f'{b} B'
            if b < 1 << 20: return f'{b/1024:.1f} KB'
            if b < 1 << 30: return f'{b/1024**2:.1f} MB'
            return f'{b/1024**3:.1f} GB'

        for d in devices:
            name = d.get('hostname') or d.get('mac', '?')
            self._devices_store.append([
                name,
                d.get('ip', ''),
                d.get('mac', ''),
                f"{d.get('signal', 0)} dBm",
                fmt(d.get('rx_bytes', 0)),
                fmt(d.get('tx_bytes', 0)),
                d.get('blocked', False),
            ])
        n = len(devices)
        self._devices_status.set_text(t('dev_count', n=n) if n else t('dev_none'))

    def _on_device_action(self, action: str):
        sel = self._devices_tv.get_selection()
        model, it = sel.get_selected()
        if it is None:
            self._devices_status.set_text(t('dev_select'))
            return
        mac = model[it][2]
        def work():
            run_cmd(['sudo', HOTSPOTCTL, action, mac])
            import time; time.sleep(0.5)
            GLib.idle_add(self._refresh_devices)
        threading.Thread(target=work, daemon=True).start()


# ─── Giriş noktası ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    app = App()
    Gtk.main()
